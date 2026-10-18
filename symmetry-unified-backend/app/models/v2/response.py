"""Response models for API v2 (schema sections 5 to 7).

Every field is required, nullable ones included: optional values are sent as
``null``, never left out. Lists that are always computed (``statements``,
``alignments``, ``evidence``, ``errors``) are never ``null``.

Cross-field rules a JSON Schema cannot express (unique ids, references that
resolve, spans that match the text, labels allowed per ``score_basis``) are
checked by contract tests, not here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.models.v2.common import (
    ComparisonMode,
    Direction,
    Score,
    SourceKind,
    Span,
    StrategyId,
    Usage,
    V2Model,
)
from app.models.v2.errors import ErrorDetail

EngineType = Literal["embedding", "local_slm", "cloud_llm", "openrouter"]
BlockType = Literal["heading", "paragraph", "blockquote", "list", "table", "image"]
StatementLabel = Literal[
    "supported", "partial", "contradicted", "not_found", "unverifiable"
]
ScoreBasis = Literal["cosine_similarity", "model_reported", "rule_based"]
EvidenceKind = Literal["counterpart_statement", "wikipedia_passage", "model_rationale"]
AlignmentCategory = Literal["equal", "modified", "missing", "added"]
WordTokenType = Literal["equal", "insert", "delete", "replace"]


class GeneratedBy(V2Model):
    """The engine that wrote a server-generated source."""

    engine_id: str
    provider: str | None
    model: str
    usage: Usage | None


class Block(V2Model):
    """A layout element of a source, used by clients to render it."""

    id: str
    type: BlockType
    span: Span | None = Field(description="null for blocks with no text")
    section_ref: str | None
    level: int | None = Field(ge=1, description="Heading level; null for other types")
    url: str | None = Field(description="Image location; null for other types")
    caption: str | None


class Source(V2Model):
    """A compared source, as obtained by the server."""

    id: str
    kind: SourceKind
    label: str | None
    language: str | None
    url: str | None
    revision_id: int | None
    license: str | None
    attribution: str | None
    generated_by: GeneratedBy | None
    text: str | None = Field(
        description=(
            "Exact original text that spans refer to. null if the source could "
            "not be obtained or include_source_text is false"
        )
    )
    blocks: list[Block] | None


class Engine(V2Model):
    """The engine that compared a pair of sources."""

    id: str
    type: EngineType
    provider: str | None
    model: str
    fallback_from: str | None


class Evidence(V2Model):
    """Why an engine chose a statement's label."""

    kind: EvidenceKind
    source_id: str | None
    statement_id: str | None
    text: str
    url: str | None


class Statement(V2Model):
    """One sentence-level claim from one source of the pair."""

    id: str
    source_id: str
    index: int = Field(ge=0)
    text: str
    translated_text: str | None
    span: Span
    section_ref: str | None
    block_id: str | None
    label: StatementLabel | None
    confidence: Score | None
    best_match_similarity: Score | None
    evidence: list[Evidence]


class WordDiffToken(V2Model):
    """Word-level diff token (``WordToken`` in the schema document).

    Same fields as the v1 paragraph-diff ``WordToken``, but strict. It has a
    different class name so the OpenAPI document keeps the v1 schema name
    ``WordToken`` unchanged instead of renaming both on collision.
    """

    type: WordTokenType
    text: str | None
    old: str | None
    new: str | None


class Alignment(V2Model):
    """Links a statement of the first source to one of the second, or marks it unpaired."""

    id: str
    source_ref: str | None
    target_ref: str | None
    category: AlignmentCategory
    similarity: Score | None
    word_diff: list[WordDiffToken] | None


class Result(V2Model):
    """The output of one engine for one pair of sources."""

    source_ids: tuple[str, str]
    engine: Engine
    status: Literal["ok", "failed"]
    direction: Direction
    comparison_language: str | None
    overall_score: Score | None
    score_basis: ScoreBasis | None
    statements: list[Statement]
    alignments: list[Alignment]
    usage: Usage | None


class ComparisonResponse(V2Model):
    """The single response format returned by every v2 comparison."""

    api_version: str
    request_id: str
    status: Literal["success", "partial"]
    mode: ComparisonMode
    strategy: StrategyId
    prompt: str | None
    duration_ms: int = Field(ge=0)
    sources: list[Source] = Field(min_length=2)
    results: list[Result]
    errors: list[ErrorDetail]
