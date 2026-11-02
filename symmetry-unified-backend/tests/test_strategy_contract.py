import asyncio

import pytest

from app.strategies import (
    ComparisonStrategy,
    Finding,
    StrategyConfigError,
    StrategyError,
    StrategyInput,
    StrategyResult,
    UnknownStrategyError,
    get_strategy,
    list_strategies,
    register_strategy,
    registry,
)

# New strategies get added here so they run the same contract tests.
STRATEGY_CASES = [("fake", {})]


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


# Every strategy returns a StrategyResult named after itself with a valid score.
@pytest.mark.unit
@pytest.mark.parametrize("name,config", STRATEGY_CASES)
def test_strategy_returns_strategy_result(name, config):
    strategy = get_strategy(name, **config)
    assert isinstance(strategy, ComparisonStrategy)
    result = run(strategy.compare(StrategyInput("a b c", "b c d")))
    assert isinstance(result, StrategyResult)
    assert result.strategy == name
    assert result.score is None or 0.0 <= result.score <= 1.0
    assert all(isinstance(f, Finding) for f in result.findings)


# Every strategy gives the same answer when it is run twice on the same input.
@pytest.mark.unit
@pytest.mark.parametrize("name,config", STRATEGY_CASES)
def test_strategy_is_stateless(name, config):
    strategy = get_strategy(name, **config)
    request = StrategyInput("a b c", "b c d")
    assert run(strategy.compare(request)) == run(strategy.compare(request))


# A failing strategy raises StrategyError carrying its name.
@pytest.mark.unit
def test_failure_raises_strategy_error_with_context():
    strategy = get_strategy("fake", fail=True)
    with pytest.raises(StrategyError) as exc:
        run(strategy.compare(StrategyInput("a", "b")))
    assert exc.value.strategy == "fake"


# Errors convert to a dict the pipeline can report per strategy.
@pytest.mark.unit
def test_error_to_dict_for_per_strategy_reporting():
    strategy = get_strategy("fake", fail=True)
    with pytest.raises(StrategyError) as exc:
        run(strategy.compare(StrategyInput("a", "b")))
    d = exc.value.to_dict()
    assert d["strategy"] == "fake" and d["message"]
    assert d["error"] == "StrategyExecutionError" and d["retryable"] is False


# One failing strategy does not stop the others from answering.
@pytest.mark.unit
def test_one_failing_strategy_does_not_fail_the_others():
    async def fan_out():
        strategies = [get_strategy("fake"), get_strategy("fake", fail=True)]
        request = StrategyInput("a b", "a c")
        return await asyncio.gather(
            *(s.compare(request) for s in strategies), return_exceptions=True
        )

    ok, bad = run(fan_out())
    assert ok.score == pytest.approx(1 / 3)
    assert isinstance(bad, StrategyError)


# Asking for an unregistered name raises UnknownStrategyError listing valid names.
@pytest.mark.unit
def test_unknown_strategy_lists_available_names():
    with pytest.raises(UnknownStrategyError) as exc:
        get_strategy("nope")
    assert "fake" in exc.value.message


# Empty texts, bad scores and bad confidences are rejected.
@pytest.mark.unit
def test_input_and_result_validation():
    with pytest.raises(ValueError):
        StrategyInput("  ", "ok")
    with pytest.raises(ValueError):
        StrategyInput("ok", "")
    with pytest.raises(ValueError):
        StrategyResult(strategy="x", score=1.5)
    with pytest.raises(ValueError):
        Finding(label="x", confidence=-0.1)
    with pytest.raises(ValueError):
        Finding(label="")


# The registry refuses non-strategies and duplicate names.
@pytest.mark.unit
def test_register_rejects_non_strategy_and_duplicates():
    with pytest.raises(TypeError):
        register_strategy("bad")(object)

    class Other(ComparisonStrategy):
        async def compare(self, request): ...

    with pytest.raises(ValueError):
        register_strategy("fake")(Other)


# A new strategy is added by registering it, with no change to the registry code.
@pytest.mark.unit
def test_new_strategy_is_added_by_registering_only(monkeypatch):
    monkeypatch.setattr(registry, "_STRATEGIES", dict(registry._STRATEGIES))

    @register_strategy("always_one")
    class AlwaysOne(ComparisonStrategy):
        async def compare(self, request):
            return StrategyResult(strategy=self.name, score=1.0)

    assert "always_one" in list_strategies()
    result = run(get_strategy("always_one").compare(StrategyInput("a", "b")))
    assert result.score == 1.0 and result.strategy == "always_one"


# A strategy that needs an engine refuses to build without it.
@pytest.mark.unit
def test_required_settings_are_checked(monkeypatch):
    monkeypatch.setattr(registry, "_STRATEGIES", dict(registry._STRATEGIES))

    @register_strategy("needs_model")
    class NeedsModel(ComparisonStrategy):
        requires = ("model_adapter",)

        async def compare(self, request): ...

    with pytest.raises(StrategyConfigError):
        get_strategy("needs_model")
    assert get_strategy("needs_model", model_adapter=object()).config


# The fake strategy shows up in the registry listing, sorted.
@pytest.mark.unit
def test_list_strategies_contains_fake_and_is_sorted():
    names = list_strategies()
    assert "fake" in names and names == sorted(names)


# Pipeline-style code can run any strategy through the interface alone.
@pytest.mark.unit
def test_pipeline_style_usage_only_through_interface():
    async def pipeline(strategy: ComparisonStrategy, a: str, b: str):
        return (await strategy.compare(StrategyInput(a, b))).score

    assert run(pipeline(get_strategy("fake"), "x y", "x y")) == 1.0
