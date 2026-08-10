
from pydantic import BaseModel, Field


class Citation(BaseModel):
    model_config = {"frozen": True}
    label: str = Field()
    url: str | None = Field(default=None)


class Reference(BaseModel):
    model_config = {"frozen": True}
    label: str = Field(max_length=10000)
    id: str | None = Field(default=None, max_length=300)
    url: str | None = Field(default=None, max_length=2000)

class Section(BaseModel):
    title: str = Field()
    raw_content: str
    clean_content: str
    citations: list[Citation] | None = None
    citation_position: list[str] | None = None


class Article(BaseModel):
    title: str = Field()
    lang: str = Field()
    source: str = Field()
    sections: list[Section]
    references: list[Reference]
