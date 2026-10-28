import asyncio
import os

import pytest

from app.engines import (
    AdapterConfigError,
    GenerationRequest,
    get_adapter,
)
from app.engines.selection import ModelSelector

# Live checks against a real hosted model. They are skipped unless these are set:
#   CLOUD_LLM_TEST_MODEL     model id, e.g. nvidia/nemotron-3.5-bolt-e4b
#   CLOUD_LLM_TEST_BASE_URL  OpenAI-compatible endpoint, e.g. https://integrate.api.nvidia.com/v1
#   CLOUD_LLM_TEST_KEY_ENV   NAME of the variable holding the key (default CLOUD_LLM_API_KEY),
#                            exported in the shell or stored in the git-ignored .env file
MODEL = os.environ.get("CLOUD_LLM_TEST_MODEL")
BASE_URL = os.environ.get("CLOUD_LLM_TEST_BASE_URL")
KEY_ENV = os.environ.get("CLOUD_LLM_TEST_KEY_ENV", "CLOUD_LLM_API_KEY")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (MODEL and BASE_URL),
        reason="CLOUD_LLM_TEST_MODEL and CLOUD_LLM_TEST_BASE_URL not set",
    ),
]


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


def live_adapter(model=None, **config):
    config.setdefault("api_key_env", KEY_ENV)
    return get_adapter("cloud_llm", model or MODEL, base_url=BASE_URL, **config)


def test_live_health_check():
    assert run(live_adapter().health_check()) is True


# A real call returns text, token usage and a cost computed from the configured prices.
def test_live_generate_reports_usage_and_cost():
    adapter = live_adapter(price_per_1m_input=1.0, price_per_1m_output=2.0)
    result = run(
        adapter.generate(
            GenerationRequest(
                prompt="Reply with the single word: ok",
                system_prompt="You answer in one word.",
                max_tokens=16,
            )
        )
    )
    assert result.text
    assert result.provider == "cloud_llm" and result.model == MODEL
    assert result.latency_ms > 0
    assert result.usage["total_tokens"] > 0
    assert result.usage["cost_usd"] > 0


def test_live_unknown_model_is_a_config_error():
    adapter = live_adapter(model="no-such-model-xyz")
    with pytest.raises(AdapterConfigError) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi", max_tokens=4)))
    assert exc.value.retryable is False


# A rejected key is a config error, and neither the key nor the server text is echoed.
def test_live_bad_key_is_a_config_error_without_leaking(monkeypatch):
    bad_key = "invalid-key-for-live-test-0123456789"
    monkeypatch.setenv("LIVE_TEST_BAD_KEY", bad_key)
    adapter = live_adapter(api_key_env="LIVE_TEST_BAD_KEY")
    with pytest.raises(AdapterConfigError) as exc:
        run(adapter.generate(GenerationRequest(prompt="hi", max_tokens=4)))
    assert bad_key not in str(exc.value) and bad_key not in repr(exc.value.to_dict())


# The selector picks the cheaper model and answers through the real endpoint.
def test_live_selector_uses_the_cheapest_model():
    catalog = {
        "models": [
            {
                "id": "live-cheap",
                "provider": "cloud_llm",
                "model": MODEL,
                "price_per_1m_input": 0.1,
                "price_per_1m_output": 0.2,
                "base_url": BASE_URL,
                "api_key_env": KEY_ENV,
            },
            {
                "id": "live-pricey",
                "provider": "cloud_llm",
                "model": "no-such-model-xyz",
                "tier": 2,
                "price_per_1m_input": 5,
                "price_per_1m_output": 5,
                "base_url": BASE_URL,
                "api_key_env": KEY_ENV,
            },
        ]
    }
    result = run(
        ModelSelector.from_dict(catalog).generate(
            GenerationRequest(prompt="Reply with the single word: ok", max_tokens=16)
        )
    )
    assert result.model == MODEL and result.text
    assert result.usage["cost_usd"] > 0
