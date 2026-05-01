"""Paragraph-level diff service.

Provides two core utilities:
- ``word_diff``: token-level diff between two strings using difflib.SequenceMatcher
- ``align_paragraphs``: semantically align source/target sentence lists using LaBSE embeddings
"""

from __future__ import annotations

import difflib
import logging
import re
from typing import List, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.models.wiki.paragraph_diff import (
    AlignedSentencePair,
    ParagraphDiffSection,
    WordToken,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Word-level diff
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> List[str]:
    """Split text into word + punctuation tokens preserving whitespace markers."""
    return re.findall(r"\S+|\s+", text)


def word_diff(text_a: str, text_b: str) -> List[WordToken]:
    """Return a list of :class:`WordToken` objects describing the diff.

    Each token has:
    - ``type``: ``"equal"`` | ``"replace"`` | ``"insert"`` | ``"delete"``
    - ``text``: present for ``"equal"`` / ``"insert"`` / ``"delete"``
    - ``old`` / ``new``: present for ``"replace"``
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    matcher = difflib.SequenceMatcher(None, tokens_a, tokens_b, autojunk=False)
    result: List[WordToken] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        chunk_a = "".join(tokens_a[i1:i2])
        chunk_b = "".join(tokens_b[j1:j2])

        if tag == "equal":
            if chunk_a.strip():
                result.append(WordToken(type="equal", text=chunk_a))
        elif tag == "replace":
            # Only emit non-whitespace replacements
            a_stripped = chunk_a.strip()
            b_stripped = chunk_b.strip()
            if a_stripped and b_stripped:
                result.append(WordToken(type="replace", old=a_stripped, new=b_stripped))
            elif a_stripped:
                result.append(WordToken(type="delete", text=a_stripped))
            elif b_stripped:
                result.append(WordToken(type="insert", text=b_stripped))
        elif tag == "delete":
            if chunk_a.strip():
                result.append(WordToken(type="delete", text=chunk_a.strip()))
        elif tag == "insert":
            if chunk_b.strip():
                result.append(WordToken(type="insert", text=chunk_b.strip()))

    return result


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> List[str]:
    """Lightweight sentence splitter — avoids spaCy dependency in this module."""
    # Normalize newlines then split on terminal punctuation
    text = text.replace("\n", " ").strip()
    raw = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw if s.strip()]


# ---------------------------------------------------------------------------
# Paragraph / sentence alignment
# ---------------------------------------------------------------------------


def align_paragraphs(
    source_sentences: List[str],
    target_sentences: List[str],
    model,  # SentenceTransformer instance
    threshold: float = 0.5,
) -> List[AlignedSentencePair]:
    """Align source sentences to the best-matching target sentence.

    Uses greedy one-to-one matching: each target sentence is consumed at most
    once. Pairs below ``threshold`` are not included.

    Returns a list of :class:`AlignedSentencePair` with word-level diffs.
    """
    if not source_sentences or not target_sentences:
        return []

    try:
        src_emb = model.encode(source_sentences, show_progress_bar=False)
        tgt_emb = model.encode(target_sentences, show_progress_bar=False)
    except Exception as exc:
        logger.error("Embedding failed in align_paragraphs: %s", exc)
        return []

    sim_matrix: np.ndarray = cosine_similarity(src_emb, tgt_emb)

    used_target: set = set()
    pairs: List[AlignedSentencePair] = []

    for src_idx, src_sent in enumerate(source_sentences):
        row = sim_matrix[src_idx].copy()
        # Mask already-used targets
        for ti in used_target:
            row[ti] = -1.0

        best_tgt_idx = int(np.argmax(row))
        best_score = float(row[best_tgt_idx])

        if best_score < threshold:
            continue

        tgt_sent = target_sentences[best_tgt_idx]
        used_target.add(best_tgt_idx)

        diff = word_diff(src_sent, tgt_sent)
        pairs.append(
            AlignedSentencePair(
                source_sentence=src_sent,
                target_sentence=tgt_sent,
                similarity=round(best_score, 4),
                word_diff=diff,
            )
        )

    return pairs


# ---------------------------------------------------------------------------
# Section-level diff
# ---------------------------------------------------------------------------


def diff_sections(
    source_sections: List[Tuple[str, str]],  # (title, clean_content)
    target_sections: List[Tuple[str, str]],
    model,
    threshold: float = 0.5,
) -> List[ParagraphDiffSection]:
    """Match source sections to target sections and produce per-section diffs.

    Section matching is done semantically (greedy on section title + intro
    sentence cosine similarity). For matched sections the sentences are aligned
    and word-diffed.

    Args:
        source_sections: list of (title, clean_content) tuples from the source article.
        target_sections: list of (title, clean_content) tuples from the target article.
        model: loaded SentenceTransformer instance.
        threshold: minimum cosine similarity to consider sections a match.

    Returns:
        List of :class:`ParagraphDiffSection` for each matched pair.
    """
    if not source_sections or not target_sections:
        return []

    # Encode section titles for matching
    src_titles = [t for t, _ in source_sections]
    tgt_titles = [t for t, _ in target_sections]

    try:
        src_title_emb = model.encode(src_titles, show_progress_bar=False)
        tgt_title_emb = model.encode(tgt_titles, show_progress_bar=False)
    except Exception as exc:
        logger.error("Section title embedding failed: %s", exc)
        return []

    title_sim: np.ndarray = cosine_similarity(src_title_emb, tgt_title_emb)

    used_target: set = set()
    result: List[ParagraphDiffSection] = []

    for src_idx, (src_title, src_content) in enumerate(source_sections):
        row = title_sim[src_idx].copy()
        for ti in used_target:
            row[ti] = -1.0

        best_tgt_idx = int(np.argmax(row))
        best_score = float(row[best_tgt_idx])

        if best_score < threshold:
            continue

        tgt_title, tgt_content = target_sections[best_tgt_idx]
        used_target.add(best_tgt_idx)

        src_sentences = _split_sentences(src_content)
        tgt_sentences = _split_sentences(tgt_content)

        aligned = align_paragraphs(
            src_sentences, tgt_sentences, model, threshold=threshold
        )

        # Overall section similarity = average of aligned pair similarities
        section_sim = (
            round(float(np.mean([p.similarity for p in aligned])), 4)
            if aligned
            else round(best_score, 4)
        )

        result.append(
            ParagraphDiffSection(
                source_title=src_title,
                target_title=tgt_title,
                similarity=section_sim,
                aligned_pairs=aligned,
            )
        )

    return result
