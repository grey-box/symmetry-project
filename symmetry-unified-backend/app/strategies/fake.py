from .base import ComparisonStrategy, Finding, StrategyInput, StrategyResult
from .errors import StrategyExecutionError
from .registry import register_strategy


# Offline test strategy that scores word overlap, or fails on demand.
@register_strategy("fake")
class FakeStrategy(ComparisonStrategy):
    description = "Word overlap between the two texts (used for tests)."

    async def compare(self, request: StrategyInput) -> StrategyResult:
        if self.config.get("fail"):
            raise StrategyExecutionError("simulated failure", strategy=self.name)
        source = set(request.source_text.lower().split())
        target = set(request.target_text.lower().split())
        score = len(source & target) / len(source | target)
        findings = [
            Finding(label="missing_in_target", source_span=word)
            for word in sorted(source - target)
        ]
        return StrategyResult(strategy=self.name, score=score, findings=findings)
