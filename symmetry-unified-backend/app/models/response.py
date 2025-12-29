from pydantic import BaseModel, Field
from typing import List, Optional


class MissingInfo(BaseModel):
    sentence: str = Field(max_length=2000)
    index: int
    similarity_score: Optional[float] = None


class ExtraInfo(BaseModel):
    sentence: str = Field(max_length=2000)
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
