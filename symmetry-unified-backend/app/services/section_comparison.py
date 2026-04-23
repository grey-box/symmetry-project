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
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.settings import LEVENSHTEIN_DISAMBIGUATION_MARGIN, SIMILARITY_THRESHOLD
from app.models.wiki.structure import Article, Section
from app.models.comparison.models import (
    ParagraphDiff,
    SectionDiff,
    SectionCompareResponse,
)
from app.services.similarity_scoring import normalized_levenshtein_distance

logger = logging.getLogger(__name__)

# Reusable model cache (shared with semantic_comparison.py pattern)
_model_cache: dict = {}

# When the prototype is selected, section *structure* matching still uses a
# multilingual transformer (LaBSE) because the prototype's NLP tools are
# English-only.  Paragraph *content* scoring then uses the prototype after
# translating both sides to English.
_PROTOTYPE_SECTION_MODEL = "sentence-transformers/LaBSE"

try:
    _sp_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "similarity_prototype")
    )
    if os.path.isdir(_sp_path) and _sp_path not in sys.path:
        sys.path.insert(0, _sp_path)
    from app.services.similarity_prototype.article_comparator import (
        ArticleComparator as _ArticleComparator,
    )
except Exception:
    _ArticleComparator = None  # type: ignore[assignment,misc]

_comparator_instance: Optional[Any] = None


def _get_comparator() -> Optional[Any]:
    """Get or create a cached ArticleComparator instance."""
    global _comparator_instance
    if _ArticleComparator is None:
        return None
    if _comparator_instance is None:
        _comparator_instance = _ArticleComparator()
    return _comparator_instance


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


