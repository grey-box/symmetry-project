from pydantic import BaseModel, Field
from typing import List, Optional


class Citation(BaseModel):
    model_config = {"frozen": True}
    label: str = Field(max_length=500)
    url: Optional[str] = Field(default=None, max_length=2000)


class Reference(BaseModel):
    model_config = {"frozen": True}
    label: str = Field(max_length=500)
    id: Optional[str] = Field(default=None, max_length=100)
    url: Optional[str] = Field(default=None, max_length=2000)


class Section(BaseModel):
    title: str = Field(max_length=500)
    raw_content: str
    clean_content: str
    citations: Optional[List[Citation]] = None
    citation_position: Optional[List[str]] = None


class Article(BaseModel):
    title: str = Field(max_length=500)
    lang: str = Field(max_length=10)
    source: str = Field(max_length=100)
    sections: List[Section]
    references: List[Reference]
