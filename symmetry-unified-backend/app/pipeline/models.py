from dataclasses import dataclass, field

from app.strategies import Finding, StrategyResult

from .v2_terms import to_schema_label

MAX_TEXT_CHARS = 100_000


# One text to compare, from any source. The text is kept exactly as given so that
# character offsets in the results point into the original. The optional id, kind,
# url and revision_id describe the source for the API layer.
@dataclass(frozen=True)
class TextInput:
    text: str
    label: str = ""
    language: str | None = None
    metadata: dict = field(default_factory=dict)
    id: str | None = None
    kind: str | None = None
    url: str | None = None
    revision_id: int | None = None

    def __post_init__(self) -> None:
        if not self.text or not self.text.strip():
            raise ValueError("text must not be empty")
        if len(self.text) > MAX_TEXT_CHARS:
            raise ValueError(f"text must not exceed {MAX_TEXT_CHARS} characters")


# Names one strategy to run, with its settings and a time limit.
@dataclass(frozen=True)
class StrategySpec:
    name: str
    config: dict = field(default_factory=dict)
    timeout_s: float = 120.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")


# One reported difference, ready to be ranked by significance. The label is the
# strategy's own; schema_label is the matching API v2 label. The ranges are
# (start, end) character offsets into the original source or target text, or None
# when the reported text cannot be found there. side says which text the
# difference belongs to.
@dataclass(frozen=True)
class Difference:
    strategy: str
    label: str
    message: str = ""
    confidence: float | None = None
    source_span: str | None = None
    target_span: str | None = None
    evidence: str | None = None
    significance: float = 0.0
    rank: int | None = None
    schema_label: str = "unverifiable"
    side: str | None = None
    source_range: tuple[int, int] | None = None
    target_range: tuple[int, int] | None = None

    # Builds a difference from a strategy finding.
    @classmethod
    def from_finding(cls, strategy: str, finding: Finding) -> "Difference":
        if finding.source_span:
            side = "source"
        elif finding.target_span:
            side = "target"
        else:
            side = None
        return cls(
            strategy=strategy,
            label=finding.label,
            message=finding.message,
            confidence=finding.confidence,
            source_span=finding.source_span,
            target_span=finding.target_span,
            evidence=finding.evidence,
            schema_label=to_schema_label(finding.label),
            side=side,
        )


# Everything one comparison produced, including per-strategy errors.
@dataclass(frozen=True)
class PipelineResult:
    source: TextInput
    target: TextInput
    results: list[StrategyResult] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    differences: list[Difference] = field(default_factory=list)
    elapsed_ms: float = 0.0

    # True when every requested strategy finished without an error.
    @property
    def ok(self) -> bool:
        return not self.errors

    # Names of the strategies that produced a result, in request order.
    @property
    def strategy_names(self) -> list[str]:
        return [result.strategy for result in self.results]
