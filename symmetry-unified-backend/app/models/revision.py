from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Revision(BaseModel):
    revid: int
    parentid: int
    timestamp: str  # ISO 8601, e.g. "2024-01-15T12:34:56Z"
    user: str
    comment: str
    size: int  # article size in bytes at this revision


class SectionDiff(BaseModel):
    section_title: str
    status: str  # "added", "removed", "modified", "unchanged"
    old_content: str | None = None
    new_content: str | None = None
    similarity_score: float | None = None  # 0.0–1.0 from SequenceMatcher
    char_delta: int  # characters added minus characters removed
    unified_diff: list[str] | None = None  # output of difflib.unified_diff


class Flag(BaseModel):
    revid: int
    reason: str  # "lead_section_modified", "section_removed", "high_volume_change", "rapid_successive_edits"
    severity: str  # "low", "medium", "high"
    detail: str  # human-readable explanation


class DiffResponse(BaseModel):
    old_revid: int
    new_revid: int
    title: str
    section_diffs: list[SectionDiff]
    total_chars_old: int
    total_chars_new: int
    flags: list[Flag] | None = None


class SectionChange(BaseModel):
    section_title: str
    old_content: str | None = None
    new_content: str | None = None
    similarity_score: float  # 0.0 for added/removed, 0.0–1.0 for modified


class RevisionDiffResponse(BaseModel):
    revid_a: int
    revid_b: int
    title: str
    lang: str
    sections_added: list[SectionChange]
    sections_removed: list[SectionChange]
    sections_modified: list[SectionChange]
    overall_similarity: float  # 0.0–1.0 across full article text


class LagReport(BaseModel):
    lang: str
    title: str | None = None  # translated title; None if no interlanguage link found
    source_last_updated: datetime | None = None
    target_last_updated: datetime | None = None
    days_behind: float | None = None  # negative means target is ahead of source
    is_lagging: bool
