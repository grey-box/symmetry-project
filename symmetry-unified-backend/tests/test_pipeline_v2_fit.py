import asyncio
from typing import get_args

import pytest

from app.pipeline import (
    SCHEMA_LABELS,
    ComparisonPipeline,
    Difference,
    PipelineConfigError,
    StrategySpec,
    TextInput,
    locate_differences,
    to_schema_label,
)
from app.pipeline.v2_terms import find_span
from app.strategies import (
    ComparisonStrategy,
    Finding,
    StrategyInputError,
    StrategyResult,
    register_strategy,
    registry,
)

SOURCE = "Cats purr.\nDogs bark loudly.  Birds sing."
TARGET = "Cats purr. Fish swim."


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


# Gives each test its own copy of the registry so test strategies do not leak.
@pytest.fixture
def isolated_registry(monkeypatch):
    monkeypatch.setattr(registry, "_STRATEGIES", dict(registry._STRATEGIES))


# Registers a strategy that reports the given findings.
def register_reporter(name, findings):
    @register_strategy(name)
    class Reporter(ComparisonStrategy):
        async def compare(self, request):
            return StrategyResult(strategy=self.name, score=0.5, findings=findings)


# Differences carry character offsets into the original texts.
@pytest.mark.unit
def test_differences_get_offsets(isolated_registry):
    register_reporter(
        "reporter",
        [
            Finding(label="no_match_in_target", source_span="Dogs bark loudly."),
            Finding(label="no_match_in_source", target_span="Fish swim."),
        ],
    )
    result = run(
        ComparisonPipeline().run(TextInput(SOURCE), TextInput(TARGET), ["reporter"])
    )
    first, second = result.differences
    assert SOURCE[slice(*first.source_range)] == "Dogs bark loudly."
    assert TARGET[slice(*second.target_range)] == "Fish swim."
    assert (first.side, second.side) == ("source", "target")


# Text that spans a changed whitespace run is still located in the original.
@pytest.mark.unit
def test_offsets_ignore_whitespace_differences():
    assert find_span(SOURCE, "Dogs bark loudly. Birds sing.", set()) == (
        SOURCE.index("Dogs"),
        len(SOURCE),
    )


# Repeated text is matched to its next unused position, in report order.
@pytest.mark.unit
def test_repeated_text_gets_distinct_offsets():
    text = "Hi there. Hi there."
    diffs = [
        Difference(strategy="s", label="x", source_span="Hi there."),
        Difference(strategy="s", label="x", source_span="Hi there."),
    ]
    first, second = locate_differences(diffs, text, text)
    assert first.source_range == (0, 9) and second.source_range == (10, 19)


# Text the original does not contain gets no offsets instead of a wrong guess.
@pytest.mark.unit
def test_missing_text_has_no_offsets():
    assert find_span(SOURCE, "never said this", set()) is None
    assert find_span(SOURCE, "", set()) is None
    assert find_span(SOURCE, None, set()) is None


# Strategy labels map onto the five labels the API v2 schema allows.
@pytest.mark.unit
def test_labels_map_to_schema_labels():
    assert to_schema_label("no_match_in_target") == "not_found"
    assert to_schema_label("no_match_in_source") == "not_found"
    assert to_schema_label("missing_in_target") == "not_found"
    assert to_schema_label("Contradicted") == "contradicted"
    assert to_schema_label("something_new") == "unverifiable"
    finding = Finding(label="no_match_in_target", source_span="x")
    diff = Difference.from_finding("s", finding)
    assert diff.label == "no_match_in_target" and diff.schema_label == "not_found"


# Source details travel with the input so the API layer can describe it.
@pytest.mark.unit
def test_input_keeps_source_details():
    item = TextInput(
        "text",
        id="a",
        kind="wikipedia",
        url="https://en.wikipedia.org/wiki/Cat",
        revision_id=7,
    )
    result = run(ComparisonPipeline().run(item, TextInput("text"), ["fake"]))
    assert result.source.kind == "wikipedia" and result.source.revision_id == 7
    assert result.strategy_names == ["fake"]


