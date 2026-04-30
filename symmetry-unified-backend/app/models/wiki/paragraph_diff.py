"""Pydantic models for paragraph-level semantic diff responses."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WordToken(BaseModel):
    """A single token in a word-level diff.

    ``type`` is one of:
    - ``"equal"``    — token is the same in both texts (``text`` is set)
    - ``"replace"``  — token was changed (``old`` and ``new`` are set)
    - ``"insert"``   — token was added in target (``text`` is set)
    - ``"delete"``   — token was removed from source (``text`` is set)
    """

    type: Literal["equal", "replace", "insert", "delete"] = Field()
    text: Optional[str] = Field(default=None)
    old: Optional[str] = Field(default=None)
    new: Optional[str] = Field(default=None)


class AlignedSentencePair(BaseModel):
    """A source sentence aligned to its closest target sentence."""

    source_sentence: str = Field()
    target_sentence: str = Field()
    similarity: float = Field(ge=0.0, le=1.0)
    word_diff: List[WordToken] = Field(default_factory=list)


class ParagraphDiffSection(BaseModel):
    """A pair of matched sections with sentence-level alignment."""

    source_title: str = Field()
    target_title: str = Field()
    similarity: float = Field(ge=0.0, le=1.0)
    aligned_pairs: List[AlignedSentencePair] = Field(default_factory=list)


class ParagraphDiffResponse(BaseModel):
    """Top-level response for the paragraph-diff endpoint."""

    source_title: str = Field()
    target_title: str = Field()
    source_lang: str = Field()
    target_lang: str = Field()
    sections: List[ParagraphDiffSection] = Field(default_factory=list)
