from pydantic import BaseModel, Field
from typing import List, Optional


class Citation(BaseModel):
    model_config = {"frozen": True}
    label: str = Field()
    url: Optional[str] = Field(default=None)


class Reference(BaseModel):
    model_config = {"frozen": True}
    label: str = Field()
    id: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None)



class Section(BaseModel):
    title: str = Field()
    raw_content: str
    clean_content: str
    citations: Optional[List[Citation]] = None
    citation_position: Optional[List[str]] = None


class Article(BaseModel):
    title: str = Field()
    lang: str = Field()
    source: str = Field()
    sections: List[Section]
    references: List[Reference]
