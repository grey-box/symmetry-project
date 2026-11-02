import time
from urllib.parse import urlparse

import httpx

from app.core.settings import LOCAL_SLM_BASE_URL

from .base import GenerationRequest, GenerationResult, ModelAdapter
from .errors import (
    AdapterConfigError,
    AdapterRequestError,
    AdapterResponseError,
    AdapterTimeoutError,
)
from .registry import register_adapter


# Local small language model served over an OpenAI-compatible API (Ollama, LM Studio, llama.cpp).
# Config: base_url (defaults to LOCAL_SLM_BASE_URL) and transport (an httpx transport, for tests).
# A missing model name or a base_url that is not an http(s) URL raises AdapterConfigError here.
@register_adapter("local_slm")
class LocalSLMAdapter(ModelAdapter):
    def __init__(self, model_name: str, **config):
        super().__init__(model_name, **config)
        if not isinstance(model_name, str) or not model_name.strip():
            raise self._error(AdapterConfigError, "model name must not be empty")
        base_url = str(config.get("base_url") or "").strip() or LOCAL_SLM_BASE_URL
        parts = urlparse(base_url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise self._error(
                AdapterConfigError,
                f"base_url must be an http(s) URL such as http://localhost:11434/v1, got {base_url!r}",
            )
        self.base_url = base_url.rstrip("/")
        self._transport = config.get("transport")

    async def generate(self, request: GenerationRequest) -> GenerationResult:
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

        start = time.perf_counter()
        try:
            async with self._client(request.timeout_s) as client:
                response = await client.post("/chat/completions", json=payload)
        except httpx.TimeoutException:
            raise self._error(
                AdapterTimeoutError, f"no reply within {request.timeout_s}s"
            ) from None
        except httpx.RequestError as e:
            raise self._error(
                AdapterRequestError,
                f"could not reach local model server at {self.base_url}: {type(e).__name__}",
            ) from None
        latency_ms = (time.perf_counter() - start) * 1000

        self._raise_for_status(response)
        text, usage = self._parse(response)
        return GenerationResult(
            text=text,
            model=self.model_name,
            provider=self.provider,
            latency_ms=latency_ms,
            usage=usage,
        )

    # Returns True when the server answers its model listing; never raises.
    async def health_check(self) -> bool:
        try:
            async with self._client(5.0) as client:
                response = await client.get("/models")
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    def _client(self, timeout_s: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url, timeout=timeout_s, transport=self._transport
        )

    def _error(self, cls, message):
        return cls(message, provider=self.provider, model=self.model_name)

    # Returns the server's own error text (capped) so messages like "add usage credits" reach the caller.
    @staticmethod
    def _server_message(response: httpx.Response) -> str:
        try:
            error = response.json()["error"]
            text = error["message"] if isinstance(error, dict) else error
        except (ValueError, KeyError, TypeError):
            return ""
        return f": {str(text)[:200]}" if text else ""

    # Maps HTTP errors: 401/403 are credentials, 404 an unknown model, 429 a retryable rate limit,
    # other 4xx a rejected request, 5xx a retryable fault.
    def _raise_for_status(self, response: httpx.Response):
        status = response.status_code
        if status < 400:
            return
        detail = self._server_message(response)
        if status in (401, 403):
            raise self._error(
                AdapterConfigError,
                f"server refused the credentials (HTTP {status}){detail}; sign in to the server (e.g. Ollama cloud models)",
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
