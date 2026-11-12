"""Pydantic models for the API v2 published schema.

See ``docs/api-v2/api-v2-response-schema.md``.
"""

from app.models.v2.common import API_VERSION, Span, Usage
from app.models.v2.errors import ErrorDetail, ErrorResponse
from app.models.v2.request import ComparisonOptions, ComparisonRequest, SourceInput
from app.models.v2.response import (
    Alignment,
    Block,
    ComparisonResponse,
    Engine,
    Evidence,
    GeneratedBy,
    Result,
    Source,
    Statement,
    WordDiffToken,
)

__all__ = [
    "API_VERSION",
    "Alignment",
    "Block",
    "ComparisonOptions",
    "ComparisonRequest",
    "ComparisonResponse",
    "Engine",
    "ErrorDetail",
    "ErrorResponse",
    "Evidence",
    "GeneratedBy",
    "Result",
    "Source",
    "SourceInput",
    "Span",
    "Statement",
    "Usage",
    "WordDiffToken",
]
