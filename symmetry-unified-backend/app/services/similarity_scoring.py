"""
Similarity scoring module for article comparison.

Computes lexical similarity between articles using word-to-word Levenshtein distance,
applies threshold bands, and detects loanword borrowing to reduce false positives.
Supports cross-language comparison with language family awareness and script normalization.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum
import re

from app.core.settings import (
    FAMILY_THRESHOLD_SAME,
    FAMILY_THRESHOLD_IE_BRANCHES,
    FAMILY_THRESHOLD_UNRELATED,
    FAMILY_THRESHOLD_UNKNOWN,
    BAND_SAME_FAMILY,
    BAND_IE_BRANCHES,
    BAND_DIFFERENT_FAMILIES,
    BAND_UNKNOWN,
)


# Latinate suffixes for loanword detection (no leading hyphens)
LOANWORD_SUFFIXES = {
    "tion",
    "sion",
    "ment",
    "idad",
    "ismo",
    "ness",
    "ance",
    "ence",
    "able",
    "ible",
    "ous",
    "ive",
    "ity",
    "ty",
    "ure",
    "age",
    "ful",
    "ing",
    "ed",
    "al",
    "ic",
    "ical",
    "less",
    "ward",
}


# Language families for linguistic classification
class LanguageFamily(Enum):
    """Major language families."""

    INDO_EUROPEAN = "indo_european"
    GERMANIC = "germanic"
    ROMANCE = "romance"
    SLAVIC = "slavic"
    SINO_TIBETAN = "sino_tibetan"
    AFRO_ASIATIC = "afro_asiatic"
    ALTAIC = "altaic"
    TAI_KADAI = "tai_kadai"
    DRAVIDIAN = "dravidian"
    AUSTROASIATIC = "austroasiatic"
    AUSTRONESIAN = "austronesian"
    NIGER_CONGO = "niger_congo"
    UNKNOWN = "unknown"


# Language to family mapping
LANGUAGE_FAMILIES: Dict[str, LanguageFamily] = {
    # Germanic
    "english": LanguageFamily.GERMANIC,
    "german": LanguageFamily.GERMANIC,
    "dutch": LanguageFamily.GERMANIC,
    "swedish": LanguageFamily.GERMANIC,
    "norwegian": LanguageFamily.GERMANIC,
    "danish": LanguageFamily.GERMANIC,
    "icelandic": LanguageFamily.GERMANIC,
    # Romance
    "spanish": LanguageFamily.ROMANCE,
    "french": LanguageFamily.ROMANCE,
    "italian": LanguageFamily.ROMANCE,
    "portuguese": LanguageFamily.ROMANCE,
    "romanian": LanguageFamily.ROMANCE,
    "catalan": LanguageFamily.ROMANCE,
    # Slavic
    "russian": LanguageFamily.SLAVIC,
    "ukrainian": LanguageFamily.SLAVIC,
    "polish": LanguageFamily.SLAVIC,
    "czech": LanguageFamily.SLAVIC,
    "slovak": LanguageFamily.SLAVIC,
    "bulgarian": LanguageFamily.SLAVIC,
    "serbian": LanguageFamily.SLAVIC,
    "croatian": LanguageFamily.SLAVIC,
    "slovene": LanguageFamily.SLAVIC,
    "belarusian": LanguageFamily.SLAVIC,
    "macedonian": LanguageFamily.SLAVIC,
    # Sino-Tibetan
    "mandarin": LanguageFamily.SINO_TIBETAN,
    "cantonese": LanguageFamily.SINO_TIBETAN,
    "chinese": LanguageFamily.SINO_TIBETAN,
    "tibetan": LanguageFamily.SINO_TIBETAN,
    # Afro-Asiatic
    "arabic": LanguageFamily.AFRO_ASIATIC,
    "hebrew": LanguageFamily.AFRO_ASIATIC,
    "amharic": LanguageFamily.AFRO_ASIATIC,
    # Altaic
    "turkish": LanguageFamily.ALTAIC,
    "mongolian": LanguageFamily.ALTAIC,
    "korean": LanguageFamily.ALTAIC,
    # Dravidian
    "tamil": LanguageFamily.DRAVIDIAN,
    "telugu": LanguageFamily.DRAVIDIAN,
    "kannada": LanguageFamily.DRAVIDIAN,
    "malayalam": LanguageFamily.DRAVIDIAN,
    # Austronesian
    "tagalog": LanguageFamily.AUSTRONESIAN,
    "indonesian": LanguageFamily.AUSTRONESIAN,
    "malay": LanguageFamily.AUSTRONESIAN,
    "javanese": LanguageFamily.AUSTRONESIAN,
    # Niger-Congo
    "swahili": LanguageFamily.NIGER_CONGO,
    "yoruba": LanguageFamily.NIGER_CONGO,
}


# Cyrillic to Latin transliteration mapping
CYRILLIC_TO_LATIN: Dict[str, str] = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    # Uppercase
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "G",
    "Д": "D",
    "Е": "E",
    "Ё": "Yo",
    "Ж": "Zh",
    "З": "Z",
    "И": "I",
    "Й": "Y",
    "К": "K",
    "Л": "L",
    "М": "M",
    "Н": "N",
    "О": "O",
    "П": "P",
    "Р": "R",
    "С": "S",
    "Т": "T",
    "У": "U",
    "Ф": "F",
    "Х": "H",
    "Ц": "Ts",
    "Ч": "Ch",
    "Ш": "Sh",
    "Щ": "Sch",
    "Ъ": "",
    "Ы": "Y",
    "Ь": "",
    "Э": "E",
    "Ю": "Yu",
    "Я": "Ya",
}


# Common Swadesh-100 meanings (simplified core vocabulary)
SWADESH_100 = {
    "I",
    "you",
    "he",
    "we",
    "they",
    "this",
    "that",
    "one",
    "two",
    "three",
    "hand",
    "foot",
    "head",
    "eye",
    "ear",
    "tooth",
    "bone",
    "blood",
    "skin",
    "meat",
    "fish",
    "bird",
    "dog",
    "cat",
    "fire",
    "water",
    "stone",
    "tree",
    "sun",
    "moon",
    "star",
    "earth",
    "sea",
    "mountain",
    "walk",
    "run",
    "eat",
    "drink",
    "sleep",
    "sit",
    "stand",
    "give",
    "take",
    "come",
    "go",
    "say",
    "know",
    "think",
    "see",
    "hear",
    "die",
    "live",
    "grow",
    "play",
    "laugh",
    "cry",
    "hunt",
    "fight",
    "kill",
    "blow",
    "swell",
    "full",
    "new",
    "old",
    "good",
    "bad",
    "long",
    "short",
    "hot",
    "cold",
    "wet",
    "dry",
    "fat",
    "thin",
    "big",
    "small",
    "dark",
    "light",
    "red",
    "white",
    "black",
    "green",
    "yellow",
    "blue",
    "black",
    "white",
    "red",
    "many",
    "few",
    "other",
    "same",
    "different",
    "far",
    "near",
    "above",
    "below",
    "right",
    "left",
    "front",
    "back",
    "middle",
}


@dataclass
class SimilarityScore:
    """Result of similarity comparison between two articles."""

    similarity_percent: float
    band_label: str
    confidence_flags: List[str]
    word_match_count: int
    total_words: int
    loanword_risk: str
    original_language: Optional[str] = None
    translated_language: Optional[str] = None
    original_language_family: Optional[str] = None
    translated_language_family: Optional[str] = None


def normalized_levenshtein_distance(s1: str, s2: str) -> float:
    """
    Compute normalized Levenshtein distance (0-1, where 1 = identical).
    Formula: 1 - (edit_distance / max_len)

    Args:
        s1: First string
        s2: Second string

    Returns:
        Normalized similarity score [0, 1]
    """
    if not s1 or not s2:
        return 0.0 if s1 != s2 else 1.0

    # Compute edit distance using dynamic programming
    len1, len2 = len(s1), len(s2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    edit_distance = dp[len1][len2]
    max_len = max(len1, len2)
    return 1 - (edit_distance / max_len)


def has_loanword_suffix(word: str) -> bool:
    """Check if word ends with a common Latinate suffix."""
    word_lower = word.lower()
    for suffix in LOANWORD_SUFFIXES:
        if word_lower.endswith(suffix):
            return True
    return False


def is_loanword_pair(word1: str, word2: str) -> bool:
    """Check if either word in a pair looks like a loanword."""
    return has_loanword_suffix(word1) or has_loanword_suffix(word2)


def transliterate_cyrillic(text: str) -> str:
    """Convert Cyrillic script to Latin for cross-script comparison."""
    result = ""
    for char in text:
        result += CYRILLIC_TO_LATIN.get(char, char)
    return result


def normalize_script(text: str, source_language: Optional[str] = None) -> str:
    """
    Normalize text script for comparison.
    Detects Cyrillic and converts to Latin transliteration.

    Args:
        text: Text to normalize
        source_language: Optional language hint

    Returns:
        Normalized text
    """
    # Check if text contains Cyrillic characters
    if any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in text):
        return transliterate_cyrillic(text)
    # Could add other script normalizations here (Arabic, CJK, etc.)
    return text


def get_language_family(language: str) -> LanguageFamily:
    """Get language family for a language code or name."""
    lang_lower = language.lower().strip()
    return LANGUAGE_FAMILIES.get(lang_lower, LanguageFamily.UNKNOWN)


def get_family_threshold(family_a: LanguageFamily, family_b: LanguageFamily) -> float:
    """
    Get recommended similarity threshold based on language families.
    Adjusted thresholds account for how different language families are.

    Returns:
        Recommended word_match_threshold (0-1)
    """
    if family_a == family_b and family_a != LanguageFamily.UNKNOWN:
        return FAMILY_THRESHOLD_SAME

    ie_branches = {
        LanguageFamily.GERMANIC,
        LanguageFamily.ROMANCE,
        LanguageFamily.SLAVIC,
    }

    if family_a in ie_branches and family_b in ie_branches:
        return FAMILY_THRESHOLD_IE_BRANCHES

    if family_a != LanguageFamily.UNKNOWN and family_b != LanguageFamily.UNKNOWN:
        return FAMILY_THRESHOLD_UNRELATED

    return FAMILY_THRESHOLD_UNKNOWN


def get_family_threshold_bands(
    family_a: LanguageFamily, family_b: LanguageFamily
) -> Tuple[float, float, float, float]:
    """
    Get adjusted similarity threshold bands for language families.

    Returns:
        (very_close_threshold, same_branch_high, same_family_low, unrelated_threshold)
    """
    if family_a == family_b and family_a != LanguageFamily.UNKNOWN:
        return BAND_SAME_FAMILY

    ie_branches = {
        LanguageFamily.GERMANIC,
        LanguageFamily.ROMANCE,
        LanguageFamily.SLAVIC,
    }
    if family_a in ie_branches and family_b in ie_branches:
        return BAND_IE_BRANCHES

    if family_a != LanguageFamily.UNKNOWN and family_b != LanguageFamily.UNKNOWN:
        return BAND_DIFFERENT_FAMILIES

    return BAND_UNKNOWN


def classify_band(
    similarity_percent: float,
    family_a: Optional[LanguageFamily] = None,
    family_b: Optional[LanguageFamily] = None,
) -> Tuple[str, str]:
    """
    Classify similarity percentage into linguistic bands.
    Optionally adjusts thresholds based on language families.

    Returns:
        (band_label, description)
    """
    # Get family-aware thresholds if families provided
    if family_a and family_b:
        very_close, same_branch, same_family, unrelated = get_family_threshold_bands(
            family_a, family_b
        )
    else:
        # Default thresholds
        very_close, same_branch, same_family, unrelated = 0.85, 0.60, 0.25, 0.10

    if similarity_percent >= very_close * 100:
        return ("very_close", "likely the same language or very close dialects")
    elif similarity_percent >= same_branch * 100:
        return ("same_branch", "likely same language family branch")
    elif similarity_percent >= same_family * 100:
        return ("same_family_distant", "possibly same family, needs more evidence")
    else:
        return ("unrelated", "likely unrelated language families or noisy data")


def score_article_pair(
    original_text: str,
    translated_text: str,
    word_match_threshold: Optional[float] = None,
    use_swadesh_filter: bool = False,
    downweight_loanwords: bool = True,
    original_language: Optional[str] = None,
    translated_language: Optional[str] = None,
) -> SimilarityScore:
    """
    Compute lexical similarity between two articles.

    Args:
        original_text: Original article text
        translated_text: Translated article text
        word_match_threshold: Threshold for word similarity (0-1). If None, auto-determined by language families.
        use_swadesh_filter: If True, only match Swadesh-100 core vocabulary
        downweight_loanwords: If True, count loanword matches as 0.5 instead of 1.0
        original_language: Optional language of original_text (e.g., 'english', 'russian')
        translated_language: Optional language of translated_text (e.g., 'french', 'spanish')

    Returns:
        SimilarityScore with similarity %, band, and confidence flags
    """
    # Detect language families
    family_a = (
        get_language_family(original_language)
        if original_language
        else LanguageFamily.UNKNOWN
    )
    family_b = (
        get_language_family(translated_language)
        if translated_language
        else LanguageFamily.UNKNOWN
    )

    # Normalize scripts for cross-script comparison
    original_text = normalize_script(original_text, original_language)
    translated_text = normalize_script(translated_text, translated_language)

    # Auto-determine word_match_threshold if not provided
    if word_match_threshold is None:
        word_match_threshold = get_family_threshold(family_a, family_b)
    # Tokenize to words (simple split on whitespace + punctuation)
    words_original = re.findall(r"\b\w+\b", original_text.lower())
    words_translated = re.findall(r"\b\w+\b", translated_text.lower())

    if not words_original or not words_translated:
        return SimilarityScore(
            similarity_percent=0.0,
            band_label="unknown",
            confidence_flags=["empty_text"],
            word_match_count=0,
            total_words=len(words_original) + len(words_translated),
            loanword_risk="unknown",
        )

    # Filter to Swadesh-100 if requested
    if use_swadesh_filter:
        words_original = [w for w in words_original if w in SWADESH_100]
        words_translated = [w for w in words_translated if w in SWADESH_100]

    # Build multiset of word pairs to compare
    # For simplicity, we'll compare each word in original_text to the best match in translated_text
    match_count = 0.0
    loanword_match_count = 0.0

    for word_orig in words_original:
        best_sim = 0.0
        best_is_loanword = False

        for word_trans in words_translated:
            sim = normalized_levenshtein_distance(word_orig, word_trans)
            if sim > best_sim:
                best_sim = sim
                best_is_loanword = is_loanword_pair(word_orig, word_trans)

        # Count as match if above threshold
        if best_sim >= word_match_threshold:
            weight = 1.0
            if downweight_loanwords and best_is_loanword:
                weight = 0.5
                loanword_match_count += 1
            match_count += weight

    total_words = len(words_original)
    lexical_similarity_percent = (
        (match_count / total_words * 100) if total_words > 0 else 0.0
    )

    # Classify band with family awareness
    band_label, band_desc = classify_band(
        lexical_similarity_percent, family_a, family_b
    )

    # Determine loanword risk
    loanword_risk = "high" if loanword_match_count > (match_count / 2) else "low"

    # Confidence flags
    confidence_flags = []
    if len(words_original) < 20:
        confidence_flags.append("low_data_original")
    if len(words_translated) < 20:
        confidence_flags.append("low_data_translated")
    if loanword_risk == "high":
        confidence_flags.append("loanword_risk_high")
    if use_swadesh_filter:
        confidence_flags.append("swadesh_filtered")

    return SimilarityScore(
        similarity_percent=round(lexical_similarity_percent, 2),
        band_label=band_label,
        confidence_flags=confidence_flags if confidence_flags else ["ok"],
        word_match_count=int(match_count),
        total_words=total_words,
        loanword_risk=loanword_risk,
        original_language=original_language,
        translated_language=translated_language,
        original_language_family=family_a.value
        if family_a != LanguageFamily.UNKNOWN
        else None,
        translated_language_family=family_b.value
        if family_b != LanguageFamily.UNKNOWN
        else None,
    )


def score_articles_batch(
    article_pairs: List[Tuple[str, str]],
    word_match_threshold: Optional[float] = None,
    use_swadesh_filter: bool = False,
    language_pairs: Optional[List[Tuple[str, str]]] = None,
) -> List[SimilarityScore]:
    """
    Score multiple article pairs in batch.

    Args:
        article_pairs: List of (original_text, translated_text) tuples
        word_match_threshold: Threshold for word similarity. If None, auto-determined per pair.
        use_swadesh_filter: Filter to Swadesh-100 vocabulary
        language_pairs: Optional list of (original_language, translated_language) tuples matching article_pairs

    Returns:
        List of SimilarityScore results
    """
    results = []
    language_pairs = language_pairs or []

    for i, (original_text, translated_text) in enumerate(article_pairs):
        original_language, translated_language = None, None
        if i < len(language_pairs):
            original_language, translated_language = language_pairs[i]

        score = score_article_pair(
            original_text,
            translated_text,
            word_match_threshold=word_match_threshold,
            use_swadesh_filter=use_swadesh_filter,
            original_language=original_language,
            translated_language=translated_language,
        )
        results.append(score)
    return results
