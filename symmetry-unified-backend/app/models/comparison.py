from pydantic import BaseModel, Field
from typing import List, Optional


class CompareRequest(BaseModel):
    """Request to compare two article text blobs using semantic similarity."""

    original_article_content: str
    translated_article_content: str
    original_language: str = Field(default="en")
    translated_language: str = Field(default="fr")
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    model_name: str = "sentence-transformers/LaBSE"


class SentenceDiff(BaseModel):
    """A sentence that differs between two compared articles."""

    sentence: str
    index: int


class ComparisonResult(BaseModel):
    """Raw comparison arrays from the semantic comparison engine."""

    left_article_array: List[str]
    right_article_array: List[str]
    left_article_missing_info_index: List[int]
    right_article_extra_info_index: List[int]


class CompareResponse(BaseModel):
    """Response for the legacy plain-text article comparison endpoint."""

    missing_info: List[SentenceDiff] = Field(default_factory=list)
    extra_info: List[SentenceDiff] = Field(default_factory=list)
    error_message: Optional[str] = None
    model_name: str = Field(
        default="sentence-transformers/LaBSE",
        description="Name of the model used for comparison",
    )
    similarity_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Similarity threshold used for comparison",
    )
    comparisons: Optional[List[ComparisonResult]] = None
