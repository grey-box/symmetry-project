"""Builds API v2 response bodies: success envelopes, errors and failed results.

Follows section 8 of ``docs/api-v2/api-v2-response-schema.md``: a request
where some work failed returns ``200`` with ``status: "partial"``; a request
where nothing usable was produced returns an ``ErrorResponse`` with the HTTP
status of its error code.
"""

import uuid
from typing import Any

from fastapi.responses import JSONResponse

from app.models.v2 import (
    API_VERSION,
    ComparisonResponse,
    Engine,
    ErrorDetail,
    ErrorResponse,
    Result,
    Usage,
)
from app.services.v2_engines import EngineHandle

REQUEST_ID_HEADER = "X-Request-ID"

# HTTP status when the error is fatal, and whether a retry could succeed (schema section 8).
ERROR_CODES: dict[str, tuple[int, bool]] = {
    "invalid_request": (422, False),
    "unsupported_engine": (422, False),
    "unsupported_strategy": (422, False),
    "source_not_found": (404, False),
    "rate_limited": (429, True),
    "engine_bad_output": (502, True),
    "engine_unavailable": (503, True),
    "engine_timeout": (504, True),
    "internal_error": (500, True),
}


# Raised by a v2 endpoint's logic when nothing usable can be returned.
class V2Failure(Exception):
    def __init__(self, errors: list[ErrorDetail]) -> None:
        super().__init__("; ".join(e.message for e in errors))
        self.errors = errors


# Returns a new request id, also sent as the X-Request-ID header.
def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


# Builds one error entry. retryable defaults to the value the schema gives the code.
def error_detail(
    code: str,
    message: str,
    scope: str = "request",
    *,
    source_id: str | None = None,
    engine_id: str | None = None,
    retryable: bool | None = None,
    details: dict[str, Any] | None = None,
) -> ErrorDetail:
    return ErrorDetail(
        code=code,
        message=message,
        scope=scope,
        source_id=source_id,
        engine_id=engine_id,
        retryable=ERROR_CODES[code][1] if retryable is None else retryable,
        details=details,
    )


# Shortcut for raising a failure with a single error.
def fail(code: str, message: str, scope: str = "request", **fields: Any) -> V2Failure:
    return V2Failure([error_detail(code, message, scope, **fields)])


# HTTP status for an ErrorResponse: the code's status if all errors share one code,
# otherwise 502 (schema section 8, rule 3).
def error_status(errors: list[ErrorDetail]) -> int:
    codes = {error.code for error in errors}
    if len(codes) == 1:
        return ERROR_CODES[codes.pop()][0]
    return 502


# The ErrorResponse returned when the whole request failed.
def error_response(request_id: str, errors: list[ErrorDetail]) -> JSONResponse:
    body = ErrorResponse(
        api_version=API_VERSION, request_id=request_id, status="failed", errors=errors
    )
    return JSONResponse(
        body.model_dump(mode="json"),
        status_code=error_status(errors),
        headers={REQUEST_ID_HEADER: request_id},
    )


# The 200 response for a comparison that produced at least one usable result.
def success_response(response: ComparisonResponse) -> JSONResponse:
    return JSONResponse(
        response.model_dump(mode="json"),
        headers={REQUEST_ID_HEADER: response.request_id},
    )


# The schema's description of the engine behind a handle.
def engine_model(handle: EngineHandle) -> Engine:
    return Engine(
        id=handle.id,
        type=handle.type,
        provider=handle.provider,
        model=handle.model,
        fallback_from=None,
    )


# Usage with only the wall-clock time known.
def latency_usage(latency_ms: float) -> Usage:
    return Usage(
        latency_ms=max(0, round(latency_ms)),
        input_tokens=None,
        output_tokens=None,
        estimated_cost_usd=None,
    )


# The entry for an engine that failed: kept in results with empty lists (rule 2).
def failed_result(
    source_ids: tuple[str, str],
    handle: EngineHandle,
    direction: str,
    latency_ms: float,
) -> Result:
    return Result(
        source_ids=source_ids,
        engine=engine_model(handle),
        status="failed",
        direction=direction,
        comparison_language=None,
        overall_score=None,
        score_basis=None,
        statements=[],
        alignments=[],
        usage=latency_usage(latency_ms),
    )
