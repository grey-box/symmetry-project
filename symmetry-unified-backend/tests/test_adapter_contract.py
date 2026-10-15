import asyncio

import pytest

from app.engines import (
    AdapterError,
    GenerationRequest,
    GenerationResult,
    ModelAdapter,
    UnknownAdapterError,
    get_adapter,
    list_adapters,
    register_adapter,
)

# New adapters get added here so they run the same contract tests.
ADAPTER_CASES = [("fake", "fake-model", {})]


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


# Every adapter returns a GenerationResult with provider and model filled in.
@pytest.mark.unit
@pytest.mark.parametrize("provider,model,config", ADAPTER_CASES)
def test_adapter_returns_generation_result(provider, model, config):
    adapter = get_adapter(provider, model, **config)
    assert isinstance(adapter, ModelAdapter)
    result = run(adapter.generate(GenerationRequest(prompt="hello")))
    assert isinstance(result, GenerationResult)
    assert isinstance(result.text, str) and result.text
    assert result.provider == provider
    assert result.model == model


# Every adapter reports health as a bool.
@pytest.mark.unit
@pytest.mark.parametrize("provider,model,config", ADAPTER_CASES)
def test_adapter_health_check_is_bool(provider, model, config):
    assert isinstance(run(get_adapter(provider, model, **config).health_check()), bool)


# Failures raise AdapterError carrying provider, model and retryable.
@pytest.mark.unit
def test_failure_raises_adapter_error_with_context():
    adapter = get_adapter("fake", "m", fail="timeout")
    with pytest.raises(AdapterError) as exc:
        run(adapter.generate(GenerationRequest(prompt="x")))
    assert exc.value.provider == "fake" and exc.value.model == "m"
    assert exc.value.retryable is True


# Errors convert to a dict the pipeline can report per engine.
@pytest.mark.unit
def test_error_to_dict_for_per_engine_reporting():
    err = get_adapter("fake", "m", fail="timeout")
    with pytest.raises(AdapterError) as exc:
        run(err.generate(GenerationRequest(prompt="x")))
    d = exc.value.to_dict()
    assert d["provider"] == "fake" and d["model"] == "m"
    assert d["retryable"] is True and d["message"]


# One failing engine does not stop the others from answering.
@pytest.mark.unit
def test_one_failing_engine_does_not_fail_the_others():
    async def fan_out():
        adapters = [
            get_adapter("fake", "a", reply="A"),
            get_adapter("fake", "b", fail="timeout"),
        ]
        return await asyncio.gather(
            *(x.generate(GenerationRequest(prompt="q")) for x in adapters),
            return_exceptions=True,
        )

    ok, bad = run(fan_out())
    assert ok.text == "A"
    assert isinstance(bad, AdapterError)


# Asking for an unregistered provider raises UnknownAdapterError.
@pytest.mark.unit
def test_unknown_provider():
    with pytest.raises(UnknownAdapterError):
        get_adapter("nope", "m")


# Empty prompts and non-positive max_tokens are rejected.
@pytest.mark.unit
def test_request_validation():
    with pytest.raises(ValueError):
        GenerationRequest(prompt="  ")
    with pytest.raises(ValueError):
        GenerationRequest(prompt="ok", max_tokens=0)


# The registry refuses non-adapters and duplicate names.
@pytest.mark.unit
def test_register_rejects_non_adapter_and_duplicates():
    with pytest.raises(TypeError):
        register_adapter("bad")(object)

    class Other(ModelAdapter):
        async def generate(self, request): ...

    with pytest.raises(ValueError):
        register_adapter("fake")(Other)


# The fake adapter shows up in the registry listing.
@pytest.mark.unit
def test_list_adapters_contains_fake():
    assert "fake" in list_adapters()


# Pipeline-style code can use any engine through the interface alone.
@pytest.mark.unit
def test_pipeline_style_usage_only_through_interface():

    async def pipeline(adapter: ModelAdapter, text: str) -> str:
        return (await adapter.generate(GenerationRequest(prompt=text))).text

    assert run(pipeline(get_adapter("fake", "m", reply="ok"), "q")) == "ok"
