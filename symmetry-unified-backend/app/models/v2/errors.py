"""Error models for API v2 (schema section 8)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.models.v2.common import V2Model

ErrorCode = Literal[
    "invalid_request",
    "unsupported_engine",
    "unsupported_strategy",
    "source_not_found",
    "rate_limited",
    "engine_bad_output",
    "engine_unavailable",
    "engine_timeout",
    "internal_error",
]
ErrorScope = Literal["request", "source", "engine"]


class ErrorDetail(V2Model):
    """One failure: of the whole request, one source, or one engine."""

    code: ErrorCode
    message: str = Field(description="Human-readable; safe to show to users")
    scope: ErrorScope
    source_id: str | None = Field(description="Set when scope is 'source'")
    engine_id: str | None = Field(
        description=(
            "Set when scope is 'engine', and with scope 'source' when the "
            "generating engine failed"
        )
    )
    retryable: bool = Field(description="Whether the same request could succeed later")
    details: dict[str, Any] | None = Field(
        description="Extra structured context. Never stack traces"
    )


class ErrorResponse(V2Model):
    """Returned when the whole request failed and nothing usable was produced."""

    api_version: str
    request_id: str
    status: Literal["failed"]
    errors: list[ErrorDetail] = Field(min_length=1)
