from __future__ import annotations

from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional


class CompareRequest(BaseModel):
    """Request to compare two article text blobs using semantic similarity."""

    text_a: str = Field(
        validation_alias=AliasChoices(
            "text_a", "original_article_content", "article_text_blob_1"
        )
    )
    text_b: str = Field(
        validation_alias=AliasChoices(
            "text_b", "translated_article_content", "article_text_blob_2"
        )
    )
    language_a: str = Field(
        default="en",
        validation_alias=AliasChoices(
            "language_a", "original_language", "article_text_blob_1_language"
        ),
    )
    language_b: str = Field(
        default="fr",
        validation_alias=AliasChoices(
            "language_b", "translated_language", "article_text_blob_2_language"
        ),
    )
    similarity_threshold: float = Field(
        default=0.75,
        validation_alias=AliasChoices("similarity_threshold", "comparison_threshold"),
    )
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
    comparisons: List[ComparisonResult] = Field(default_factory=list)
