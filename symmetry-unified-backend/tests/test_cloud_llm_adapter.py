import asyncio
import json

import httpx
import pytest

from app.engines import (
    AdapterConfigError,
    AdapterError,
    AdapterRequestError,
    AdapterResponseError,
    AdapterTimeoutError,
    GenerationRequest,
    get_adapter,
    list_adapters,
)

KEY = "sk-test-SECRET-1234567890"
KEY_ENV = "TEST_CLOUD_KEY"
BASE = "https://llm.test/v1"


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv(KEY_ENV, KEY)


# Builds a cloud_llm adapter whose HTTP calls go to the given handler instead of the network.
def adapter_with(handler, **config):
    config.setdefault("base_url", BASE)
    config.setdefault("api_key_env", KEY_ENV)
    return get_adapter(
        "cloud_llm", "cheap-model", transport=httpx.MockTransport(handler), **config
    )


# A minimal OpenAI-style chat completion body.
def completion(content="ok", usage=None):
    body = {"choices": [{"message": {"role": "assistant", "content": content}}]}
    if usage is not None:
        body["usage"] = usage
    return body


def ok(request):
    return httpx.Response(200, json=completion())


# Generates once and returns the adapter error it raises.
def error_of(adapter):
    with pytest.raises(AdapterError) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi")))
    return exc.value


@pytest.mark.unit
def test_registered_under_cloud_llm():
    assert "cloud_llm" in list_adapters()


# The key goes out as a bearer token and the request is a normal chat completion.
@pytest.mark.unit
def test_generate_sends_bearer_key_and_chat_request():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=completion("  Paris "))

    result = run(
        adapter_with(handler).generate(
            GenerationRequest(
                prompt="Capital?", system_prompt="Be brief.", max_tokens=9
            )
        )
    )

    assert seen["url"] == f"{BASE}/chat/completions"
    assert seen["auth"] == f"Bearer {KEY}"
    assert seen["body"]["model"] == "cheap-model"
    assert seen["body"]["max_tokens"] == 9 and seen["body"]["stream"] is False
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]
    assert result.text == "Paris"
    assert result.provider == "cloud_llm" and result.model == "cheap-model"


# --- config and key handling ------------------------------------------------


@pytest.mark.unit
def test_base_url_is_required():
    with pytest.raises(AdapterConfigError, match="base_url is required"):
        get_adapter("cloud_llm", "m", api_key_env=KEY_ENV)


@pytest.mark.unit
def test_missing_env_var_names_the_variable_not_a_value():
    with pytest.raises(AdapterConfigError) as exc:
        get_adapter("cloud_llm", "m", base_url=BASE, api_key_env="NO_SUCH_KEY_VAR")
    err = exc.value
    assert "NO_SUCH_KEY_VAR" in err.message and err.retryable is False


@pytest.mark.unit
def test_blank_env_var_counts_as_missing(monkeypatch):
    monkeypatch.setenv(KEY_ENV, "   ")
    with pytest.raises(AdapterConfigError):
        get_adapter("cloud_llm", "m", base_url=BASE, api_key_env=KEY_ENV)


@pytest.mark.unit
def test_default_env_var_name(monkeypatch):
    monkeypatch.setenv("CLOUD_LLM_API_KEY", "from-default")
    adapter = get_adapter("cloud_llm", "m", base_url=BASE)
    assert adapter.api_key_env == "CLOUD_LLM_API_KEY"


# A raw key passed as config is refused and must not be echoed back.
@pytest.mark.unit
def test_raw_api_key_is_refused_and_not_echoed():
    with pytest.raises(AdapterConfigError) as exc:
        get_adapter("cloud_llm", "m", base_url=BASE, api_key="sk-live-ABCDEF")
    assert "sk-live-ABCDEF" not in str(exc.value)


# Pasting a key into api_key_env by mistake is caught and the value is not echoed.
@pytest.mark.unit
def test_key_pasted_as_env_name_is_refused_and_not_echoed():
    with pytest.raises(AdapterConfigError) as exc:
        get_adapter("cloud_llm", "m", base_url=BASE, api_key_env="sk-live-ABCDEF")
    assert "sk-live-ABCDEF" not in str(exc.value)


@pytest.mark.unit
def test_key_is_not_stored_in_config_or_repr():
    adapter = adapter_with(ok)
    assert KEY not in repr(adapter.config) and KEY not in repr(
        adapter.__dict__.get("config")
    )
    assert adapter.config["api_key_env"] == KEY_ENV


# --- the key never leaks through errors -------------------------------------


# Providers sometimes echo the key in a 401 body; it must not reach the error.
@pytest.mark.unit
@pytest.mark.parametrize("status", [401, 403])
def test_auth_errors_never_include_server_text(status):
    body = {"error": {"message": f"Incorrect API key provided: {KEY}"}}
    err = error_of(adapter_with(lambda r: httpx.Response(status, json=body)))
    assert isinstance(err, AdapterConfigError) and err.retryable is False
    assert KEY not in str(err) and KEY not in repr(err.to_dict())
    assert "API key" in err.message


# The key is scrubbed from any other server text too.
@pytest.mark.unit
def test_key_is_scrubbed_from_other_error_text():
    body = {"error": {"message": f"bad request for {KEY}"}}
    err = error_of(adapter_with(lambda r: httpx.Response(400, json=body)))
    assert isinstance(err, AdapterRequestError)
    assert KEY not in str(err) and "[redacted]" in err.message