# Failures carry an API v2 error code and scope.
@pytest.mark.unit
def test_errors_carry_code_and_scope(isolated_registry):
    @register_strategy("bad_input")
    class BadInput(ComparisonStrategy):
        async def compare(self, request):
            raise StrategyInputError("unusable", strategy=self.name)

    @register_strategy("slow")
    class Slow(ComparisonStrategy):
        async def compare(self, request):
            await asyncio.sleep(1)

    @register_strategy("crash")
    class Crash(ComparisonStrategy):
        async def compare(self, request):
            raise RuntimeError("boom")

    result = run(
        ComparisonPipeline().run(
            TextInput("a"),
            TextInput("b"),
            ["bad_input", StrategySpec("slow", timeout_s=0.01), "crash"],
        )
    )
    by_name = {e["strategy"]: e for e in result.errors}
    assert by_name["bad_input"]["code"] == "invalid_request"
    assert by_name["slow"]["code"] == "engine_timeout"
    assert by_name["slow"]["scope"] == "engine" and by_name["slow"]["retryable"]
    assert by_name["crash"]["code"] == "internal_error"


# Request-level problems carry the code the API should answer with.
@pytest.mark.unit
def test_config_errors_carry_codes():
    pipeline = ComparisonPipeline()
    with pytest.raises(PipelineConfigError) as unknown:
        run(pipeline.run(TextInput("a"), TextInput("b"), ["nope"]))
    assert unknown.value.to_dict()["code"] == "unsupported_strategy"
    with pytest.raises(PipelineConfigError) as empty:
        run(pipeline.run(TextInput("a"), TextInput("b"), []))
    assert empty.value.to_dict()["code"] == "invalid_request"


# The pipeline still accepts a list, so one strategy per request is an API rule.
@pytest.mark.unit
def test_pipeline_accepts_one_or_several_strategies():
    one = run(ComparisonPipeline().run(TextInput("a"), TextInput("b"), ["fake"]))
    assert one.strategy_names == ["fake"]


# The pipeline's values fit the published API v2 models (skipped until they land).
@pytest.mark.unit
def test_values_fit_api_v2_models(isolated_registry):
    common = pytest.importorskip("app.models.v2.common")
    errors = pytest.importorskip("app.models.v2.errors")
    response = pytest.importorskip("app.models.v2.response")
    assert set(SCHEMA_LABELS) == set(get_args(response.StatementLabel))
    assert {"text", "document", "wikipedia", "llm_output"} == set(
        get_args(common.SourceKind)
    )

    register_reporter(
        "reporter", [Finding(label="no_match_in_target", source_span="Dogs bark")]
    )

    @register_strategy("slow")
    class Slow(ComparisonStrategy):
        async def compare(self, request):
            await asyncio.sleep(1)

    result = run(
        ComparisonPipeline().run(
            TextInput(SOURCE), TextInput(TARGET), ["reporter", StrategySpec("slow", timeout_s=0.01)]
        )
    )
    diff = result.differences[0]
    span = common.Span(start=diff.source_range[0], end=diff.source_range[1])
    assert SOURCE[span.start : span.end] == "Dogs bark"
    assert diff.schema_label in get_args(response.StatementLabel)

    entry = result.errors[0]
    detail = errors.ErrorDetail(
        code=entry["code"],
        message=entry["message"],
        scope=entry["scope"],
        source_id=None,
        engine_id=None,
        retryable=entry["retryable"],
        details=None,
    )
    assert detail.code == "engine_timeout"

    with pytest.raises(PipelineConfigError) as unknown:
        run(ComparisonPipeline().run(TextInput("a"), TextInput("b"), ["nope"]))
    config = unknown.value.to_dict()
    assert config["code"] in get_args(errors.ErrorCode)
