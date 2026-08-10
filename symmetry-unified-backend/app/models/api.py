
from pydantic import BaseModel


class ModelSelectionResponse(BaseModel):
    """Response for model management operations (select, delete, import)."""

    successful: str


class ListResponse(BaseModel):
    """Generic list response used by model listing endpoints."""

    response: list[str]
