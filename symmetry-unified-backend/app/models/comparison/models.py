from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Base request models
# ---------------------------------------------------------------------------


class BaseCompareRequest(BaseModel):
    """Base request for text comparison endpoints."""

    original_article_content: str = Field(
        ..., description="Original article text", min_length=1
    )
    translated_article_content: str = Field(
        ..., description="Translated article text", min_length=1
    )


class SemanticCompareRequest(BaseCompareRequest):
    """Request for semantic comparison with configurable model and threshold."""

    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    model_name: str = Field(default="sentence-transformers/LaBSE", max_length=100)


# ---------------------------------------------------------------------------
# Legacy plain-text comparison models
# ---------------------------------------------------------------------------


class CompareRequest(BaseModel):
    """Request to compare two article text blobs using semantic similarity."""

    original_article_content: str
    translated_article_content: str
    original_language: str = Field(default="en")
    translated_language: str = Field(default="fr")
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    model_name: str = "sentence-transformers/LaBSE"


class SentenceDiff(BaseModel):
    """A sentence that differs between two compared articles."""

    sentence: str
    index: int


class ComparisonResult(BaseModel):
    """Raw comparison arrays from the semantic comparison engine."""

    left_article_array: List[str]
    right_article_array: List[str]
    left_article_missing_info_index: List[int]
    right_article_extra_info_index: List[int]
    # Optional free-form details (e.g. per-sentence scores, top match list)
    details: Optional[dict] = None


class CompareResponse(BaseModel):
    """Response for the legacy plain-text article comparison endpoint."""

    missing_info: List[SentenceDiff] = Field(default_factory=list)
    extra_info: List[SentenceDiff] = Field(default_factory=list)
    error_message: Optional[str] = None
    model_name: str = Field(
        default="sentence-transformers/LaBSE",
        description="Name of the model used for comparison",
    )
    similarity_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Similarity threshold used for comparison",
    )
    comparisons: Optional[List[ComparisonResult]] = None


# ---------------------------------------------------------------------------
# Legacy response models (also used by comparison endpoints)
# ---------------------------------------------------------------------------


class MissingInfo(BaseModel):
    sentence: str = Field()
    index: int
    similarity_score: Optional[float] = None


class ExtraInfo(BaseModel):
    sentence: str = Field()
    index: int
    similarity_score: Optional[float] = None


class ArticleComparisonResponse(BaseModel):
    missing_info: List[MissingInfo]
    extra_info: List[ExtraInfo]
    model_name: str = Field(
        default="sentence-transformers/LaBSE",
        description="Name of the model used for comparison",
    )
    similarity_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Similarity threshold used for comparison",
    )


# ---------------------------------------------------------------------------
# Section-level comparison models
# ---------------------------------------------------------------------------


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

