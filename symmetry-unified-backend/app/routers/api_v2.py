"""API v2 router.

Declares the v2 comparison endpoints under ``/symmetry/v2``. Every endpoint
accepts a ``ComparisonRequest`` and documents ``ComparisonResponse``.
``POST /compare/llm-vs-wikipedia`` and ``POST /compare/llm-vs-llm`` are
implemented; ``POST /compare`` returns ``501 Not Implemented`` until its
comparison logic is built.

Requests are validated before the handler runs, so an invalid body gets
``422``. The v1 API under ``/symmetry/v1`` is not affected by this module.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.v2 import ComparisonRequest, ComparisonResponse, ErrorResponse
from app.services.llm_vs_llm import LlmVsLlmService
from app.services.llm_vs_wikipedia import LlmVsWikipediaService
from app.services.v2_engines import CatalogEngineResolver
from app.services.v2_responses import (
    V2Failure,
    error_detail,
    error_response,
    new_request_id,
    success_response,
)
from app.services.v2_strategies import PROFILES, available_strategies
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


# Markdown list of the strategies a mode offers, for the OpenAPI descriptions.
def _strategy_docs(mode: str) -> str:
    return "\n".join(
        f"- `{sid}` ({PROFILES[sid].score_basis}): {PROFILES[sid].description}"
        for sid in available_strategies(mode)
    )


# Builds the LLM vs Wikipedia service. Tests override this dependency with fakes.
def get_llm_vs_wikipedia_service() -> LlmVsWikipediaService:
    return LlmVsWikipediaService(ParsedArticleReader(), CatalogEngineResolver())


# Builds the LLM vs LLM service. Tests override this dependency with fakes.
def get_llm_vs_llm_service() -> LlmVsLlmService:
    return LlmVsLlmService()


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
`label` and, where the strategy finds one, the Wikipedia passage as `evidence`:

- `supported`: the article states the statement or clearly implies it.
- `contradicted`: the article says something that conflicts with it.
- `partial`: close to an article sentence but below the similarity threshold
  (`semantic_similarity` only, when `options.partial_threshold` is set).
- `not_found`: the article does not address it. **This does not mean the
  statement is false**, only that the article text did not cover it.

**Choosing a strategy.** Set `strategy` in the body; `null` uses
`factual_consistency`. The route stays the same for every strategy:
"""
    + _strategy_docs("llm_vs_wikipedia")
    + """

`engines` lists model catalog ids for language-model strategies; empty means
the cheapest configured model. Embedding strategies use the server's embedding
model, so `engines` must be empty. A strategy that is unknown or cannot run on
the requested engines is rejected with `422 unsupported_strategy`, listing the
available ones. If one of several engines fails, the response is `200` with
`status: "partial"`; if every engine fails, an `ErrorResponse` is returned.

Limits: `factual_consistency` checks only the first 12,000 characters of the
article, so claims backed later in a long article can come back `not_found`.
Generating the answer on the server (`generate_with`), `pivot_language` and
direction `both` are not supported yet. Wikipedia text is licensed CC BY-SA
4.0: show the source's `attribution` wherever its text or evidence is displayed.
""",
    response_model=ComparisonResponse,
    responses=_ERROR_RESPONSES,
)
async def compare_llm_vs_wikipedia(
    body: ComparisonRequest,
    service: Annotated[LlmVsWikipediaService, Depends(get_llm_vs_wikipedia_service)],
):
    return await _respond(service, body, "LLM vs Wikipedia")


@router.post(
    "/compare/llm-vs-llm",
    summary="Compare several LLM answers to the same prompt",
    description="""
Compares two or more LLM answers to the same prompt and highlights where they
disagree.

Send `mode: "llm_vs_llm"`, the `prompt` (optional, echoed back) and two or more
`llm_output` sources, each with the answer as `text`. Every pair of answers
gets one result (3 answers give 3 pairs). Within a pair, each sentence of both
answers is labelled against the other answer:

- `supported`: the other answer says something very similar.
- `partial`: close, but below the similarity threshold (only when
  `options.partial_threshold` is set).
- `not_found`: the other answer does not say it.

Each judged sentence carries `best_match_similarity` and, when matched, the
other answer's sentence as `counterpart_statement` evidence. The pair's
`alignments` mark sentences `equal`, `modified`, `missing` (only in the first
answer) or `added` (only in the second): these are the disagreements to
highlight, located by each statement's `span`. `overall_score` is the mean
similarity.

**Similar meaning is not agreement on facts, and agreement between models is
not proof that they are right.** "400 metres tall" and "330 metres tall" score
as similar.

**Choosing a strategy.** Set `strategy` in the body; `null` uses
`semantic_similarity`. The route stays the same for every strategy:
"""
    + _strategy_docs("llm_vs_llm")
    + """

Embedding strategies use the server's embedding model, so `engines` must be
empty. If one pair cannot be compared, the response is `200` with
`status: "partial"`; if no pair can be, an `ErrorResponse` is returned.

Not supported yet: generating the answers on the server (`generate_with`), which
needs the multi-engine fan-out with per-engine errors; direction
`first_to_second`; `pivot_language`.
""",
    response_model=ComparisonResponse,
    responses=_ERROR_RESPONSES,
)
async def compare_llm_vs_llm(
    body: ComparisonRequest,
    service: Annotated[LlmVsLlmService, Depends(get_llm_vs_llm_service)],
):
    return await _respond(service, body, "LLM vs LLM")


# Runs a comparison service and returns its response, or the ErrorResponse when
# nothing usable was produced. Every response carries the request id header.
async def _respond(service, body: ComparisonRequest, name: str):
    request_id = new_request_id()
    try:
        response = await service.compare(body, request_id)
    except V2Failure as failure:
        return error_response(request_id, failure.errors)
    except Exception:
        logger.exception("%s comparison failed (%s)", name, request_id)
        return error_response(
            request_id,
            [error_detail("internal_error", "The comparison failed unexpectedly.")],
        )
    return success_response(response)
