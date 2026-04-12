from pydantic import BaseModel, Field


class BaseCompareRequest(BaseModel):
    """Base request for text comparison endpoints."""

    original_article_content: str = Field(
        ..., description="Original article text", min_length=1
    )
    translated_article_content: str = Field(
        ..., description="Translated article text", min_length=1
    )


class SemanticCompareRequest(BaseCompareRequest):
    """Request for semantic comparison with configurable model and threshold."""

    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    model_name: str = Field(default="sentence-transformers/LaBSE", max_length=100)


class ChunkedTranslateRequest(BaseModel):
    source_language: str = Field(..., min_length=2, max_length=10)
    target_language: str = Field(..., min_length=2, max_length=10)
    text: str = Field(..., min_length=1)
