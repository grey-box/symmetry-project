"""
Send one prompt to the user's chosen AI provider and get JSON back.

The API key comes from the app's settings with each request.  It is only
passed to the provider, never logged, stored or put in an error message.

Claude goes through the official Anthropic SDK.  Every other provider here
(OpenAI, Gemini, Groq, OpenRouter, or a local server such as Ollama)
offers an OpenAI-compatible /chat/completions endpoint, so one function
covers all of them and only the base URL and default model differ.
"""

import json
import logging
import re
from dataclasses import dataclass

import anthropic
import httpx

logger = logging.getLogger(__name__)

# Base URL and default model for each OpenAI-compatible provider.  The model
# can be changed in the app's settings; these are only starting points.
OPENAI_COMPATIBLE = {
    "openai": ("https://api.openai.com/v1", "gpt-5-mini"),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-2.5-flash",
    ),
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
    "openrouter": ("https://openrouter.ai/api/v1", "anthropic/claude-sonnet-5-5"),
}

DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"

# Claude models that take the effort setting and server-side fallbacks.
# Older models reject them, so they are only sent to these.
_EFFORT_MODEL_PREFIXES = (
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-haiku-5",
)
_FALLBACK_MODEL_PREFIXES = ("claude-opus-5", "claude-sonnet-5-5", "claude-fable-5")

_MAX_OUTPUT_TOKENS = 16_000
_TIMEOUT_SECONDS = 300.0

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")


class AiAgentError(Exception):
    """A provider call failed.  *status* is the HTTP status to return."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


@dataclass
class AgentReply:
    data: dict
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


def default_model(provider: str) -> str:
    if provider == "anthropic":
        return DEFAULT_ANTHROPIC_MODEL
    return OPENAI_COMPATIBLE.get(provider, ("", ""))[1]


def _parse_json(text: str) -> dict:
    """JSON object from a reply, allowing for a ```json fence around it."""
    cleaned = _CODE_FENCE_RE.sub("", text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Some models add a sentence before or after the object.
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise AiAgentError("The AI reply was not JSON.") from None
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            raise AiAgentError("The AI reply was not valid JSON.") from None
    if not isinstance(data, dict):
        raise AiAgentError("The AI reply was not a JSON object.")
    return data


# ---------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------


async def _ask_anthropic(
    api_key: str, model: str, system: str, prompt: str, schema: dict
) -> AgentReply:
    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=_TIMEOUT_SECONDS)
    output_config: dict = {"format": {"type": "json_schema", "schema": schema}}
    if model.startswith(_EFFORT_MODEL_PREFIXES):
        output_config["effort"] = "medium"

    request = {
        "model": model,
        "max_tokens": _MAX_OUTPUT_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
        "output_config": output_config,
    }
    try:
        if model.startswith(_FALLBACK_MODEL_PREFIXES):
            # If the model declines, the API retries on a fallback model in
            # the same call instead of returning nothing.
            response = await client.beta.messages.create(
                **request,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        else:
            response = await client.messages.create(**request)
    except anthropic.AuthenticationError:
        raise AiAgentError("Anthropic rejected the API key.", 401) from None
    except anthropic.PermissionDeniedError:
        raise AiAgentError(
            "This Anthropic API key can't use that model.", 403
        ) from None
    except anthropic.NotFoundError:
        raise AiAgentError(
            f"Anthropic doesn't know the model '{model}'.", 400
        ) from None
    except anthropic.RateLimitError:
        raise AiAgentError(
            "Anthropic rate limit reached. Try again shortly.", 429
        ) from None
    except anthropic.BadRequestError as e:
        raise AiAgentError(f"Anthropic refused the request: {e.message}", 400) from None
    except anthropic.APIStatusError as e:
        raise AiAgentError(f"Anthropic returned an error ({e.status_code}).") from None
    except anthropic.APIConnectionError:
        raise AiAgentError("Could not reach the Anthropic API.") from None

    if response.stop_reason == "refusal":
        raise AiAgentError("The model declined to summarize this revision.", 422)
    if response.stop_reason == "max_tokens":
        raise AiAgentError("The AI reply was cut off before it finished.")

    text = "".join(block.text for block in response.content if block.type == "text")
    return AgentReply(
        data=_parse_json(text),
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


# ---------------------------------------------------------------------------
# OpenAI-compatible providers
# ---------------------------------------------------------------------------


def _status_error(provider: str, response: httpx.Response) -> AiAgentError:
    try:
        detail = response.json().get("error", {})
        message = detail.get("message", "") if isinstance(detail, dict) else str(detail)
    except ValueError:
        message = ""
    if response.status_code == 401:
        return AiAgentError(f"{provider} rejected the API key.", 401)
    if response.status_code == 429:
        return AiAgentError(f"{provider} rate limit reached. Try again shortly.", 429)
    message = message[:300] or response.reason_phrase
    return AiAgentError(f"{provider} returned {response.status_code}: {message}")


async def _ask_openai_compatible(
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    system: str,
    prompt: str,
    schema: dict,
) -> AgentReply:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "revision_summary",
                "schema": schema,
                "strict": True,
            },
        },
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    url = base_url.rstrip("/") + "/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 400:
                # Not every model takes a JSON schema.  Plain JSON mode is
                # widely supported, and the prompt already lists the fields.
                payload["response_format"] = {"type": "json_object"}
                response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise AiAgentError(f"{provider} did not answer in time.", 504) from None
    except httpx.RequestError as e:
        raise AiAgentError(f"Could not reach {url} ({type(e).__name__}).") from None

    if response.status_code != 200:
        raise _status_error(provider, response)

    body = response.json()
    try:
        choice = body["choices"][0]
        text = choice["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise AiAgentError(f"{provider} sent a reply with no message.") from None
    if choice.get("finish_reason") == "length":
        raise AiAgentError("The AI reply was cut off before it finished.")

    usage = body.get("usage") or {}
    return AgentReply(
        data=_parse_json(text),
        model=body.get("model", model),
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
    )


async def ask_for_json(
    provider: str,
    api_key: str,
    model: str | None,
    system: str,
    prompt: str,
    schema: dict,
    base_url: str | None = None,
) -> AgentReply:
    """
    Ask *provider* to answer *prompt* with JSON matching *schema*.

    Raises AiAgentError with a message that is safe to show in the app.
    """
    model = (model or "").strip() or default_model(provider)

    if provider == "anthropic":
        if not api_key:
            raise AiAgentError("Add your Anthropic API key in Settings first.", 400)
        return await _ask_anthropic(api_key, model, system, prompt, schema)

    if provider == "custom":
        if not base_url:
            raise AiAgentError("Set the endpoint URL for the custom provider.", 400)
        if not model:
            raise AiAgentError("Set a model name for the custom provider.", 400)
        endpoint = base_url
    elif provider in OPENAI_COMPATIBLE:
        if not api_key:
            raise AiAgentError(f"Add your {provider} API key in Settings first.", 400)
        endpoint = OPENAI_COMPATIBLE[provider][0]
    else:
        raise AiAgentError(f"Unknown AI provider '{provider}'.", 400)

    return await _ask_openai_compatible(
        provider, endpoint, api_key, model, system, prompt, schema
    )
