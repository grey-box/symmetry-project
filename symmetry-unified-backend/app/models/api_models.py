from pydantic import BaseModel
from typing import List


class ModelSelectionResponse(BaseModel):
    """Response for model management operations (select, delete, import)."""

    successful: str


class ListResponse(BaseModel):
    """Generic list response used by model listing endpoints."""

    response: List[str]


class FactExtractionRequest(BaseModel):
    section_content: str
    model_id: str
    section_title: str = ""
    num_facts: int = 1


class FactExtractionResponse(BaseModel):
    facts: List[str]
    model_used: str
    section_title: str = ""
