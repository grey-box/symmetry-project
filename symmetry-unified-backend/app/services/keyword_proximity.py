"""
Keyword proximity analysis for matched paragraph pairs.

Extracts distinctive concepts/keywords from each side of a matched paragraph
pair and identifies those present in one article but absent in the other.

This forms a "second layer" of proximity on top of the semantic similarity
score: even when two paragraphs are semantically matched, one article may
discuss specific people, places, events, or topics that the other omits.

Cross-language strategy
-----------------------
Concepts are kept as lower-case phrases ("pablo ruiz picasso"), with French
and Italian elisions removed ("golfe d'Italie" becomes "golfe italie").  Two
concepts from different languages count as the same when, after removing
accents, any of these hold:

1. They are identical ("Málaga" / "Malaga").
2. The words of one are contained in the other ("picasso" and
   "pablo picasso" both match "pablo ruiz picasso").
3. Their Levenshtein similarity reaches _CROSS_LANG_MATCH_THRESHOLD, which
   catches close cognates ("barcelona" / "barcelone").
4. A multilingual sentence encoder (LaBSE) says they are translations
   ("spain" / "españa", "germany" / "deutschland").  This step only runs on
   what steps 1-3 left unmatched, and a pair must be each other's best
   candidate, because LaBSE also rates some neighbours highly
   ("sweden" / "switzerland" scores 0.89).
"""

import logging
import re
import unicodedata
from collections.abc import Callable, Sequence

import numpy as np

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
# similarity reaches this value (0 = completely different, 1 = identical).
# 0.75 let one edit in four letters through, which matched "iran" with
# "iraq" and "austria" with "australia".  Translations that differ by more
# than that ("france" / "francia") are left to the LaBSE step.
_CROSS_LANG_MATCH_THRESHOLD = 0.8

# Cosine similarity a pair of names needs under LaBSE to count as a
# translation.  Chosen from en/fr, en/es, en/de and en/pt comparisons of
# Picasso, Berlin, Barcelona and Lisbon: pairs from 0.80 up were nearly all
# right (france/frankreich 0.83, frederick ii/friedrich ii 0.84,
# iberian peninsula/península ibérica 0.83), and most pairs below 0.75
# were wrong (manet/mañach 0.73).  Different places that still score high:
# sweden/switzerland 0.89, austria/australia 0.83, barcino/barkeno 0.83.
# Requiring a mutual best match stops those when both names appear in the
# paragraph pair.
_NAME_TRANSLATION_THRESHOLD = 0.8

# Elided articles and prepositions ("l'", "d'", "dell'", "qu'") that are
# glued to the next word in French, Italian and Catalan.
_ELISION_RE = re.compile(
    r"\b(?:l|d|j|m|n|s|t|c|qu|jusqu|lorsqu|puisqu|dell|dall|nell|sull|all|coll|degl)['’ʼ]",
    re.IGNORECASE,
)
_POSSESSIVE_RE = re.compile(r"['’ʼ]s\b", re.IGNORECASE)

# Small words that join the parts of a name ("Gulf of Naples", "José Ruiz y
# Blasco").  They are ignored when comparing the words of two names.
# fmt: off
_CONNECTOR_WORDS: frozenset[str] = frozenset(
    {
        "the", "of", "and", "de", "del", "della", "delle", "di", "da", "do",
        "dos", "das", "du", "des", "la", "le", "les", "el", "los", "las", "lo",
        "il", "y", "e", "et", "und", "von", "van", "der", "den", "dem", "zu",
        "a", "al", "au", "aux",
    }
)
# fmt: on

# Anything that turns a list of strings into a 2-D array of embeddings.
NameEncoder = Callable[[list[str]], np.ndarray]

# spaCy NLP model cache
_nlp_cache: dict = {}

# LaBSE vectors for names already seen, keyed by the name.  Cleared when it
# grows past _NAME_EMBEDDING_CACHE_LIMIT so a long session can't fill memory.
_name_embedding_cache: dict[str, np.ndarray] = {}
_NAME_EMBEDDING_CACHE_LIMIT = 20_000


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
    """
    Turn a name into a lower-case phrase of plain words.

    "Pablo Ruiz Picasso" -> "pablo ruiz picasso", "golfe d'Italie" ->
    "golfe italie", "the Gulf of Naples" -> "gulf of naples".  Accents are
    kept so the keyword chips in the UI read naturally; _fold removes them
    for comparisons.
    """
    text = _POSSESSIVE_RE.sub("", text.lower())
    text = _ELISION_RE.sub("", text)
    words = re.sub(r"[\W_]+", " ", text).split()
    if words and words[0] == "the":
        words = words[1:]
    return " ".join(words)


