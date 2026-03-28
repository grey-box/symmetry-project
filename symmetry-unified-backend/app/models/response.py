from pydantic import BaseModel, Field
from typing import List, Optional


class MissingInfo(BaseModel):
    sentence: str = Field()
    index: int
    similarity_score: Optional[float] = None


class ExtraInfo(BaseModel):
    sentence: str = Field()
    index: int
    similarity_score: Optional[float] = None


class SourceArticleResponse(BaseModel):
    sourceArticle: str
    articleLanguages: List[str]


class TranslateArticleResponse(BaseModel):
    translatedArticle: str


class ArticleComparisonResponse(BaseModel):
    missing_info: List[MissingInfo]
    extra_info: List[ExtraInfo]
    model_name: str = Field(default="sentence-transformers/LaBSE", description="Name of the model used for comparison")
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="Similarity threshold used for comparison")
