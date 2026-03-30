"""
Central settings module — single source of truth for all configurable thresholds.

Values are read from the environment (or .env file) with sensible defaults.
Services import from here instead of hardcoding constants directly.
"""

from starlette.config import Config

_config = Config(".env")

# ---------------------------------------------------------------------------
# Semantic / cosine similarity
# ---------------------------------------------------------------------------

# Global default cosine-similarity threshold used when no per-request value is
# supplied.  Applies to both semantic_comparison.py and section_comparison.py.
SIMILARITY_THRESHOLD: float = _config("SIMILARITY_THRESHOLD", cast=float, default=0.65)

# ---------------------------------------------------------------------------
# Levenshtein disambiguation
# ---------------------------------------------------------------------------

# When the top-2 paragraph candidates have cosine-similarity scores within
# this margin, Levenshtein distance is used as a tiebreaker.
LEVENSHTEIN_DISAMBIGUATION_MARGIN: float = _config(
    "LEVENSHTEIN_DISAMBIGUATION_MARGIN", cast=float, default=0.08
)

# ---------------------------------------------------------------------------
# Language-family word-match thresholds (similarity_scoring.py)
# ---------------------------------------------------------------------------

# Threshold applied when both languages belong to the same family.
FAMILY_THRESHOLD_SAME: float = _config(
    "FAMILY_THRESHOLD_SAME", cast=float, default=0.50
)

# Threshold applied when both languages are Indo-European but different branches
# (e.g. Germanic vs Romance).
FAMILY_THRESHOLD_IE_BRANCHES: float = _config(
    "FAMILY_THRESHOLD_IE_BRANCHES", cast=float, default=0.60
)

# Threshold applied when the two languages belong to completely different families.
FAMILY_THRESHOLD_UNRELATED: float = _config(
    "FAMILY_THRESHOLD_UNRELATED", cast=float, default=0.70
)

# Threshold used when one or both language families are unknown.
FAMILY_THRESHOLD_UNKNOWN: float = _config(
    "FAMILY_THRESHOLD_UNKNOWN", cast=float, default=0.70
)

# ---------------------------------------------------------------------------
# Language-family band thresholds (similarity_scoring.py)
# ---------------------------------------------------------------------------
# Each tuple is (very_close, same_branch_high, same_family_low, unrelated_low)

BAND_SAME_FAMILY: tuple = (
    _config("BAND_SAME_FAMILY_VERY_CLOSE", cast=float, default=0.75),
    _config("BAND_SAME_FAMILY_BRANCH", cast=float, default=0.55),
    _config("BAND_SAME_FAMILY_DISTANT", cast=float, default=0.30),
    _config("BAND_SAME_FAMILY_UNRELATED", cast=float, default=0.15),
)

BAND_IE_BRANCHES: tuple = (
    _config("BAND_IE_VERY_CLOSE", cast=float, default=0.80),
    _config("BAND_IE_BRANCH", cast=float, default=0.60),
    _config("BAND_IE_DISTANT", cast=float, default=0.35),
    _config("BAND_IE_UNRELATED", cast=float, default=0.20),
)

BAND_DIFFERENT_FAMILIES: tuple = (
    _config("BAND_DIFF_VERY_CLOSE", cast=float, default=0.85),
    _config("BAND_DIFF_BRANCH", cast=float, default=0.65),
    _config("BAND_DIFF_DISTANT", cast=float, default=0.40),
    _config("BAND_DIFF_UNRELATED", cast=float, default=0.25),
)

BAND_UNKNOWN: tuple = (
    _config("BAND_UNK_VERY_CLOSE", cast=float, default=0.85),
    _config("BAND_UNK_BRANCH", cast=float, default=0.60),
    _config("BAND_UNK_DISTANT", cast=float, default=0.25),
    _config("BAND_UNK_UNRELATED", cast=float, default=0.10),
)
