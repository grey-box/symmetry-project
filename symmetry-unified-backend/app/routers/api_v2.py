"""API v2 router.

Declares the v2 comparison endpoints under ``/symmetry/v2``. Every endpoint
accepts a ``ComparisonRequest`` and documents ``ComparisonResponse``.
``POST /compare/llm-vs-wikipedia`` is implemented; the other endpoints return
``501 Not Implemented`` until their comparison logic is built.

Requests are validated before the handler runs, so an invalid body gets
``422``. The v1 API under ``/symmetry/v1`` is not affected by this module.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.v2 import ComparisonRequest, ComparisonResponse, ErrorResponse
from app.services.llm_vs_wikipedia import LlmVsWikipediaService
from app.services.v2_engines import CatalogEngineResolver
from app.services.v2_responses import (
    V2Failure,
    error_detail,
    error_response,
    new_request_id,
    success_response,
)
from app.services.wikipedia_reference import ParsedArticleReader

logger = logging.getLogger(__name__)

API_V2_PREFIX = "/symmetry/v2"

router = APIRouter(prefix=API_V2_PREFIX, tags=["v2"])

_NOT_IMPLEMENTED = {
    status.HTTP_501_NOT_IMPLEMENTED: {
        "description": "The endpoint is declared but not implemented yet."
    }
}

# Error statuses a comparison endpoint can return with an ErrorResponse body.
# 422 is left out: request validation errors still use FastAPI's default body.
_ERROR_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "A source could not be found (source_not_found).",
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorResponse,
        "description": "Unexpected failure, or a source could not be reached (internal_error).",
    },
    status.HTTP_502_BAD_GATEWAY: {
        "model": ErrorResponse,
        "description": "Every engine failed, with different errors or unreadable output.",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": ErrorResponse,
        "description": "No engine is available (engine_unavailable).",
    },
    status.HTTP_504_GATEWAY_TIMEOUT: {
        "model": ErrorResponse,
        "description": "Every engine timed out (engine_timeout).",
    },
}


# Builds the LLM vs Wikipedia service. Tests override this dependency with fakes.
def get_llm_vs_wikipedia_service() -> LlmVsWikipediaService:
    return LlmVsWikipediaService(ParsedArticleReader(), CatalogEngineResolver())


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
    response_model=ComparisonResponse,
    responses=_NOT_IMPLEMENTED,
)
async def compare(body: ComparisonRequest):
    raise _not_implemented(f"POST {API_V2_PREFIX}/compare")


@router.post(
    "/compare/llm-vs-wikipedia",
    summary="Compare LLM output against a Wikipedia article",
    description="""
Checks each statement of an LLM answer against a Wikipedia article.

Send exactly two sources: one `llm_output` source with the answer as `text`,
and one `wikipedia` source given by `url`, or by `title` with `language`
(optionally a `revision_id`). Each statement of the answer comes back with a
`label`, the engine's `confidence` and, when the engine quotes one, the
Wikipedia passage it relied on as `evidence`:

- `supported`: the article states the statement or clearly implies it.
- `contradicted`: the article says something that conflicts with it.
- `not_found`: the article does not address it. **This does not mean the
  statement is false**, only that the article text did not cover it.

`strategy` defaults to `factual_consistency`, the only strategy this endpoint
supports. `engines` lists model catalog ids; empty means the cheapest
configured model. If one of several engines fails, the response is `200`
with `status: "partial"` and the failure in `errors`; if every engine fails,
an `ErrorResponse` is returned.

Limits: only the first 12,000 characters of the article are checked, so
claims backed later in a long article can come back `not_found`. Generating
the answer on the server (`generate_with`), `pivot_language` and direction
`both` are not supported yet. Wikipedia text is licensed CC BY-SA 4.0:
show the source's `attribution` wherever its text or evidence is displayed.
""",
    response_model=ComparisonResponse,
    responses=_ERROR_RESPONSES,
)
async def compare_llm_vs_wikipedia(
    body: ComparisonRequest,
    service: Annotated[LlmVsWikipediaService, Depends(get_llm_vs_wikipedia_service)],
):
    request_id = new_request_id()
    try:
        response = await service.compare(body, request_id)
    except V2Failure as failure:
        return error_response(request_id, failure.errors)
    except Exception:
        logger.exception("LLM vs Wikipedia comparison failed (%s)", request_id)
        return error_response(
            request_id,
            [error_detail("internal_error", "The comparison failed unexpectedly.")],
        )
    return success_response(response)


@router.post(
    "/compare/llm-vs-llm",
    summary="Compare outputs of several LLMs for one prompt",
    description=(
        "Runs one prompt through several engines and compares their outputs. "
        "If one engine fails, the error is reported for that engine without "
        "failing the whole request. Not implemented yet."
    ),
    response_model=ComparisonResponse,
    responses=_NOT_IMPLEMENTED,
)
async def compare_llm_vs_llm(body: ComparisonRequest):
    raise _not_implemented(f"POST {API_V2_PREFIX}/compare/llm-vs-llm")
