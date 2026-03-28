from typing import List, Optional
from pydantic import BaseModel
from app.models.wiki_structure import Section


class Revision(BaseModel):
    revid: int
    parentid: Optional[int] = None
    timestamp: str
    user: Optional[str] = None
    comment: Optional[str] = None
    content: Optional[str] = None
    sections: Optional[List[Section]] = None