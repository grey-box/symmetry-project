import asyncio

import pytest

from app.pipeline import (
    MAX_TEXT_CHARS,
    ComparisonPipeline,
    Difference,
    PipelineConfigError,
    StrategySpec,
    TextInput,
    keep_order,
)
from app.strategies import (
    ComparisonStrategy,
    Finding,
    StrategyExecutionError,
    StrategyResult,
    register_strategy,
    registry,
)


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


# Compares two short texts with the given strategies.
def compare(strategies, a="the cat sat", b="the dog sat", pipeline=None):
    pipeline = pipeline or ComparisonPipeline()
    return run(pipeline.run(TextInput(a), TextInput(b), strategies))


# Gives each test its own copy of the registry so test strategies do not leak.
@pytest.fixture
def isolated_registry(monkeypatch):
    monkeypatch.setattr(registry, "_STRATEGIES", dict(registry._STRATEGIES))


# The pipeline compares two arbitrary texts and returns one assembled result.
@pytest.mark.unit
def test_compares_two_arbitrary_texts():
    result = compare(["fake"])
    assert result.ok and not result.errors
    assert [r.strategy for r in result.results] == ["fake"]
    assert result.results[0].score == pytest.approx(0.5)
    assert result.elapsed_ms >= 0


# Labels and language travel with the inputs so any source type can be compared.
@pytest.mark.unit
def test_inputs_keep_label_and_language():
    pipeline = ComparisonPipeline()
    source = TextInput("hello world", label="wikipedia:Cat", language="en")
    target = TextInput("hello there", label="llm:gpt", language="en")
    result = run(pipeline.run(source, target, ["fake"]))
    assert result.source.label == "wikipedia:Cat"
    assert result.target.label == "llm:gpt" and result.target.language == "en"


# Texts reach the strategies unchanged, so offsets in results match the originals.
@pytest.mark.unit
def test_text_is_not_modified():
    result = compare(["fake"], a="  one\r\ntwo  ", b="one\ntwo")
    assert result.source.text == "  one\r\ntwo  "
    assert result.target.text == "one\ntwo"


# Several strategies run together and results follow the request order.
@pytest.mark.unit
def test_runs_several_strategies_in_request_order(isolated_registry):
    @register_strategy("zzz_first")
    class First(ComparisonStrategy):
        async def compare(self, request):
            await asyncio.sleep(0.02)
            return StrategyResult(strategy=self.name, score=0.1)

    result = compare(["zzz_first", "fake"])
    assert [r.strategy for r in result.results] == ["zzz_first", "fake"]


# Per-strategy failures land in errors while other results are kept.
@pytest.mark.unit
def test_failure_is_isolated_and_reported(isolated_registry):
    @register_strategy("always_fails")
    class AlwaysFails(ComparisonStrategy):
        async def compare(self, request):
            raise StrategyExecutionError("boom", strategy=self.name)

    result = compare(["fake", "always_fails"])
    assert not result.ok
    assert [r.strategy for r in result.results] == ["fake"]
    assert result.errors[0]["strategy"] == "always_fails"
    assert result.errors[0]["error"] == "StrategyExecutionError"


# An unexpected exception inside a strategy is isolated too.
@pytest.mark.unit
def test_unexpected_exception_is_isolated(isolated_registry):
    @register_strategy("buggy")
    class Buggy(ComparisonStrategy):
        async def compare(self, request):
            raise KeyError("oops")

    result = compare(["fake", "buggy"])
    assert result.results[0].strategy == "fake"
    assert "KeyError" in result.errors[0]["message"]


# A strategy that returns the wrong type is reported as an error.
@pytest.mark.unit
def test_wrong_return_type_is_an_error(isolated_registry):
    @register_strategy("wrong_type")
    class WrongType(ComparisonStrategy):
        async def compare(self, request):
            return {"score": 1}

    result = compare(["wrong_type"])
    assert not result.results and result.errors[0]["strategy"] == "wrong_type"


# A strategy that exceeds its time limit is reported as retryable.
@pytest.mark.unit
def test_timeout_is_reported_as_retryable(isolated_registry):
    @register_strategy("slow")
    class Slow(ComparisonStrategy):
        async def compare(self, request):
            await asyncio.sleep(1)
            return StrategyResult(strategy=self.name, score=1.0)

    result = compare([StrategySpec("slow", timeout_s=0.01), "fake"])
    assert [r.strategy for r in result.results] == ["fake"]
    assert result.errors[0]["retryable"] is True
    assert "timed out" in result.errors[0]["message"]


# Strategy settings in a spec reach the strategy.
@pytest.mark.unit
def test_spec_config_reaches_the_strategy():
    result = compare([StrategySpec("fake", {"fail": True})])
    assert result.errors and result.errors[0]["message"] == "simulated failure"


# Bad requests fail before any strategy runs.
@pytest.mark.unit
def test_bad_requests_raise_config_errors():
    with pytest.raises(PipelineConfigError) as unknown:
        compare(["nope"])
    assert "available" in unknown.value.message
    with pytest.raises(PipelineConfigError):
        compare([])
    with pytest.raises(PipelineConfigError):
        compare(["fake", "fake"])


# Config errors convert to a dict the API layer can map to its error model.
@pytest.mark.unit
def test_config_error_to_dict():
    with pytest.raises(PipelineConfigError) as exc:
        compare([])
    assert exc.value.to_dict()["error"] == "PipelineConfigError"


# Empty, blank and oversized texts are rejected.
@pytest.mark.unit
def test_text_validation():
    with pytest.raises(ValueError):
        TextInput("   ")
    with pytest.raises(ValueError):
        TextInput("x" * (MAX_TEXT_CHARS + 1))
    TextInput("x" * MAX_TEXT_CHARS)
    with pytest.raises(ValueError):
        StrategySpec("")
    with pytest.raises(ValueError):
        StrategySpec("fake", timeout_s=0)


# Findings become differences tagged with their strategy, in strategy order.
@pytest.mark.unit
def test_findings_become_differences():
    pipeline = ComparisonPipeline(ranker=keep_order)
    result = compare(["fake"], a="a b c", b="a", pipeline=pipeline)
    assert [d.source_span for d in result.differences] == ["b", "c"]
    assert all(
        isinstance(d, Difference) and d.strategy == "fake" for d in result.differences
    )
    assert all(d.rank is None for d in result.differences)


# A ranker passed to the pipeline decides the order of the differences.
@pytest.mark.unit
def test_ranker_hook_orders_differences():
    def reverse(differences):
        return list(reversed(differences))

    pipeline = ComparisonPipeline(ranker=reverse)
    result = compare(["fake"], a="a b c", b="a", pipeline=pipeline)
    assert [d.source_span for d in result.differences] == ["c", "b"]


# Difference.from_finding copies every field of the finding.
@pytest.mark.unit
def test_difference_from_finding():
    finding = Finding(
        label="x",
        message="m",
        confidence=0.4,
        source_span="s",
        target_span="t",
        evidence="e",
    )
    d = Difference.from_finding("strat", finding)
    assert (d.strategy, d.label, d.message, d.confidence) == ("strat", "x", "m", 0.4)
    assert (d.source_span, d.target_span, d.evidence) == ("s", "t", "e")


# The pipeline can be used from several tasks at once.
@pytest.mark.unit
def test_pipeline_is_reusable_and_concurrent():
    pipeline = ComparisonPipeline()

    async def many():
        return await asyncio.gather(
            *(
                pipeline.run(TextInput("a b"), TextInput("a c"), ["fake"])
                for _ in range(5)
            )
        )

    assert all(r.ok for r in run(many()))
