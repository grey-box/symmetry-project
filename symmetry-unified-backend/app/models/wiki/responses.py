
from pydantic import BaseModel, Field

from app.models.wiki.structure import Citation, Reference, Section


class CitedArticle(BaseModel):
    title: str = Field()
    count: int = Field(ge=0)


class StructuredArticleResponse(BaseModel):
    title: str = Field()
    lang: str = Field()
    source: str = Field()
    sections: list[Section]
    references: list[Reference]
    total_sections: int = Field(ge=0)
    total_citations: int = Field(ge=0)
    total_references: int = Field(ge=0)


class StructuredSectionResponse(BaseModel):
    title: str = Field()
    raw_content: str
    clean_content: str
    citations: list[Citation] | None = None
    citation_position: list[str] | None = None
    word_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)


class StructuredCitationResponse(BaseModel):
    citations: list[Citation]
    total_citations: int = Field(ge=0)
    unique_targets: int = Field(ge=0)
    most_cited_articles: list[CitedArticle]


class StructuredReferenceResponse(BaseModel):
    references: list[Reference]
    total_references: int = Field(ge=0)
    references_with_urls: int = Field(ge=0)
    reference_density: float = Field(ge=0)


class SourceArticleResponse(BaseModel):
    sourceArticle: str
    articleLanguages: list[str]


class AvailableTargetLanguage(BaseModel):
    lang: str
    title: str


class ArticleLanguagesResponse(BaseModel):
    source_lang: str
    source_title: str
    available_targets: list[AvailableTargetLanguage]


class TranslateArticleResponse(BaseModel):
    translatedArticle: str
