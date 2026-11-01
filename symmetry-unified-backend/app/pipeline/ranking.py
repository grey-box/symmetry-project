from dataclasses import dataclass, field, replace

from .models import Difference
from .v2_terms import SCHEMA_LABELS

# How much each API v2 label matters: a contradiction most, a statement that cannot
# be checked least. A supported statement is not a difference, so it scores zero.
LABEL_WEIGHTS: dict[str, float] = {
    "contradicted": 1.0,
    "not_found": 0.8,
    "partial": 0.6,
    "unverifiable": 0.4,
    "supported": 0.0,
}


# Tunable settings for how significance is scored.
@dataclass(frozen=True)
class RankingConfig:
    label_weights: dict[str, float] = field(default_factory=lambda: dict(LABEL_WEIGHTS))
    unknown_confidence: float = 0.5
    long_span_chars: int = 200

    def __post_init__(self) -> None:
        if self.long_span_chars <= 0:
            raise ValueError("long_span_chars must be positive")
        if not 0.0 <= self.unknown_confidence <= 1.0:
            raise ValueError("unknown_confidence must be between 0 and 1")
        unknown = sorted(set(self.label_weights) - set(SCHEMA_LABELS))
        if unknown:
            raise ValueError(f"label_weights has unknown labels: {unknown}")
        if any(not 0.0 <= w <= 1.0 for w in self.label_weights.values()):
            raise ValueError("label weights must be between 0 and 1")


# Scores one difference from 0 to 1: label weight x confidence x how much text it covers.
def score_difference(difference: Difference, config: RankingConfig) -> float:
    weight = config.label_weights.get(difference.schema_label, 0.0)
    confidence = (
        config.unknown_confidence
        if difference.confidence is None
        else difference.confidence
    )
    span = max(len(difference.source_span or ""), len(difference.target_span or ""))
    coverage = min(1.0, span / config.long_span_chars)
    return round(weight * confidence * (0.5 + 0.5 * coverage), 4)


# Orders differences from most to least significant and numbers them from 1.
# Differences that score zero (supported statements) are left out. Equal scores keep
# the order the strategies reported them in. The input list is not changed.
def rank_differences(
    differences: list[Difference], config: RankingConfig | None = None
) -> list[Difference]:
    config = config or RankingConfig()
    scored = [replace(d, significance=score_difference(d, config)) for d in differences]
    kept = [d for d in scored if d.significance > 0.0]
    kept.sort(key=lambda d: -d.significance)
    return [replace(d, rank=position) for position, d in enumerate(kept, start=1)]
