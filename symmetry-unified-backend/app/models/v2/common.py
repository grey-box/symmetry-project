"""Shared types for the API v2 published schema.

Field names, enum values and constraints follow
``docs/api-v2/api-v2-response-schema.md``. Enums are lowercase string
literals so that the generated JSON Schema matches
``docs/api-v2/api-v2-schema.json``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

API_VERSION = "2.0"

ComparisonMode = Literal["text_vs_text", "llm_vs_wikipedia", "llm_vs_llm"]
SourceKind = Literal["text", "document", "wikipedia", "llm_output"]
Direction = Literal["both", "first_to_second"]

# Strategy ids are an open set owned by the strategy registry, so they are
# plain strings rather than an enum. Known ids today: "semantic_similarity",
# "factual_consistency".
StrategyId = Annotated[str, Field(min_length=1)]

Score = Annotated[float, Field(ge=0.0, le=1.0)]


class V2Model(BaseModel):
    """Base class for v2 models: unknown fields are rejected.

    Matches ``additionalProperties: false`` in the JSON Schema. Requests with
    unknown fields fail validation, and the server cannot emit undocumented
    fields. Clients must still tolerate unknown fields (versioning rule 2).
    """

    model_config = ConfigDict(extra="forbid")


class Span(V2Model):
    """Location in ``Source.text``, in Unicode code points (Python indexing)."""

    start: int = Field(ge=0, description="0-based, inclusive")
    end: int = Field(ge=0, description="Exclusive")

    @model_validator(mode="after")
    def _end_not_before_start(self) -> Span:
        if self.end < self.start:
            raise ValueError("span end must not be before start")
        return self


class Usage(V2Model):
    """Time and cost of one engine call."""

    latency_ms: int = Field(ge=0, description="Wall-clock time spent in the engine")
    input_tokens: int | None = Field(ge=0)
    output_tokens: int | None = Field(ge=0)
    estimated_cost_usd: float | None = Field(ge=0)