@pytest.mark.unit
def test_key_not_in_error_when_server_unreachable():
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    err = error_of(adapter_with(refuse))
    assert isinstance(err, AdapterRequestError) and KEY not in str(err)
    assert "cloud LLM endpoint" in err.message


# --- error mapping ----------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "status,error_cls,retryable",
    [
        (404, AdapterConfigError, False),
        (429, AdapterResponseError, True),
        (400, AdapterRequestError, False),
        (402, AdapterRequestError, False),
        (500, AdapterResponseError, True),
        (503, AdapterResponseError, True),
    ],
)
def test_http_status_maps_to_adapter_error(status, error_cls, retryable):
    err = error_of(adapter_with(lambda r: httpx.Response(status, json={"error": "x"})))
    assert isinstance(err, error_cls) and err.retryable is retryable
    assert err.provider == "cloud_llm" and err.model == "cheap-model"


@pytest.mark.unit
def test_timeout_is_retryable():
    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    err = error_of(adapter_with(slow))
    assert isinstance(err, AdapterTimeoutError) and err.retryable is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>gateway</html>"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json=completion("  ")),
    ],
)
def test_unusable_reply_raises_response_error(response):
    assert isinstance(error_of(adapter_with(lambda r: response)), AdapterResponseError)


@pytest.mark.unit
def test_health_check_uses_the_key_and_never_raises():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"data": []})

    assert run(adapter_with(handler).health_check()) is True
    assert seen["auth"] == f"Bearer {KEY}"
    assert run(adapter_with(lambda r: httpx.Response(401)).health_check()) is False


# --- provider quirks --------------------------------------------------------


# Some models require max_completion_tokens and reject a temperature value.
@pytest.mark.unit
def test_max_completion_tokens_and_omitted_temperature():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=completion())

    adapter = adapter_with(
        handler, max_tokens_param="max_completion_tokens", omit_temperature=True
    )
    run(adapter.generate(GenerationRequest(prompt="hi", max_tokens=33)))
    assert seen["body"]["max_completion_tokens"] == 33
    assert "max_tokens" not in seen["body"] and "temperature" not in seen["body"]


@pytest.mark.unit
def test_invalid_max_tokens_param_is_refused():
    with pytest.raises(AdapterConfigError):
        adapter_with(ok, max_tokens_param="max_new_tokens")


# --- cost reporting ---------------------------------------------------------


@pytest.mark.unit
def test_cost_is_computed_from_prices_and_token_usage():
    usage = {"prompt_tokens": 2000, "completion_tokens": 500, "total_tokens": 2500}
    adapter = adapter_with(
        lambda r: httpx.Response(200, json=completion(usage=usage)),
        price_per_1m_input=0.30,
        price_per_1m_output=1.20,
    )
    result = run(adapter.generate(GenerationRequest(prompt="hi")))
    assert result.usage["cost_usd"] == pytest.approx(0.0012)
    assert result.usage["total_tokens"] == 2500


@pytest.mark.unit
def test_no_cost_without_prices_or_token_counts():
    usage = {"prompt_tokens": 10, "completion_tokens": 5}
    priced = adapter_with(
        lambda r: httpx.Response(200, json=completion()),
        price_per_1m_input=1.0,
        price_per_1m_output=1.0,
    )
    unpriced = adapter_with(lambda r: httpx.Response(200, json=completion(usage=usage)))
    assert "cost_usd" not in run(priced.generate(GenerationRequest(prompt="hi"))).usage
    assert (
        "cost_usd" not in run(unpriced.generate(GenerationRequest(prompt="hi"))).usage
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "prices",
    [
        {"price_per_1m_input": 1.0},
        {"price_per_1m_output": 1.0},
        {"price_per_1m_input": -1, "price_per_1m_output": 1},
        {"price_per_1m_input": "cheap", "price_per_1m_output": 1},
        {"price_per_1m_input": True, "price_per_1m_output": 1},
    ],
)
def test_invalid_prices_are_refused(prices):
    with pytest.raises(AdapterConfigError):
        adapter_with(ok, **prices)


# --- keys stored in the git-ignored .env file --------------------------------


# A key in .env is found when the variable is not exported in the shell.
@pytest.mark.unit
def test_key_is_read_from_dotenv_file(tmp_path, monkeypatch):
    monkeypatch.delenv("DOTENV_ONLY_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "DOTENV_ONLY_KEY=from-dotenv-file\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json=completion())

    run(
        adapter_with(handler, api_key_env="DOTENV_ONLY_KEY").generate(
            GenerationRequest(prompt="hi")
        )
    )
    assert seen["auth"] == "Bearer from-dotenv-file"


# The shell environment wins over .env, as in app/core/settings.py.
@pytest.mark.unit
def test_exported_variable_wins_over_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(f"{KEY_ENV}=from-dotenv-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json=completion())

    run(adapter_with(handler).generate(GenerationRequest(prompt="hi")))
    assert seen["auth"] == f"Bearer {KEY}"


@pytest.mark.unit
def test_key_missing_from_env_and_dotenv_is_a_config_error(tmp_path, monkeypatch):
    monkeypatch.delenv("ABSENT_KEY", raising=False)
    (tmp_path / ".env").write_text("OTHER=1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(AdapterConfigError, match="ABSENT_KEY is not set"):
        get_adapter("cloud_llm", "m", base_url=BASE, api_key_env="ABSENT_KEY")
