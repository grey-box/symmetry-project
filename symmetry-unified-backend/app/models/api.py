from pydantic import BaseModel
from typing import List


class ModelSelectionResponse(BaseModel):
    """Response for model management operations (select, delete, import)."""

    successful: str


class ListResponse(BaseModel):
    """Generic list response used by model listing endpoints."""

    response: List[str]


from pydantic import BaseModel
from typing import List


class ModelSelectionResponse(BaseModel):
    """Response for model management operations (select, delete, import)."""

    successful: str


class ListResponse(BaseModel):
    """Generic list response used by model listing endpoints."""

    response: List[str]
