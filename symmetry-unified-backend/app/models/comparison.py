from __future__ import annotations

from pydantic import BaseModel, Field
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
    original_article_content: str = Field(
        ...,
        min_length=1,
        description="Full text of the original article"
    )
    translated_article_content: str = Field(
        ...,
        min_length=1,
        description="Full text of the translated article"
    )
    original_language: str = Field(
        ...,
        description="Language code of original article (e.g., 'en')",
        max_length=20
    )

    translated_language: str = Field(
        ...,
        description="Language code of translated article (e.g., 'fr')",
        max_length=20
    )
    
    model_name: str = Field(
        default="sentence-transformers/LaBSE",
        max_length=100,
        description="Sentence-transformer model name used for semantic comparison",
    )


class SentenceDiff(BaseModel):
    sentence: str
    index: int



class ComparisonResult(BaseModel):
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
