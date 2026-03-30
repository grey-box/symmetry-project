from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional


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
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    similarity_score: Optional[float] = None  # 0.0–1.0 from SequenceMatcher
    char_delta: int  # characters added minus characters removed
    unified_diff: Optional[List[str]] = None  # output of difflib.unified_diff


class Flag(BaseModel):
    revid: int
    reason: str  # "lead_section_modified", "section_removed", "high_volume_change", "rapid_successive_edits"
    severity: str  # "low", "medium", "high"
    detail: str  # human-readable explanation


class DiffResponse(BaseModel):
    old_revid: int
    new_revid: int
    title: str
    section_diffs: List[SectionDiff]
    total_chars_old: int
    total_chars_new: int
    flags: Optional[List[Flag]] = None
