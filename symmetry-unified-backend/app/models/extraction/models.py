
from pydantic import BaseModel


class FactExtractionRequest(BaseModel):
    section_content: str
    model_id: str
    section_title: str = ""
    num_facts: int = 1


class FactExtractionResponse(BaseModel):
    facts: list[str]
    model_used: str
    section_title: str = ""
    chunks: list[str] = []
