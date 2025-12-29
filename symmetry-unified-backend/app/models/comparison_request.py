from pydantic import BaseModel, Field


class BaseCompareRequest(BaseModel):
    text_a: str = Field(..., description="First text to compare", min_length=1)
    text_b: str = Field(..., description="Second text to compare", min_length=1)


class LLMCompareRequest(BaseCompareRequest):
    pass


class SemanticCompareRequest(BaseCompareRequest):
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    model_name: str = Field(default="sentence-transformers/LaBSE", max_length=100)
