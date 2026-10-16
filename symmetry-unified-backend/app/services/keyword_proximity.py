"""
Keyword proximity analysis for matched paragraph pairs.

Extracts distinctive concepts/keywords from each side of a matched paragraph
pair and identifies those present in one article but absent in the other.

This forms a "second layer" of proximity on top of the semantic similarity
score: even when two paragraphs are semantically matched, one article may
discuss specific people, places, events, or topics that the other omits.

Cross-language strategy
-----------------------
Named entities (PERSON, ORG, GPE, LOC) and proper nouns are often written
identically or very similarly across languages (e.g. "Paris", "Einstein",
"NATO").  For other tokens we rely on fuzzy Levenshtein matching so that
cognates (e.g. "democracy" / "démocratie") are treated as equivalent rather
than distinct.  This makes the extraction meaningful even when source_lang
≠ target_lang.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# spaCy model registry (same languages as PR #10 / existing code)
# ---------------------------------------------------------------------------

_SPACY_MODEL_MAP: dict[str, str] = {
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",
    "es": "es_core_news_sm",
    "it": "it_core_news_sm",
    "pt": "pt_core_news_sm",
    "nl": "nl_core_news_sm",
    "pl": "pl_core_news_sm",
    "ru": "ru_core_news_sm",
    "zh": "zh_core_web_sm",
    "ja": "ja_core_news_sm",
    "ca": "ca_core_news_sm",
    "da": "da_core_news_sm",
    "el": "el_core_news_sm",
    "nb": "nb_core_news_sm",
    "lt": "lt_core_news_sm",
    "mk": "mk_core_news_sm",
    "ro": "ro_core_news_sm",
    "sl": "sl_core_news_sm",
    "uk": "uk_core_news_sm",
    "ko": "ko_core_news_sm",
    "fi": "fi_core_news_sm",
    "sv": "sv_core_news_sm",
    "hr": "hr_core_news_sm",
    "sk": "sk_core_news_sm",
}

# Entity labels kept as concepts.  The English models use OntoNotes labels,
# while most other *_core_news_sm models (es, de, fr, it, pt, ...) use the
# WikiNER set PER / LOC / ORG / MISC, so both sets are needed.  Without PER
# and MISC, people and titled works vanish from non-English paragraphs.
_TARGET_ENT_TYPES: frozenset[str] = frozenset(
    {
        # OntoNotes (English)
        "PERSON",
        "ORG",
        "GPE",
        "LOC",
        "EVENT",
        "WORK_OF_ART",
        "FAC",
        "NORP",
        "PRODUCT",
        "LAW",
        # WikiNER (ORG and LOC are shared with OntoNotes)
        "PER",
        "MISC",
    }
)

# Pipeline components whose labels tell us which entity scheme a model uses.
_NER_COMPONENTS = ("ner", "entity_ruler")

# Minimum character length for a keyword to be considered
_MIN_KEYWORD_LENGTH = 3

# Levenshtein similarity threshold for cross-language keyword matching.
# Two keywords are considered "the same concept" if their normalised edit
# similarity exceeds this value (0 = completely different, 1 = identical).
_CROSS_LANG_MATCH_THRESHOLD = 0.75

# spaCy NLP model cache
_nlp_cache: dict = {}


def _load_nlp(language: str):
    """Load (and cache) a spaCy language model.  Returns None on failure."""
    if language in _nlp_cache:
        return _nlp_cache[language]

    model_name = _SPACY_MODEL_MAP.get(language)
    if not model_name:
        logger.debug("No spaCy model registered for language '%s'", language)
        _nlp_cache[language] = None
        return None

    try:
        import spacy

        nlp = spacy.load(model_name)
        _nlp_cache[language] = nlp
        return nlp
    except OSError:
        logger.warning(
            "spaCy model '%s' not installed. Run: python -m spacy download %s",
            model_name,
            model_name,
        )
        _nlp_cache[language] = None
        return None
    except Exception as exc:
        logger.error("Failed to load spaCy model '%s': %s", model_name, exc)
        _nlp_cache[language] = None
        return None


def _normalise(text: str) -> str:
    """Lower-case and strip non-alphabetic (and non-digit) characters."""
    return re.sub(r"[^\w]", "", text.lower().strip())


def _uses_wikiner_labels(nlp) -> bool:
    """True when the pipeline tags entities with the WikiNER set (PER, ...)."""
    return any(
        "PER" in nlp.get_pipe(name).labels
        for name in _NER_COMPONENTS
        if name in nlp.pipe_names
    )


def _extract_concepts(text: str, language: str) -> set[str]:
    """
    Extract a set of meaningful concepts from *text* written in *language*.

    Priority:
    1. Named-entity surface forms (see _TARGET_ENT_TYPES)
    2. Lemmatised PROPN tokens not already captured by NER
    3. Lemmatised NOUN / ADJ tokens (only when NER is unavailable as fallback)

    Returns normalised (lowercased, stripped) concepts with length >= 3.
    """
    nlp = _load_nlp(language)
    if nlp is None:
        # Fallback: split on spaces, keep tokens >= 4 chars that start uppercase
        tokens = {_normalise(t) for t in text.split() if len(t) >= 4 and t[0].isupper()}
        return {t for t in tokens if len(t) >= _MIN_KEYWORD_LENGTH}

    doc = nlp(text)

    concepts: set[str] = set()

    # The small WikiNER models often tag capitalised sentence openers as
    # entities of any label ("Además" as PER or LOC, "Durante el verano" as
    # MISC).  Real people, places, organisations and titles almost always
    # contain a proper noun, so require one.  OntoNotes models (English) are
    # left alone because labels like NORP ("Spanish") are adjectives.
    require_propn = _uses_wikiner_labels(nlp)

    # Named entities (highest priority)
    for ent in doc.ents:
        if ent.label_ in _TARGET_ENT_TYPES:
            if require_propn and not any(t.pos_ == "PROPN" for t in ent):
                continue
            norm = _normalise(ent.text)
            if len(norm) >= _MIN_KEYWORD_LENGTH:
                concepts.add(norm)

    # Proper nouns not already captured by a named entity span
    ent_start_tokens = {t.i for ent in doc.ents for t in ent}
    for token in doc:
        if token.i in ent_start_tokens:
            continue
        if token.pos_ == "PROPN" and not token.is_stop and token.is_alpha:
            norm = _normalise(token.lemma_)
            if len(norm) >= _MIN_KEYWORD_LENGTH:
                concepts.add(norm)

    # If nothing was found (very short or purely numeric text), also scan nouns
    if not concepts:
        for token in doc:
            if token.pos_ in {"NOUN", "ADJ"} and not token.is_stop and token.is_alpha:
                norm = _normalise(token.lemma_)
                if len(norm) >= _MIN_KEYWORD_LENGTH:
                    concepts.add(norm)

    return concepts


def _levenshtein_similarity(a: str, b: str) -> float:
    """
    Compute normalised Levenshtein similarity in [0, 1].

    Replicates the logic already in similarity_scoring.py so we avoid a
    circular dependency from within the services package.
    """
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0

    # Classic DP edit distance
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev[j - 1] + cost)

    edit_distance = dp[lb]
    return 1.0 - edit_distance / max(la, lb)


def _is_matched_cross_lang(
    keyword: str,
    other_concepts: set[str],
    threshold: float = _CROSS_LANG_MATCH_THRESHOLD,
) -> bool:
    """
    Return True if *keyword* has a counterpart in *other_concepts* that is
    similar enough to count as "the same concept" across languages.

    We first try exact match, then fuzzy Levenshtein similarity.
    """
    if keyword in other_concepts:
        return True
    for other in other_concepts:
        if _levenshtein_similarity(keyword, other) >= threshold:
            return True
    return False


def extract_exclusive_keywords(
    source_text: str,
    target_text: str,
    source_lang: str,
    target_lang: str,
) -> tuple[list[str], list[str]]:
    """
    For a matched paragraph pair, return the concepts that are distinctive
    to each side.

    Parameters
    ----------
    source_text : str
        Paragraph from the source article.
    target_text : str
        Matched paragraph from the target article.
    source_lang : str
        ISO 639-1 code for the source article language (e.g. ``"en"``).
    target_lang : str
        ISO 639-1 code for the target article language (e.g. ``"fr"``).

    Returns
    -------
    source_exclusive : List[str]
        Concepts present in *source_text* but absent from *target_text*.
    target_exclusive : List[str]
        Concepts present in *target_text* but absent from *source_text*.
    """
    if not source_text or not target_text:
        return [], []

    try:
        source_concepts = _extract_concepts(source_text, source_lang)
        target_concepts = _extract_concepts(target_text, target_lang)
    except Exception as exc:
        logger.error("Keyword extraction failed: %s", exc)
        return [], []

    source_exclusive: list[str] = []
    target_exclusive: list[str] = []

    same_language = source_lang == target_lang

    for kw in sorted(source_concepts):
        if same_language:
            if kw not in target_concepts:
                source_exclusive.append(kw)
        else:
            if not _is_matched_cross_lang(kw, target_concepts):
                source_exclusive.append(kw)

    for kw in sorted(target_concepts):
        if same_language:
            if kw not in source_concepts:
                target_exclusive.append(kw)
        else:
            if not _is_matched_cross_lang(kw, source_concepts):
                target_exclusive.append(kw)

    return source_exclusive, target_exclusive
