from __future__ import annotations

from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional


# class CompareRequest(BaseModel):
#     article_text_blob_1: str = Field(
#         ..., description="First article text", min_length=1
#     )
#     article_text_blob_2: str = Field(
#         ..., description="Second article text", min_length=1
#     )
#     article_text_blob_1_language: str = Field(
#         ..., description="Language of first article", max_length=10
#     )
#     article_text_blob_2_language: str = Field(
#         ..., description="Language of second article", max_length=10
#     )
#     comparison_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
#     model_name: str = Field(
#         default="sentence-transformers/LaBSE",
#         description="Model name for semantic comparison",
#         max_length=100,
#     )

class CompareRequest(BaseModel):
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
    sentence: str
    index: int



class ComparisonResult(BaseModel):
    """Raw comparison arrays from the semantic comparison engine."""

    left_article_array: List[str]
    right_article_array: List[str]
    left_article_missing_info_index: List[int]
    right_article_extra_info_index: List[int]


# class CompareResponse(BaseModel):
#     comparisons: List[ComparisonResult]


# class CompareResponse(BaseModel):
#     missing_info: list[SentenceDiff] = []
#     extra_info: list[SentenceDiff] = []
#     error_message: str | None = None

class CompareResponse(BaseModel):
    missing_info: List[SentenceDiff] = Field(default_factory=list)
    extra_info: List[SentenceDiff] = Field(default_factory=list)
    error_message: Optional[str] = None
    comparisons: List[ComparisonResult] = Field(default_factory=list)
