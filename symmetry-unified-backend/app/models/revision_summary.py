"""
Request and response models for the AI revision summary.

The AI agent gets the evidence from the LaBSE paragraph comparison and the
Wikidata entity lookup for two revisions and writes a structured summary of
what changed.  The summary fields are kept simple (strings, lists, fixed
choices) so every provider can return them as JSON.
"""

from typing import Literal

from pydantic import BaseModel, Field

Provider = Literal["anthropic", "openai", "gemini", "groq", "openrouter", "custom"]
Significance = Literal["low", "medium", "high"]


class RevisionSummaryRequest(BaseModel):
    old_revid: int = Field(..., description="Older revision ID")
    new_revid: int = Field(..., description="Newer revision ID")
    title: str = Field(..., description="Article title")
    lang: str = Field("en", description="Language code of the article")
    provider: Provider = Field("anthropic", description="Which AI provider to call")
    model: str | None = Field(
        None, description="Model name; the provider's default is used when empty"
    )
    base_url: str | None = Field(
        None,
        description=(
            "OpenAI-compatible endpoint, only used when provider is 'custom' "
            "(for example http://localhost:11434/v1 for Ollama)"
        ),
    )


# ---------------------------------------------------------------------------
# What the AI agent returns
# ---------------------------------------------------------------------------


class KeyChange(BaseModel):
    section: str
    change_type: Literal[
        "added",
        "removed",
        "reworded",
        "expanded",
        "condensed",
        "moved",
        "recontextualized",
    ]
    description: str
    significance: Significance
    old_excerpt: str = ""
    new_excerpt: str = ""


class SemanticShift(BaseModel):
    topic: str
    before: str
    after: str
    why_it_matters: str


class Concern(BaseModel):
    severity: Significance
    category: Literal[
        "removed_content",
        "removed_sources",
        "neutrality",
        "unsupported_claim",
        "factual_change",
        "recontextualization",
        "possible_vandalism",
        "other",
    ]
    section: str
    explanation: str
    evidence: str = ""


class EntityChange(BaseModel):
    entity: str
    wikidata_id: str = ""
    change: Literal["added", "removed", "relinked"]
    note: str = ""


class AiRevisionSummary(BaseModel):
    headline: str
    overall_impact: Literal["minor", "moderate", "substantial"]
    overview: str
    key_changes: list[KeyChange] = Field(default_factory=list)
    semantic_shifts: list[SemanticShift] = Field(default_factory=list)
    concerns: list[Concern] = Field(default_factory=list)
    entity_changes: list[EntityChange] = Field(default_factory=list)
    things_to_verify: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoint response
# ---------------------------------------------------------------------------


class EvidenceStats(BaseModel):
    """How much comparison evidence was sent to the agent."""

    sections_added: int
    sections_removed: int
    paragraphs_modified: int
    paragraphs_added: int
    paragraphs_removed: int
    entities_added: int
    entities_removed: int
    edits_between: int
    changes_left_out: int = Field(
        0, description="Changes left out of the prompt to keep it a reasonable size"
    )


class RevisionSummaryResponse(BaseModel):
    title: str
    lang: str
    old_revid: int
    new_revid: int
    provider: str
    model: str
    summary: AiRevisionSummary
    evidence_stats: EvidenceStats
    input_tokens: int | None = None
    output_tokens: int | None = None
