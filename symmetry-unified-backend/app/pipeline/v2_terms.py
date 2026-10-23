import asyncio
import re

from app.strategies import (
    StrategyConfigError,
    StrategyError,
    StrategyInputError,
    UnknownStrategyError,
)

# Statement labels the published API v2 schema allows.
SCHEMA_LABELS = ("supported", "partial", "contradicted", "not_found", "unverifiable")

# Strategy-specific labels that mean one of the schema labels.
_LABEL_ALIASES = {
    "no_match_in_target": "not_found",
    "no_match_in_source": "not_found",
    "missing_in_target": "not_found",
}


# Maps a strategy's own label onto the schema label list; unknown labels are unverifiable.
def to_schema_label(label: str) -> str:
    cleaned = label.strip().lower()
    if cleaned in SCHEMA_LABELS:
        return cleaned
    return _LABEL_ALIASES.get(cleaned, "unverifiable")


# Returns the (error code, scope) pair the API v2 error model uses for a failure.
def classify_error(exc: BaseException) -> tuple[str, str]:
    if isinstance(exc, UnknownStrategyError):
        return "unsupported_strategy", "request"
    if isinstance(exc, (StrategyConfigError, StrategyInputError)):
        return "invalid_request", "request"
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "engine_timeout", "engine"
    return "internal_error", "request"


# Builds the error entry stored in a pipeline result, with API v2 code and scope.
def error_entry(exc: StrategyError, strategy: str = "") -> dict[str, object]:
    entry = exc.to_dict()
    entry["code"], entry["scope"] = classify_error(exc)
    if strategy and not entry.get("strategy"):
        entry["strategy"] = strategy
    return entry


# Finds a snippet in the original text and returns its (start, end) character offsets.
def find_span(text: str, snippet: str | None, taken: set[int]) -> tuple[int, int] | None:
    if not snippet or not snippet.strip():
        return None
    start = text.find(snippet)
    while start != -1:
        if start not in taken:
            taken.add(start)
            return start, start + len(snippet)
        start = text.find(snippet, start + 1)
    # Fall back to a match that ignores differences in whitespace between words.
    pattern = re.compile(r"\s+".join(re.escape(word) for word in snippet.split()))
    for match in pattern.finditer(text):
        if match.start() not in taken:
            taken.add(match.start())
            return match.span()
    return None
