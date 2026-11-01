import asyncio
import json

import pytest

pytest.importorskip("app.engines.base")  # skipped until the engines are merged

from app.engines import (
    AdapterTimeoutError,
    GenerationRequest,
    GenerationResult,
    ModelAdapter,
)
from app.strategies import (
    StrategyConfigError,
    StrategyExecutionError,
    StrategyInput,
    StrategyInputError,
    StrategyResult,
    get_strategy,
    list_strategies,
)
from app.strategies.factual_consistency import parse_verdict

REFERENCE = "Paris is the capital of France. The Seine flows through Paris."


# Fake engine that answers from a table keyed by words in the statement.
class ScriptedAdapter(ModelAdapter):
    provider = "scripted"

    def __init__(self, replies=None, fail=None, **config):
        super().__init__("scripted-model", **config)
        self.replies = replies or {}
        self.fail = fail
        self.in_flight = 0
        self.peak = 0
        self.prompts = []

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.prompts.append(request.prompt)
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(0.005)
            if self.fail:
                raise self.fail
            statement = request.prompt.split("Statement:\n", 1)[1]
            for key, reply in self.replies.items():
                if key in statement:
                    return GenerationResult(
                        text=reply, model=self.model_name, provider=self.provider
                    )
            raise AssertionError(f"no scripted reply for {statement!r}")
        finally:
            self.in_flight -= 1


# Builds the JSON reply an engine would give.
def verdict(label, confidence=0.9, evidence=""):
    return json.dumps({"label": label, "confidence": confidence, "evidence": evidence})


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


# Runs the strategy with a scripted engine.
def compare(replies, target, reference=REFERENCE, **config):
    adapter = config.pop("adapter", None) or ScriptedAdapter(replies)
    strategy = get_strategy("factual_consistency", model_adapter=adapter, **config)
    return run(strategy.compare(StrategyInput(reference, target)))


REPLIES = {
    "capital": verdict("supported", 0.95, "Paris is the capital of France."),
    "Rhine": verdict("contradicted", 0.8, "The Seine flows through Paris."),
    "population": verdict("not_found", 0.7),
}
TARGET = (
    "Paris is the capital of France. The Rhine flows through Paris. "
    "Its population is two million."
)


# The strategy is registered and needs an engine to be built.
@pytest.mark.unit
def test_registered_and_requires_an_engine():
    assert "factual_consistency" in list_strategies()
    with pytest.raises(StrategyConfigError):
        get_strategy("factual_consistency")


# It follows the strategy contract: a named result with a score from 0 to 1.
@pytest.mark.unit
def test_follows_the_strategy_contract():
    result = compare(REPLIES, TARGET)
    assert isinstance(result, StrategyResult)
    assert result.strategy == "factual_consistency"
    assert 0.0 <= result.score <= 1.0


# Each statement is labelled and the score is the share that is supported.
@pytest.mark.unit
def test_labels_statements_and_scores_supported_share():
    result = compare(REPLIES, TARGET)
    labels = [row["label"] for row in result.details["statements"]]
    assert labels == ["supported", "contradicted", "not_found"]
    assert result.score == pytest.approx(1 / 3)
    assert result.details["counts"] == {
        "supported": 1,
        "contradicted": 1,
        "not_found": 1,
    }


# Findings hold only what is not supported, with the statement and confidence.
@pytest.mark.unit
def test_findings_hold_only_unsupported_statements():
    result = compare(REPLIES, TARGET)
    assert [f.label for f in result.findings] == ["contradicted", "not_found"]
    contradicted = result.findings[0]
    assert contradicted.target_span == "The Rhine flows through Paris."
    assert contradicted.confidence == pytest.approx(0.8)
    assert contradicted.evidence == "The Seine flows through Paris."


# A quote that is not in the reference is dropped rather than shown as evidence.
@pytest.mark.unit
def test_made_up_evidence_is_dropped():
    replies = {"Rhine": verdict("contradicted", 0.9, "The Rhine is in Germany.")}
    result = compare(replies, "The Rhine flows through Paris.")
    assert result.findings[0].evidence is None


# Quotes match the reference even when whitespace and case differ.
@pytest.mark.unit
def test_evidence_matching_ignores_case_and_spacing():
    reply = verdict("supported", 1.0, "paris is  the CAPITAL of france.")
    evidence = parse_verdict(reply, REFERENCE)[2]
    assert evidence == "paris is  the CAPITAL of france."


# Replies wrapped in code fences or extra text are still read.
@pytest.mark.unit
def test_reply_with_fences_is_parsed():
    reply = "Sure!\n```json\n" + verdict("not_found", 0.5) + "\n```"
    assert parse_verdict(reply, REFERENCE) == ("not_found", 0.5, None)


# Confidence is clamped to the 0 to 1 range, and may be absent.
@pytest.mark.unit
def test_confidence_is_clamped_and_optional():
    assert parse_verdict(verdict("supported", 7), REFERENCE)[1] == 1.0
    assert parse_verdict('{"label": "supported"}', REFERENCE)[1] is None


# A reply that is not a valid verdict raises a strategy error naming the statement.
@pytest.mark.unit
@pytest.mark.parametrize(
    "reply",
    [
        "I cannot say",
        '{"label": "maybe"}',
        "{not json}",
        '{"label": "supported", "confidence": "high"}',
    ],
)
def test_unreadable_reply_is_a_strategy_error(reply):
    with pytest.raises(StrategyExecutionError) as exc:
        compare({"capital": reply}, "Paris is the capital of France.")
    assert "Paris is the capital" in exc.value.message


# Engine failures become strategy errors and keep the retryable flag.
@pytest.mark.unit
def test_engine_failure_is_a_retryable_strategy_error():
    failing = ScriptedAdapter(fail=AdapterTimeoutError("slow", provider="p", model="m"))
    with pytest.raises(StrategyExecutionError) as exc:
        compare({}, "Paris is the capital of France.", adapter=failing)
    assert exc.value.retryable is True and "slow" in exc.value.message


# No more than max_concurrency engine calls run at once.
@pytest.mark.unit
def test_concurrency_is_limited():
    target = " ".join(f"Capital {n} is a city." for n in range(12))
    adapter = ScriptedAdapter({"Capital": verdict("supported")})
    compare({}, target, adapter=adapter, max_concurrency=3)
    assert 1 < adapter.peak <= 3


# Too many statements are rejected before any engine call is made.
@pytest.mark.unit
def test_statement_limit():
    adapter = ScriptedAdapter({"x": verdict("supported")})
    with pytest.raises(StrategyInputError):
        compare({}, "a. b. c.", adapter=adapter, max_statements=2)
    assert adapter.prompts == []


# A long reference is cut to the limit and the result says so.
@pytest.mark.unit
def test_long_reference_is_truncated_and_flagged():
    adapter = ScriptedAdapter({"capital": verdict("supported")})
    result = compare(
        {},
        "Paris is the capital.",
        reference="x" * 50,
        adapter=adapter,
        max_reference_chars=10,
    )
    assert result.details["reference_truncated"] is True
    assert "x" * 10 in adapter.prompts[0] and "x" * 11 not in adapter.prompts[0]


# A custom splitter decides what counts as a statement.
@pytest.mark.unit
def test_custom_splitter():
    result = compare(
        {"capital": verdict("supported")},
        "Paris is the capital of France. Rome.",
        splitter=lambda text: [text],
    )
    assert len(result.details["statements"]) == 1


# The result records which engine produced the labels.
@pytest.mark.unit
def test_details_record_the_model():
    assert compare(REPLIES, TARGET).details["model"] == "scripted-model"