def _fold(text: str) -> str:
    """Remove accents so "málaga" and "malaga" compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _content_words(concept: str) -> frozenset[str]:
    """The words of a concept without connectors, accents removed."""
    return frozenset(w for w in _fold(concept).split() if w not in _CONNECTOR_WORDS)


def _keep(concepts: set[str], text: str) -> None:
    """Normalise *text* and add it to *concepts* if it is long enough."""
    norm = _normalise(text)
    if len(norm.replace(" ", "")) >= _MIN_KEYWORD_LENGTH:
        concepts.add(norm)


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
    2. Runs of PROPN tokens not already captured by NER, kept together so
       "Pablo Ruiz Picasso" stays one name when NER misses it
    3. Lemmatised NOUN / ADJ tokens (only when NER is unavailable as fallback)

    Returns normalised phrases (see _normalise) with at least 3 letters.
    """
    nlp = _load_nlp(language)
    if nlp is None:
        # Fallback: split on spaces, keep tokens >= 4 chars that start uppercase
        concepts: set[str] = set()
        for t in text.split():
            if len(t) >= 4 and t[0].isupper():
                _keep(concepts, t)
        return concepts

    doc = nlp(text)

    concepts = set()

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
            _keep(concepts, ent.text)

    # Proper nouns not already captured by a named entity span.  Neighbouring
    # proper nouns are joined into one name.
    in_entity = {t.i for ent in doc.ents for t in ent}
    run: list = []

    def flush_run() -> None:
        # Taggers sometimes count a joining word as part of a name, such as
        # the Spanish "y" in an English text's "José Ruiz y Blasco".
        while run and run[0].lower_ in _CONNECTOR_WORDS:
            run.pop(0)
        while run and run[-1].lower_ in _CONNECTOR_WORDS:
            run.pop()
        if len(run) == 1:
            _keep(concepts, run[0].lemma_)
        elif run:
            _keep(concepts, " ".join(t.text for t in run))
        run.clear()

    for token in doc:
        is_name_part = (
            token.i not in in_entity
            and token.pos_ == "PROPN"
            and not token.is_stop
            and token.is_alpha
        )
        if is_name_part:
            run.append(token)
        else:
            flush_run()
    flush_run()

    # If nothing was found (very short or purely numeric text), also scan nouns
    if not concepts:
        for token in doc:
            if token.pos_ in {"NOUN", "ADJ"} and not token.is_stop and token.is_alpha:
                _keep(concepts, token.lemma_)

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


def _names_match(a: str, b: str, threshold: float) -> bool:
    """Spelling-based match between two normalised concepts (steps 1-3)."""
    folded_a, folded_b = _fold(a), _fold(b)
    if folded_a == folded_b:
        return True

    words_a, words_b = _content_words(a), _content_words(b)
    if words_a and words_b and (words_a <= words_b or words_b <= words_a):
        return True

    return _levenshtein_similarity(folded_a, folded_b) >= threshold


def _is_matched_cross_lang(
    keyword: str,
    other_concepts: set[str],
    threshold: float = _CROSS_LANG_MATCH_THRESHOLD,
) -> bool:
    """
    Return True if *keyword* has a counterpart in *other_concepts* that is
    spelled similarly enough to count as "the same concept" across
    languages.  Translations are handled separately by
    _pair_translated_names.
    """
    if keyword in other_concepts:
        return True
    return any(_names_match(keyword, other, threshold) for other in other_concepts)


def _embed_names(names: list[str], encode: NameEncoder) -> np.ndarray:
    """Unit-length embeddings for *names*, reusing cached vectors."""
    missing = [n for n in dict.fromkeys(names) if n not in _name_embedding_cache]
    if missing:
        if len(_name_embedding_cache) + len(missing) > _NAME_EMBEDDING_CACHE_LIMIT:
            _name_embedding_cache.clear()
        vectors = np.asarray(encode(missing), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.where(norms == 0, 1, norms)
        _name_embedding_cache.update(zip(missing, vectors))
    return np.stack([_name_embedding_cache[n] for n in names])


def _pair_translated_names(
    source_names: Sequence[str],
    target_names: Sequence[str],
    encode: NameEncoder,
    threshold: float = _NAME_TRANSLATION_THRESHOLD,
) -> set[tuple[str, str]]:
    """
    Pair names that LaBSE considers translations of each other.

    A pair is kept only when each name is the other's closest candidate and
    their cosine similarity reaches *threshold*.
    """
    if not source_names or not target_names:
        return set()

    source_vectors = _embed_names(list(source_names), encode)
    target_vectors = _embed_names(list(target_names), encode)
    similarity = source_vectors @ target_vectors.T

    pairs: set[tuple[str, str]] = set()
    best_target_for = similarity.argmax(axis=1)
    best_source_for = similarity.argmax(axis=0)
    for i, j in enumerate(best_target_for):
        if best_source_for[j] == i and similarity[i, j] >= threshold:
            pairs.add((source_names[i], target_names[j]))
    return pairs


def extract_exclusive_keywords(
    source_text: str,
    target_text: str,
    source_lang: str,
    target_lang: str,
    encode_names: NameEncoder | None = None,
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
    encode_names : callable, optional
        Multilingual encoder (LaBSE) used to match translated names such as
        "spain" / "españa" when the languages differ.  It is only called for
        names that spelling could not match.  Without it, translated names
        that are spelled differently stay exclusive.

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

    if source_lang == target_lang:
        return (
            sorted(source_concepts - target_concepts),
            sorted(target_concepts - source_concepts),
        )

    source_exclusive = [
        kw
        for kw in sorted(source_concepts)
        if not _is_matched_cross_lang(kw, target_concepts)
    ]
    target_exclusive = [
        kw
        for kw in sorted(target_concepts)
        if not _is_matched_cross_lang(kw, source_concepts)
    ]

    if encode_names is not None and source_exclusive and target_exclusive:
        try:
            pairs = _pair_translated_names(
                source_exclusive, target_exclusive, encode_names
            )
        except Exception as exc:
            logger.warning("Translated name matching failed: %s", exc)
            pairs = set()
        matched_source = {s for s, _ in pairs}
        matched_target = {t for _, t in pairs}
        source_exclusive = [kw for kw in source_exclusive if kw not in matched_source]
        target_exclusive = [kw for kw in target_exclusive if kw not in matched_target]

    return source_exclusive, target_exclusive
