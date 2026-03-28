"""
Pydantic models for section-level article comparison.

These models support the structured diff view that compares Wikipedia articles
component-by-component (section-by-section, paragraph-by-paragraph).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional


class SectionCompareRequest(BaseModel):
    """Request to compare two Wikipedia articles at the section/paragraph level."""

    source_query: str = Field(
        ...,
        description="Wikipedia URL or title for the source article",
    )
    target_query: str = Field(
        ...,
        description="Wikipedia URL or title for the target article",
    )
    source_lang: str = Field(
        default="en",
        description="Language code for the source article (e.g. 'en')",
        max_length=10,
    )
    target_lang: str = Field(
        default="fr",
        description="Language code for the target article (e.g. 'fr')",
        max_length=10,
    )
    similarity_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for matching",
    )
    model_name: str = Field(
        default="sentence-transformers/LaBSE",
        description="Sentence-transformer model for embedding comparison",
    )


class ParagraphDiff(BaseModel):
    """Comparison result for a single paragraph within a matched section."""

    source_text: Optional[str] = Field(
        default=None,
        description="Paragraph text from the source article (None if added in target)",
    )
    target_text: Optional[str] = Field(
        default=None,
        description="Paragraph text from the target article (None if missing from target)",
    )
    similarity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Cosine similarity score between the two paragraphs",
    )
    levenshtein_score: Optional[float] = Field(
        default=None,
        description="Levenshtein similarity (used for disambiguation when semantic scores are close)",
    )
    status: str = Field(
        description="One of: 'matched', 'missing_in_target', 'added_in_target'",
    )


class SectionDiff(BaseModel):
    """Comparison result for a matched pair of sections (or unmatched section)."""

    source_title: Optional[str] = Field(
        default=None,
        description="Section title from source article",
    )
    target_title: Optional[str] = Field(
        default=None,
        description="Section title from target article",
    )
    section_similarity: float = Field(
        default=0.0,
        description="Overall similarity between the two sections",
    )
    status: str = Field(
        description="One of: 'matched', 'missing_in_target', 'added_in_target'",
    )
    paragraph_diffs: List[ParagraphDiff] = Field(
        default_factory=list,
        description="Paragraph-level diffs within this section pair",
    )


class SectionCompareResponse(BaseModel):
    """Full comparison result between two structured Wikipedia articles."""

    source_title: str
    target_title: str
    source_lang: str
    target_lang: str
    source_section_count: int
    target_section_count: int
    matched_section_count: int
    missing_section_count: int = Field(
        description="Sections present in source but not target",
    )
    added_section_count: int = Field(
        description="Sections present in target but not source",
    )
    overall_similarity: float = Field(
        description="Weighted average similarity across matched sections",
    )
    section_diffs: List[SectionDiff] = Field(
        default_factory=list,
    )
    model_name: str = Field(default="sentence-transformers/LaBSE")
    error_message: Optional[str] = None
