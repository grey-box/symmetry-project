from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# The two texts a strategy compares, plus optional context such as language.
@dataclass(frozen=True)
class StrategyInput:
    source_text: str
    target_text: str
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_text or not self.source_text.strip():
            raise ValueError("source_text must not be empty")
        if not self.target_text or not self.target_text.strip():
            raise ValueError("target_text must not be empty")


# One observation a strategy reports, such as a statement label or a disagreement.
@dataclass(frozen=True)
class Finding:
    label: str
    message: str = ""
    confidence: float | None = None
    source_span: str | None = None
    target_span: str | None = None
    evidence: str | None = None

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("label must not be empty")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


# Strategy-neutral output returned by every strategy.
@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    score: float | None = None
    findings: list[Finding] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")


# The single interface the pipeline uses to run any comparison strategy.
class ComparisonStrategy(ABC):
    name: str = ""
    description: str = ""
    requires: tuple[str, ...] = ()

    def __init__(self, **config: Any) -> None:
        self.config = config

    # Compares the two texts and raises a StrategyError subclass on any failure.
    @abstractmethod
    async def compare(self, request: StrategyInput) -> StrategyResult: ...
