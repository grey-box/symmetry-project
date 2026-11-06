import asyncio
import json
import os
import subprocess
import sys

import httpx
import pytest

from app.core.settings import LOCAL_SLM_BASE_URL
from app.engines import (
    AdapterConfigError,
    AdapterRequestError,
    AdapterResponseError,
    AdapterTimeoutError,
    GenerationRequest,
    get_adapter,
    list_adapters,
)


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


# Builds a local_slm adapter whose HTTP calls go to the given handler instead of a server.
def adapter_with(handler, **config):
    return get_adapter(
        "local_slm", "qwen2.5:1.5b", transport=httpx.MockTransport(handler), **config
    )


# A minimal OpenAI-style chat completion body.
def completion(content, usage=None):
    body = {"choices": [{"message": {"role": "assistant", "content": content}}]}
    if usage is not None:
        body["usage"] = usage
    return body


# Raises the given httpx error for every request.
def failing(exc_cls):
    def handler(request):
        raise exc_cls("boom", request=request)

    return handler


@pytest.mark.unit
def test_registered_under_local_slm():
    assert "local_slm" in list_adapters()


@pytest.mark.unit
def test_default_base_url_comes_from_settings():
    assert get_adapter("local_slm", "m").base_url == LOCAL_SLM_BASE_URL.rstrip("/")


# Sends an OpenAI-style chat request and returns text, usage and latency.
@pytest.mark.unit
def test_generate_sends_chat_request_and_returns_result():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        usage = {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}
        return httpx.Response(200, json=completion("  Paris  ", usage))

    adapter = adapter_with(handler, base_url="http://slm.test/v1/")
    result = run(
        adapter.generate(
            GenerationRequest(
                prompt="Capital of France?",
                system_prompt="Answer briefly.",
                max_tokens=16,
                temperature=0.2,
            )
        )
    )

    assert seen["url"] == "http://slm.test/v1/chat/completions"
    assert seen["body"] == {
        "model": "qwen2.5:1.5b",
        "messages": [
            {"role": "system", "content": "Answer briefly."},
            {"role": "user", "content": "Capital of France?"},
        ],
        "max_tokens": 16,
        "temperature": 0.2,
        "stream": False,
    }
    assert result.text == "Paris"
    assert result.provider == "local_slm" and result.model == "qwen2.5:1.5b"
    assert result.usage["total_tokens"] == 7
    assert result.latency_ms >= 0


@pytest.mark.unit
def test_no_system_message_when_system_prompt_missing():
    seen = {}

    def handler(request):
        seen["messages"] = json.loads(request.content)["messages"]
        return httpx.Response(200, json=completion("ok"))

    run(adapter_with(handler).generate(GenerationRequest(prompt="hi")))
    assert seen["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.unit
def test_missing_usage_gives_empty_dict():
    adapter = adapter_with(lambda r: httpx.Response(200, json=completion("ok")))
    assert run(adapter.generate(GenerationRequest(prompt="hi"))).usage == {}


@pytest.mark.unit
def test_timeout_raises_retryable_timeout_error():
    adapter = adapter_with(failing(httpx.ReadTimeout))
    with pytest.raises(AdapterTimeoutError) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi", timeout_s=1.0)))
    assert exc.value.retryable is True
    assert exc.value.provider == "local_slm" and exc.value.model == "qwen2.5:1.5b"


@pytest.mark.unit
def test_unreachable_server_raises_request_error_naming_the_url():
    adapter = adapter_with(failing(httpx.ConnectError), base_url="http://slm.test/v1")
    with pytest.raises(AdapterRequestError) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi")))
    assert "http://slm.test/v1" in exc.value.message


# HTTP status codes map onto the adapter error types and their retryable flag.
@pytest.mark.unit
@pytest.mark.parametrize(
    "status,error_cls,retryable",
    [
        (401, AdapterConfigError, False),
        (403, AdapterConfigError, False),
        (404, AdapterConfigError, False),
        (429, AdapterResponseError, True),
        (400, AdapterRequestError, False),
        (402, AdapterRequestError, False),
        (500, AdapterResponseError, True),
        (503, AdapterResponseError, True),
    ],
)
def test_http_status_maps_to_adapter_error(status, error_cls, retryable):
    adapter = adapter_with(lambda r: httpx.Response(status, json={"error": "x"}))
    with pytest.raises(error_cls) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi")))
    assert exc.value.retryable is retryable


# Bodies that are not a usable chat completion raise AdapterResponseError.
@pytest.mark.unit
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"unexpected": True}),
        httpx.Response(200, json=completion("   ")),
        httpx.Response(200, json=completion(None)),
    ],
)
def test_unusable_reply_raises_response_error(response):
    adapter = adapter_with(lambda r: response)
    with pytest.raises(AdapterResponseError):
        run(adapter.generate(GenerationRequest(prompt="hi")))


