from pydantic import BaseModel, Field


class ChunkedTranslateRequest(BaseModel):
    source_language: str = Field(..., min_length=2, max_length=10)
    target_language: str = Field(..., min_length=2, max_length=10)
    text: str = Field(..., min_length=1)
