from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.wiki_structure import Citation, Reference, Section


class CitedArticle(BaseModel):
    title: str = Field(max_length=500)
    count: int = Field(ge=0)


class StructuredArticleResponse(BaseModel):
    title: str = Field(max_length=500)
    lang: str = Field(max_length=10)
    source: str = Field(max_length=100)
    sections: List[Section]
    references: List[Reference]
    total_sections: int = Field(ge=0)
    total_citations: int = Field(ge=0)
    total_references: int = Field(ge=0)


class StructuredSectionResponse(BaseModel):
    title: str = Field(max_length=500)
    raw_content: str
    clean_content: str
    citations: Optional[List[Citation]] = None
    citation_position: Optional[List[str]] = None
    word_count: int = Field(ge=0)
    citation_count: int = Field(ge=0)


class StructuredCitationResponse(BaseModel):
    citations: List[Citation]
    total_citations: int = Field(ge=0)
    unique_targets: int = Field(ge=0)
    most_cited_articles: List[CitedArticle]


class StructuredReferenceResponse(BaseModel):
    references: List[Reference]
    total_references: int = Field(ge=0)
    references_with_urls: int = Field(ge=0)
    reference_density: float = Field(ge=0)
