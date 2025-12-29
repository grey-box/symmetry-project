from pydantic import BaseModel, Field
from typing import List


class CompareRequest(BaseModel):
    article_text_blob_1: str = Field(
        ..., description="First article text", min_length=1
    )
    article_text_blob_2: str = Field(
        ..., description="Second article text", min_length=1
    )
    article_text_blob_1_language: str = Field(
        ..., description="Language of first article", max_length=10
    )
    article_text_blob_2_language: str = Field(
        ..., description="Language of second article", max_length=10
    )
    comparison_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    model_name: str = Field(
        default="sentence-transformers/LaBSE",
        description="Model name for semantic comparison",
        max_length=100,
    )


class ComparisonResult(BaseModel):
    left_article_array: List[str]
    right_article_array: List[str]
    left_article_missing_info_index: List[int]
    right_article_extra_info_index: List[int]


class CompareResponse(BaseModel):
    comparisons: List[ComparisonResult]
