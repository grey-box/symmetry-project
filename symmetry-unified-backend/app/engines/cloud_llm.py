import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from starlette.config import Config

from .base import GenerationRequest, GenerationResult, ModelAdapter
from .errors import (
    AdapterConfigError,
    AdapterRequestError,
    AdapterResponseError,
    AdapterTimeoutError,
)
from .registry import register_adapter

DEFAULT_API_KEY_ENV = "CLOUD_LLM_API_KEY"
MAX_TOKENS_PARAMS = ("max_tokens", "max_completion_tokens")


# Returns the value of a variable from the process environment, else from the .env file
# (the same lookup order as app/core/settings.py), or "" when it is set in neither.
def _read_secret(name: str) -> str:
    env_file = Path(".env")
    config = Config(env_file if env_file.is_file() else None)
    return str(config(name, default="")).strip()


# Hosted LLM behind any OpenAI-compatible endpoint (OpenAI, Mistral, Qwen, OpenRouter, ...).
# Config:
#   base_url          required; the provider endpoint, e.g. https://api.openai.com/v1
#   api_key_env       NAME of the variable holding the key (default CLOUD_LLM_API_KEY), read from the
#                     process environment, else from the git-ignored .env file; the key itself is
#                     never accepted as config and never appears in errors
#   price_per_1m_input / price_per_1m_output
#                     optional USD prices (give both); adds usage["cost_usd"] to each result
#   max_tokens_param  "max_tokens" (default) or "max_completion_tokens" for models that require it
#   omit_temperature  True for models that reject a temperature value
#   transport         an httpx transport, for tests
# Bad config (missing key, bad base_url or prices, empty model name) raises AdapterConfigError here.
@register_adapter("cloud_llm")
class CloudLLMAdapter(ModelAdapter):
    def __init__(self, model_name: str, **config):
        super().__init__(model_name, **config)
        if not isinstance(model_name, str) or not model_name.strip():
            raise self._error(AdapterConfigError, "model name must not be empty")
        base_url = str(config.get("base_url") or "").strip()
        if not base_url:
            raise self._error(AdapterConfigError, "base_url is required")
        parts = urlparse(base_url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise self._error(
                AdapterConfigError,
                f"base_url must be an http(s) URL such as https://api.openai.com/v1, got {base_url!r}",
            )
        self.base_url = base_url.rstrip("/")
        self._transport = config.get("transport")

        if "api_key" in config:
            raise self._error(
                AdapterConfigError,
                "api_key is not accepted; set api_key_env to the name of an environment variable",
            )
        env_name = config.get("api_key_env") or DEFAULT_API_KEY_ENV
        if not isinstance(env_name, str) or not env_name.isidentifier():
            raise self._error(
                AdapterConfigError,
                "api_key_env must be the name of an environment variable, not the key",
            )
        self.api_key_env = env_name
        self._api_key = _read_secret(env_name)
        if not self._api_key:
            raise self._error(
                AdapterConfigError,
                f"{env_name} is not set; export it or add it to the git-ignored .env file",
            )

        self._prices = self._read_prices(config)
        self._max_tokens_param = config.get("max_tokens_param", "max_tokens")
        if self._max_tokens_param not in MAX_TOKENS_PARAMS:
            raise self._error(
                AdapterConfigError,
                f"max_tokens_param must be one of {MAX_TOKENS_PARAMS}",
            )
        self._omit_temperature = bool(config.get("omit_temperature", False))

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        start = time.perf_counter()
        try:
            async with self._client(request.timeout_s) as client:
                response = await client.post(
                    "/chat/completions", json=self._build_payload(request)
                )
        except httpx.TimeoutException:
            raise self._error(
                AdapterTimeoutError, f"no reply within {request.timeout_s}s"
            ) from None
        except httpx.RequestError as e:
            raise self._error(
                AdapterRequestError,
                f"could not reach cloud LLM endpoint at {self.base_url}: {type(e).__name__}",
            ) from None
        latency_ms = (time.perf_counter() - start) * 1000

        self._raise_for_status(response)
        text, usage = self._parse(response)
        return GenerationResult(
            text=text,
            model=self.model_name,
            provider=self.provider,
            latency_ms=latency_ms,
            usage=self._with_cost(usage),
        )

    # Returns True when the endpoint answers its model listing with the key; never raises.
    async def health_check(self) -> bool:
        try:
            async with self._client(5.0) as client:
                response = await client.get("/models")
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    # Returns (input, output) USD prices per 1M tokens, or None when no pricing is configured.
    def _read_prices(self, config) -> tuple[float, float] | None:
        raw = (config.get("price_per_1m_input"), config.get("price_per_1m_output"))
        if raw == (None, None):
            return None
        if any(
            isinstance(p, bool) or not isinstance(p, int | float) or p < 0 for p in raw
        ):
            raise self._error(
                AdapterConfigError,
                "price_per_1m_input and price_per_1m_output must both be numbers >= 0",
            )
        return float(raw[0]), float(raw[1])

    # Builds the chat completions request body, adjusted for models with different parameter rules.
    def _build_payload(self, request: GenerationRequest) -> dict:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": False,
        }
        if self._max_tokens_param != "max_tokens":
            payload[self._max_tokens_param] = payload.pop("max_tokens")
        if self._omit_temperature:
            payload.pop("temperature")
        return payload

    def _client(self, timeout_s: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout_s,
            transport=self._transport,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )

    def _error(self, cls, message):
        return cls(message, provider=self.provider, model=self.model_name)

    # Returns the server's own error text (capped, with the key removed) so messages
    # like "add usage credits" reach the caller.
    def _server_message(self, response: httpx.Response) -> str:
        try:
            error = response.json()["error"]
            text = error["message"] if isinstance(error, dict) else error
        except (ValueError, KeyError, TypeError):
            return ""
        text = str(text).replace(self._api_key, "[redacted]")[:200]
        return f": {text}" if text else ""

    # Maps HTTP errors: 401/403 are credentials, 404 an unknown model, 429 a retryable rate limit,
    # other 4xx a rejected request, 5xx a retryable fault. The server's text is left out of
    # 401/403 errors because providers sometimes echo part of the key there.
    def _raise_for_status(self, response: httpx.Response):
        status = response.status_code
        if status < 400:
            return
        detail = self._server_message(response)
        if status in (401, 403):
            raise self._error(
                AdapterConfigError,
                f"server refused the credentials (HTTP {status}); "
                "check that the API key in the environment variable is valid",
            )
        if status == 404:
            raise self._error(
                AdapterConfigError,
                f"model or endpoint not found at {self.base_url} (HTTP 404); "
                f"check the model name and that base_url ends in /v1",
            )
        if status == 429:
            raise self._error(AdapterResponseError, f"rate limited (HTTP 429){detail}")
        if status < 500:
            raise self._error(
                AdapterRequestError, f"request rejected (HTTP {status}){detail}"
            )
        raise self._error(AdapterResponseError, f"server error (HTTP {status}){detail}")

    # Pulls the reply text and token usage out of a chat completions response.
    def _parse(self, response: httpx.Response) -> tuple[str, dict]:
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise self._error(
                AdapterResponseError, "response is not a chat completion"
            ) from None
        if not isinstance(text, str) or not text.strip():
            raise self._error(AdapterResponseError, "model returned an empty reply")
        usage = body.get("usage") or {}
        return text.strip(), usage if isinstance(usage, dict) else {}

    # Adds usage["cost_usd"] when prices are configured and the server reported token counts.
    def _with_cost(self, usage: dict) -> dict:
        if self._prices is None:
            return usage
        tokens_in, tokens_out = (
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )
        if not all(isinstance(t, int | float) for t in (tokens_in, tokens_out)):
            return usage
        cost = (tokens_in * self._prices[0] + tokens_out * self._prices[1]) / 1_000_000
        return {**usage, "cost_usd": round(cost, 8)}
