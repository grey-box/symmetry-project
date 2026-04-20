from pydantic import BaseModel
from typing import List


class FactExtractionRequest(BaseModel):
    section_content: str
    model_id: str
    section_title: str = ""
    num_facts: int = 1


class FactExtractionResponse(BaseModel):
    facts: List[str]
    model_used: str
    section_title: str = ""
    chunks: List[str] = []
from pydantic import BaseModel
from typing import List


class FactExtractionRequest(BaseModel):
    section_content: str
    model_id: str
    section_title: str = ""
    num_facts: int = 1


class FactExtractionResponse(BaseModel):
    facts: List[str]
    model_used: str
    section_title: str = ""
    chunks: List[str] = []
