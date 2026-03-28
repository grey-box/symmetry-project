"""
Section-level article comparison service.

Compares two structured Wikipedia articles component-by-component:
1. Match sections across the two articles using semantic similarity of titles + content.
2. Within matched sections, compare paragraphs (sentences / chunks) pairwise.
3. Use Levenshtein distance for disambiguation when semantic similarity scores are close.

This provides a structured diff showing which sections/paragraphs correspond,
which are missing, and which are added.
"""

import logging
import re
from typing import List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.wiki_structure import Article, Section
from app.models.section_comparison import (
    ParagraphDiff,
    SectionDiff,
    SectionCompareResponse,
)
from app.services.similarity_scoring import normalized_levenshtein_distance

logger = logging.getLogger(__name__)

# Reusable model cache (shared with semantic_comparison.py pattern)
_model_cache: dict = {}

# When two paragraph embeddings have similarity scores within this margin,
# Levenshtein distance is used as a tiebreaker for matching.
LEVENSHTEIN_DISAMBIGUATION_MARGIN = 0.08 # Consider moving to a central config or making configurable


def _get_model(model_name: str) -> SentenceTransformer:
    """Load a SentenceTransformer model with caching."""
    if model_name not in _model_cache:
        logger.info("Loading sentence-transformer model: %s", model_name)
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def _split_into_paragraphs(section: Section) -> List[str]:
    """
    Split a section's clean_content into paragraph-sized chunks.

    Wikipedia sections parsed by article_fetcher concatenate <p> tags with
    spaces.  We split on double-newline boundaries first; if that produces
    only one chunk we fall back to sentence-level splitting (period + space).
    """
    text = section.clean_content.strip()
    if not text:
        return []

    # Try splitting on double-newline (paragraph boundaries preserved from HTML)
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

    if len(paragraphs) <= 1 and len(text) > 300:
        # Fallback: split on sentence boundaries for long single-paragraph sections
        sentences = re.split(r"(?<=[.!?])\s+", text)
        # Group sentences into ~150-word chunks
        chunks: List[str] = []
        current: List[str] = []
        word_count = 0
        for sentence in sentences:
            words = len(sentence.split())
            if word_count + words > 150 and current:
                chunks.append(" ".join(current))
                current = [sentence]
                word_count = words
            else:
                current.append(sentence)
                word_count += words
        if current:
            chunks.append(" ".join(current))
        return [c for c in chunks if c.strip()]

    return paragraphs


