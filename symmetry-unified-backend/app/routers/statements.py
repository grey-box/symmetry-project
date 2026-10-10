"""API for splitting English LLM output into statements."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.statement_splitting import MAX_TEXT_LENGTH, split_statements

router = APIRouter(
    prefix="/symmetry/v1/statements",
    tags=["statements"],
)


class SplitStatementsRequest(BaseModel):
    text: str = Field(
        ...,
        strict=True,
        max_length=MAX_TEXT_LENGTH,
        description="English LLM-generated text, up to 100,000 characters.",
    )


class SplitStatementsResponse(BaseModel):
    statements: list[str] = Field(
        ...,
        description="Sentence-level statements in source order.",
    )


@router.post(
    "/split",
    response_model=SplitStatementsResponse,
    summary="Split LLM text into individual statements",
)
def split_llm_text(
    request: SplitStatementsRequest,
) -> SplitStatementsResponse:
    return SplitStatementsResponse(statements=split_statements(request.text))