def _compare_paragraphs_prototype(
    source_paragraphs: List[str],
    target_paragraphs: List[str],
    source_lang: str,
    target_lang: str,
    comparator: Any,
    threshold: float = None,
) -> List[ParagraphDiff]:
    """
    Compare paragraphs using the similarity prototype (Phase 1+2+3 pipeline).

    Both sides are translated to English automatically when their language is
    not English, because the prototype's NLP tools (TF-IDF vocabulary, WordNet,
    spaCy en_core_web_sm) are English-only.  Original text is preserved in the
    returned ParagraphDiff objects so the UI displays the source language content.

    Matching follows the same greedy best-match strategy as _compare_paragraphs(),
    using the prototype's MIN_MATCH_THRESHOLD instead of the LaBSE threshold.
    """
    from app.ai.translation import translate

    if not source_paragraphs and not target_paragraphs:
        return []

    if not source_paragraphs:
        return [
            ParagraphDiff(target_text=p, similarity_score=0.0, status="added_in_target")
            for p in target_paragraphs
        ]
    if not target_paragraphs:
        return [
            ParagraphDiff(
                source_text=p, similarity_score=0.0, status="missing_in_target"
            )
            for p in source_paragraphs
        ]

    # Translate to English for prototype's English-only NLP tools.
    # Run both sides concurrently to avoid serialising two slow MarianMT passes.
    def _translate_batch(paragraphs: List[str], src: str) -> List[str]:
        if src == "en":
            return list(paragraphs)
        with ThreadPoolExecutor() as executor:
            return list(executor.map(lambda p: translate(p, src, "en"), paragraphs))

    with ThreadPoolExecutor(max_workers=2) as pool:
        src_future = pool.submit(_translate_batch, source_paragraphs, source_lang)
        tgt_future = pool.submit(_translate_batch, target_paragraphs, target_lang)
        source_en = src_future.result()
        target_en = tgt_future.result()

    # Clean but keep index mapping to originals for display
    left_clean = [comparator.clean_sentence(p) for p in source_en]
    right_clean = [comparator.clean_sentence(p) for p in target_en]

    valid_left = [
        (i, p) for i, p in enumerate(left_clean) if comparator.is_valid_sentence(p)
    ]
    valid_right = [
        (j, p) for j, p in enumerate(right_clean) if comparator.is_valid_sentence(p)
    ]

    # If nothing passes validation fall back to all-missing / all-added
    if not valid_left or not valid_right:
        diffs: List[ParagraphDiff] = [
            ParagraphDiff(
                source_text=source_paragraphs[i],
                similarity_score=0.0,
                status="missing_in_target",
            )
            for i in range(len(source_paragraphs))
        ]
        diffs += [
            ParagraphDiff(
                target_text=target_paragraphs[j],
                similarity_score=0.0,
                status="added_in_target",
            )
            for j in range(len(target_paragraphs))
        ]
        return diffs

    left_orig_indices, left_texts = zip(*valid_left)
    right_orig_indices, right_texts = zip(*valid_right)
    left_orig_indices = list(left_orig_indices)
    right_orig_indices = list(right_orig_indices)

    matrix = comparator.build_score_matrix(list(left_texts), list(right_texts))
    # Use the caller-supplied threshold so the UI control takes effect.
    # Fall back to the prototype's own minimum if none was provided.
    threshold = threshold if threshold is not None else comparator.MIN_MATCH_THRESHOLD

    diffs = []
    used_right: set = set()

    for li, src_orig_idx in enumerate(left_orig_indices):
        row = matrix[li]
        candidates = [rj for rj in range(len(right_orig_indices)) if rj not in used_right]

        if not candidates:
            diffs.append(
                ParagraphDiff(
                    source_text=source_paragraphs[src_orig_idx],
                    similarity_score=0.0,
                    status="missing_in_target",
                )
            )
            continue

        best_rj = max(candidates, key=lambda rj: row[rj])
        best_score = float(row[best_rj])
        tgt_orig_idx = right_orig_indices[best_rj]

        if best_score >= threshold:
            used_right.add(best_rj)
            diffs.append(
                ParagraphDiff(
                    source_text=source_paragraphs[src_orig_idx],
                    target_text=target_paragraphs[tgt_orig_idx],
                    similarity_score=round(best_score, 4),
                    status="matched",
                )
            )
        else:
            diffs.append(
                ParagraphDiff(
                    source_text=source_paragraphs[src_orig_idx],
                    similarity_score=round(best_score, 4),
                    status="missing_in_target",
                )
            )

    # Unmatched target paragraphs
    for rj in range(len(right_orig_indices)):
        if rj not in used_right:
            tgt_orig_idx = right_orig_indices[rj]
            diffs.append(
                ParagraphDiff(
                    target_text=target_paragraphs[tgt_orig_idx],
                    similarity_score=0.0,
                    status="added_in_target",
                )
            )

    return diffs


def compare_article_sections(
    source_article: Article,
    target_article: Article,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    model_name: str = "sentence-transformers/LaBSE",
) -> SectionCompareResponse:
    """
    Compare two structured Wikipedia articles at the section and paragraph level.

    Args:
        source_article: Parsed source language article.
        target_article: Parsed target language article.
        similarity_threshold: Cosine similarity threshold for matching.
        model_name: Sentence-transformer model name.  Pass "similarity_prototype"
            to use the Phase 1/2/3 prototype for paragraph scoring; section
            structure matching will still use LaBSE (multilingual).

    Returns:
        SectionCompareResponse with full structured diff.
    """
    use_prototype = model_name == "similarity_prototype"
    comparator = _get_comparator() if use_prototype else None

    # Section structure matching always uses a multilingual transformer.
    # The prototype's NLP tools are English-only, so we fall back to LaBSE
    # for the title/content embedding step regardless of the chosen model.
    section_model_name = _PROTOTYPE_SECTION_MODEL if use_prototype else model_name

    try:
        model = _get_model(section_model_name)
    except Exception as e:
        logger.error("Failed to load model %s: %s", section_model_name, e)
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

        if use_prototype and comparator is not None:
            paragraph_diffs = _compare_paragraphs_prototype(
                source_paragraphs,
                target_paragraphs,
                source_article.lang,
                target_article.lang,
                comparator,
                threshold=similarity_threshold,
            )
        else:
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