def _match_sections(
    source_sections: List[Section],
    target_sections: List[Section],
    model: SentenceTransformer,
    threshold: float,
) -> Tuple[
    List[Tuple[int, int, float]],  # matched pairs (source_idx, target_idx, score)
    List[int],  # unmatched source indices
    List[int],  # unmatched target indices
]:
    """
    Match sections between source and target articles using title + content embeddings.

    Uses a greedy best-match approach: encode section titles concatenated with a
    content preview (first 200 chars), compute the full cosine similarity matrix,
    then greedily assign the best remaining match above threshold.
    """
    if not source_sections or not target_sections:
        return (
            [],
            list(range(len(source_sections))),
            list(range(len(target_sections))),
        )

    def section_text(s: Section) -> str:
        preview = s.clean_content[:200] if s.clean_content else ""
        return f"{s.title}. {preview}"

    source_texts = [section_text(s) for s in source_sections]
    target_texts = [section_text(s) for s in target_sections]

    source_embeddings = model.encode(source_texts)
    target_embeddings = model.encode(target_texts)

    sim_matrix = cosine_similarity(source_embeddings, target_embeddings)

    matched_pairs: List[Tuple[int, int, float]] = []
    used_source: set = set()
    used_target: set = set()

    # Greedy assignment: pick best pair, mark used, repeat
    flat_indices = np.argsort(sim_matrix, axis=None)[::-1]
    for flat_idx in flat_indices:
        src_idx = int(flat_idx // sim_matrix.shape[1])
        tgt_idx = int(flat_idx % sim_matrix.shape[1])
        score = float(sim_matrix[src_idx, tgt_idx])

        if score < threshold:
            break
        if src_idx in used_source or tgt_idx in used_target:
            continue

        matched_pairs.append((src_idx, tgt_idx, score))
        used_source.add(src_idx)
        used_target.add(tgt_idx)

    unmatched_source = [i for i in range(len(source_sections)) if i not in used_source]
    unmatched_target = [i for i in range(len(target_sections)) if i not in used_target]

    return matched_pairs, unmatched_source, unmatched_target


def _compare_paragraphs(
    source_paragraphs: List[str],
    target_paragraphs: List[str],
    model: SentenceTransformer,
    threshold: float,
) -> List[ParagraphDiff]:
    """
    Compare paragraphs within a matched section pair.

    Uses cosine similarity for primary matching and Levenshtein distance for
    disambiguation when two candidates are within LEVENSHTEIN_DISAMBIGUATION_MARGIN.
    """
    if not source_paragraphs and not target_paragraphs:
        return []

    if not source_paragraphs:
        return [
            ParagraphDiff(
                target_text=p,
                similarity_score=0.0,
                status="added_in_target",
            )
            for p in target_paragraphs
        ]

    if not target_paragraphs:
        return [
            ParagraphDiff(
                source_text=p,
                similarity_score=0.0,
                status="missing_in_target",
            )
            for p in source_paragraphs
        ]

    source_embeddings = model.encode(source_paragraphs)
    target_embeddings = model.encode(target_paragraphs)

    sim_matrix = cosine_similarity(source_embeddings, target_embeddings)

    diffs: List[ParagraphDiff] = []
    used_target: set = set()

    # For each source paragraph, find best matching target paragraph
    for src_idx in range(len(source_paragraphs)):
        row = sim_matrix[src_idx]

        # Find top-2 candidates for Levenshtein disambiguation
        candidate_indices = [
            j for j in range(len(target_paragraphs)) if j not in used_target
        ]
        if not candidate_indices:
            diffs.append(
                ParagraphDiff(
                    source_text=source_paragraphs[src_idx],
                    similarity_score=0.0,
                    status="missing_in_target",
                )
            )
            continue

        # Sort candidates by cosine similarity descending
        candidates = sorted(candidate_indices, key=lambda j: row[j], reverse=True)
        best_idx = candidates[0]
        best_score = float(row[best_idx])

        levenshtein = None

        # Disambiguation: if top-2 are within margin, use Levenshtein as tiebreaker
        if len(candidates) >= 2:
            second_idx = candidates[1]
            second_score = float(row[second_idx])

            if best_score - second_score < LEVENSHTEIN_DISAMBIGUATION_MARGIN:
                lev_best = normalized_levenshtein_distance(
                    source_paragraphs[src_idx], target_paragraphs[best_idx]
                )
                lev_second = normalized_levenshtein_distance(
                    source_paragraphs[src_idx], target_paragraphs[second_idx]
                )

                if lev_second > lev_best:
                    best_idx = second_idx
                    best_score = second_score
                    levenshtein = lev_second
                else:
                    levenshtein = lev_best

        if best_score >= threshold:
            used_target.add(best_idx)
            diffs.append(
                ParagraphDiff(
                    source_text=source_paragraphs[src_idx],
                    target_text=target_paragraphs[best_idx],
                    similarity_score=round(best_score, 4),
                    levenshtein_score=round(levenshtein, 4)
                    if levenshtein is not None
                    else None,
                    status="matched",
                )
            )
        else:
            diffs.append(
                ParagraphDiff(
                    source_text=source_paragraphs[src_idx],
                    similarity_score=round(best_score, 4),
                    levenshtein_score=round(levenshtein, 4)
                    if levenshtein is not None
                    else None,
                    status="missing_in_target",
                )
            )

    # Remaining target paragraphs that were not matched
    for tgt_idx in range(len(target_paragraphs)):
        if tgt_idx not in used_target:
            diffs.append(
                ParagraphDiff(
                    target_text=target_paragraphs[tgt_idx],
                    similarity_score=0.0,
                    status="added_in_target",
                )
            )

    return diffs


def compare_article_sections(
    source_article: Article,
    target_article: Article,
    similarity_threshold: float = 0.65,
    model_name: str = "sentence-transformers/LaBSE",
) -> SectionCompareResponse:
    """
    Compare two structured Wikipedia articles at the section and paragraph level.

    Args:
        source_article: Parsed source language article.
        target_article: Parsed target language article.
        similarity_threshold: Cosine similarity threshold for matching.
        model_name: Sentence-transformer model name.

    Returns:
        SectionCompareResponse with full structured diff.
    """
    try:
        model = _get_model(model_name)
    except Exception as e:
        logger.error("Failed to load model %s: %s", model_name, e)
        return SectionCompareResponse(
            source_title=source_article.title,
            target_title=target_article.title,
            source_lang=source_article.lang,
            target_lang=target_article.lang,
            source_section_count=len(source_article.sections),
            target_section_count=len(target_article.sections),
            matched_section_count=0,
            missing_section_count=len(source_article.sections),
            added_section_count=len(target_article.sections),
            overall_similarity=0.0,
            section_diffs=[],
            model_name=model_name,
            error_message=f"Failed to load model: {e}",
        )

    # 1. Match sections across articles
    matched_pairs, unmatched_source, unmatched_target = _match_sections(
        source_article.sections,
        target_article.sections,
        model,
        similarity_threshold,
    )

    section_diffs: List[SectionDiff] = []
    similarity_sum = 0.0

    # 2. For matched section pairs, compare paragraphs
    for src_idx, tgt_idx, section_score in matched_pairs:
        source_section = source_article.sections[src_idx]
        target_section = target_article.sections[tgt_idx]

        source_paragraphs = _split_into_paragraphs(source_section)
        target_paragraphs = _split_into_paragraphs(target_section)

        paragraph_diffs = _compare_paragraphs(
            source_paragraphs,
            target_paragraphs,
            model,
            similarity_threshold,
        )

        section_diffs.append(
            SectionDiff(
                source_title=source_section.title,
                target_title=target_section.title,
                section_similarity=round(section_score, 4),
                status="matched",
                paragraph_diffs=paragraph_diffs,
            )
        )
        similarity_sum += section_score

    # 3. Add unmatched source sections (missing in target)
    for src_idx in unmatched_source:
        source_section = source_article.sections[src_idx]
        source_paragraphs = _split_into_paragraphs(source_section)

        section_diffs.append(
            SectionDiff(
                source_title=source_section.title,
                section_similarity=0.0,
                status="missing_in_target",
                paragraph_diffs=[
                    ParagraphDiff(
                        source_text=p,
                        similarity_score=0.0,
                        status="missing_in_target",
                    )
                    for p in source_paragraphs
                ],
            )
        )

    # 4. Add unmatched target sections (added in target)
    for tgt_idx in unmatched_target:
        target_section = target_article.sections[tgt_idx]
        target_paragraphs = _split_into_paragraphs(target_section)

        section_diffs.append(
            SectionDiff(
                target_title=target_section.title,
                section_similarity=0.0,
                status="added_in_target",
                paragraph_diffs=[
                    ParagraphDiff(
                        target_text=p,
                        similarity_score=0.0,
                        status="added_in_target",
                    )
                    for p in target_paragraphs
                ],
            )
        )

    total_sections = len(matched_pairs) + len(unmatched_source) + len(unmatched_target)
    overall_similarity = similarity_sum / len(matched_pairs) if matched_pairs else 0.0

    return SectionCompareResponse(
        source_title=source_article.title,
        target_title=target_article.title,
        source_lang=source_article.lang,
        target_lang=target_article.lang,
        source_section_count=len(source_article.sections),
        target_section_count=len(target_article.sections),
        matched_section_count=len(matched_pairs),
        missing_section_count=len(unmatched_source),
        added_section_count=len(unmatched_target),
        overall_similarity=round(overall_similarity, 4),
        section_diffs=section_diffs,
        model_name=model_name,
    )