@pytest.mark.unit
def test_health_check_true_when_models_endpoint_answers():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        return httpx.Response(200, json={"data": []})

    assert run(adapter_with(handler, base_url="http://slm.test/v1").health_check())
    assert seen["path"] == "/v1/models"


@pytest.mark.unit
@pytest.mark.parametrize(
    "handler",
    [lambda r: httpx.Response(500), failing(httpx.ConnectError)],
)
def test_health_check_false_on_error_or_unreachable(handler):
    assert run(adapter_with(handler).health_check()) is False


# Calls a real local server; set LOCAL_SLM_TEST_MODEL (e.g. qwen2.5:1.5b) to run it.
@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("LOCAL_SLM_TEST_MODEL"), reason="LOCAL_SLM_TEST_MODEL not set"
)
def test_live_local_server():
    adapter = get_adapter("local_slm", os.environ["LOCAL_SLM_TEST_MODEL"])
    assert run(adapter.health_check()) is True
    result = run(
        adapter.generate(
            GenerationRequest(prompt="Reply with the word: ok", max_tokens=8)
        )
    )
    assert result.text


# A refused connection (nothing listens on port 1) is reported, not left as a raw httpx error.
@pytest.mark.unit
def test_connection_refused_raises_request_error():
    adapter = get_adapter("local_slm", "m", base_url="http://127.0.0.1:1/v1")
    with pytest.raises(AdapterRequestError):
        run(adapter.generate(GenerationRequest(prompt="hi")))
    assert run(adapter.health_check()) is False


# Concurrent calls on one adapter stay independent, as in the LLM-vs-LLM fan-out.
@pytest.mark.unit
def test_concurrent_generate_calls_are_independent():
    def handler(request):
        prompt = json.loads(request.content)["messages"][-1]["content"]
        if prompt == "bad":
            return httpx.Response(500)
        return httpx.Response(200, json=completion(f"re: {prompt}"))

    async def fan_out():
        adapter = adapter_with(handler)
        return await asyncio.gather(
            *(adapter.generate(GenerationRequest(prompt=p)) for p in ["a", "bad", "c"]),
            return_exceptions=True,
        )

    first, failed, third = run(fan_out())
    assert first.text == "re: a" and third.text == "re: c"
    assert isinstance(failed, AdapterResponseError)


# Content sent as a list of parts is not a plain string reply and is rejected cleanly.
@pytest.mark.unit
def test_non_string_content_raises_response_error():
    adapter = adapter_with(
        lambda r: httpx.Response(200, json=completion([{"type": "text", "text": "x"}]))
    )
    with pytest.raises(AdapterResponseError):
        run(adapter.generate(GenerationRequest(prompt="hi")))


# A non-dict usage field is ignored rather than breaking the result.
@pytest.mark.unit
def test_non_dict_usage_is_ignored():
    adapter = adapter_with(
        lambda r: httpx.Response(200, json={**completion("ok"), "usage": "n/a"})
    )
    assert run(adapter.generate(GenerationRequest(prompt="hi"))).usage == {}


live = pytest.mark.skipif(
    not os.environ.get("LOCAL_SLM_TEST_MODEL"), reason="LOCAL_SLM_TEST_MODEL not set"
)


# Ollama answers 404 for an unknown model, which maps to a config error.
@pytest.mark.integration
@live
def test_live_unknown_model_raises_config_error():
    adapter = get_adapter("local_slm", "no-such-model:0b")
    with pytest.raises(AdapterConfigError):
        run(adapter.generate(GenerationRequest(prompt="hi", max_tokens=4)))


