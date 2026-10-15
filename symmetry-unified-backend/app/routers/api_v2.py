"""API v2 router skeleton.

Declares the v2 comparison endpoints under ``/symmetry/v2`` so that the
versioned paths exist and appear in the OpenAPI document. Every endpoint
returns ``501 Not Implemented`` until its comparison logic is built.

Request and response models are attached to these endpoints when the v2
Pydantic models are implemented. The v1 API under ``/symmetry/v1`` is not
affected by this module.
"""

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

API_V2_PREFIX = "/symmetry/v2"
V2_RATE_LIMIT = "60/minute"

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix=API_V2_PREFIX, tags=["v2"])

_NOT_IMPLEMENTED = {
    status.HTTP_501_NOT_IMPLEMENTED: {
        "description": "The endpoint is declared but not implemented yet."
    }
}
_RATE_LIMITED = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "description": (
            "Rate limit exceeded. Maximum 60 requests per minute per client."
            )
    }
}

def _not_implemented(endpoint: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{endpoint} is not implemented yet.",
    )


@router.post(
    "/compare",
    summary="Compare two text sources",
    description=(
        "Generic comparison of two sources (raw text, a Wikipedia article or "
        "LLM output). The comparison mode and strategy are selected in the "
        "request body. Not implemented yet."
    ),
    responses={**_NOT_IMPLEMENTED, **_RATE_LIMITED},
)
@limiter.limit(V2_RATE_LIMIT)
async def compare(request: Request):
    raise _not_implemented(f"POST {API_V2_PREFIX}/compare")


@router.post(
    "/compare/llm-vs-wikipedia",
    summary="Compare LLM output against a Wikipedia article",
    description=(
        "Labels each statement of the LLM output as supported, contradicted "
        "or not found in the matching Wikipedia article, with a confidence "
        "score and evidence. Not implemented yet."
    ),
    responses={**_NOT_IMPLEMENTED, **_RATE_LIMITED},
)
@limiter.limit(V2_RATE_LIMIT)
async def compare_llm_vs_wikipedia(request: Request):
    raise _not_implemented(f"POST {API_V2_PREFIX}/compare/llm-vs-wikipedia")


@router.post(
    "/compare/llm-vs-llm",
    summary="Compare outputs of several LLMs for one prompt",
    description=(
        "Runs one prompt through several engines and compares their outputs. "
        "If one engine fails, the error is reported for that engine without "
        "failing the whole request. Not implemented yet."
    ),
    responses={**_NOT_IMPLEMENTED, **_RATE_LIMITED},
)
@limiter.limit(V2_RATE_LIMIT)
async def compare_llm_vs_llm(request: Request):
    raise _not_implemented(f"POST {API_V2_PREFIX}/compare/llm-vs-llm")