# A real server that cannot answer in time raises AdapterTimeoutError.
@pytest.mark.integration
@live
def test_live_timeout():
    adapter = get_adapter("local_slm", os.environ["LOCAL_SLM_TEST_MODEL"])
    with pytest.raises(AdapterTimeoutError):
        run(
            adapter.generate(
                GenerationRequest(prompt="Write a long story.", timeout_s=0.01)
            )
        )


# max_tokens, system prompt and usage are honoured by a real model.
@pytest.mark.integration
@live
def test_live_max_tokens_system_prompt_and_usage():
    adapter = get_adapter("local_slm", os.environ["LOCAL_SLM_TEST_MODEL"])
    result = run(
        adapter.generate(
            GenerationRequest(
                prompt="Count from 1 to 100.",
                system_prompt="You are a counting assistant.",
                max_tokens=5,
            )
        )
    )
    assert result.text
    assert 0 < result.usage.get("completion_tokens", 0) <= 6
    assert result.latency_ms > 0


# Several real calls at once all return text.
@pytest.mark.integration
@live
def test_live_concurrent_calls():
    adapter = get_adapter("local_slm", os.environ["LOCAL_SLM_TEST_MODEL"])

    async def fan_out():
        return await asyncio.gather(
            *(
                adapter.generate(GenerationRequest(prompt=f"Say {n}", max_tokens=8))
                for n in ("one", "two", "three")
            )
        )

    assert all(r.text for r in run(fan_out()))


# The server's own error text reaches the caller, capped in length.
@pytest.mark.unit
def test_server_error_message_is_included():
    body = {"error": {"message": "Add usage credits to use cloud models"}}
    adapter = adapter_with(lambda r: httpx.Response(402, json=body))
    with pytest.raises(AdapterRequestError) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi")))
    assert "HTTP 402" in exc.value.message
    assert "Add usage credits" in exc.value.message

    long_body = {"error": {"message": "x" * 1000}}
    adapter = adapter_with(lambda r: httpx.Response(400, json=long_body))
    with pytest.raises(AdapterRequestError) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi")))
    assert len(exc.value.message) < 300


# Bad config is caught when the adapter is built, as a config error, not on the first call.
@pytest.mark.unit
@pytest.mark.parametrize(
    "base_url",
    ["localhost:11434/v1", "not a url", "ftp://localhost/v1", "http://", 42],
)
def test_invalid_base_url_raises_config_error(base_url):
    with pytest.raises(AdapterConfigError) as exc:
        get_adapter("local_slm", "m", base_url=base_url)
    assert exc.value.provider == "local_slm" and exc.value.retryable is False


@pytest.mark.unit
@pytest.mark.parametrize("model", ["", "   ", None])
def test_empty_model_name_raises_config_error(model):
    with pytest.raises(AdapterConfigError):
        get_adapter("local_slm", model)


# None or blank base_url falls back to the default instead of crashing; stray spaces are trimmed.
@pytest.mark.unit
@pytest.mark.parametrize("base_url", [None, "", "   "])
def test_blank_base_url_uses_default(base_url):
    assert get_adapter("local_slm", "m", base_url=base_url).base_url == (
        LOCAL_SLM_BASE_URL.rstrip("/")
    )


@pytest.mark.unit
def test_base_url_is_trimmed():
    assert (
        get_adapter("local_slm", "m", base_url="  http://slm.test/v1/ ").base_url
        == "http://slm.test/v1"
    )


# The 404 message points at the base_url too, since a missing /v1 also gives a 404.
@pytest.mark.unit
def test_404_message_mentions_base_url_and_model():
    adapter = adapter_with(lambda r: httpx.Response(404, json={"error": "nope"}))
    with pytest.raises(AdapterConfigError) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi")))
    assert "/v1" in exc.value.message and "model" in exc.value.message


# The setting reads the environment, and an empty value falls back to the default.
@pytest.mark.unit
@pytest.mark.parametrize(
    "value,expected",
    [("http://example.test:1/v1", "http://example.test:1/v1"), ("", None)],
)
def test_base_url_setting_reads_environment(value, expected):
    code = "from app.core.settings import LOCAL_SLM_BASE_URL as u; print(u)"
    out = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "LOCAL_SLM_BASE_URL": value},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert out == (expected or "http://localhost:11434/v1")
