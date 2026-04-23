"""Semantic comparison engine using sentence-transformers."""

import logging
import os
import sys
from typing import List, Optional, Tuple

import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.comparison.registry import DEFAULT_MODEL
from app.core.settings import SIMILARITY_THRESHOLD as _DEFAULT_SIMILARITY_THRESHOLD
from app.services.chunking import chunk_text

logger = logging.getLogger(__name__)

# Module-level model cache
_model_cache: dict = {}

# Optional similarity_prototype pipeline
try:
    _sp_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "services", "similarity_prototype"
        )
    )
    if os.path.isdir(_sp_path) and _sp_path not in sys.path:
        sys.path.insert(0, _sp_path)
    from app.services.similarity_prototype.article_comparator import (
        ArticleComparator as _ArticleComparator,
    )
except Exception:
    _ArticleComparator = None  # type: ignore[assignment,misc]

_SPACY_MODEL_MAP = {
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",
    "es": "es_core_news_sm",
    "it": "it_core_news_sm",
    "pt": "pt_core_news_sm",
    "nl": "nl_core_news_sm",
}


def _get_model(model_name: str) -> SentenceTransformer:
    if model_name not in _model_cache:
        logger.info("Loading sentence-transformer model: %s", model_name)
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def universal_sentences_split(text: str) -> List[str]:
    sentences = []
    for sentence in text.replace("!", ".").replace("?", ".").split("."):
        if sentence.strip():
            sentences.append(sentence.strip())
    return sentences


def preprocess_input(article: str, language: str) -> List[str]:
    if not article:
        return []

    cleaned = article.replace("\n\n", " ").replace("\n", ". ").strip()

    if len(cleaned) > 3500:
        out = chunk_text(cleaned, chunk_size=450, overlap=60)
        return [x for x in out if isinstance(x, str) and x.strip()]

    if language in _SPACY_MODEL_MAP:
        try:
            nlp = spacy.load(_SPACY_MODEL_MAP[language])
            doc = nlp(cleaned)
            sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
            if sentences:
                return sentences
        except Exception as exc:
            logger.warning(
                "spaCy model unavailable for %s: %s — falling back", language, exc
            )

    return [s for s in universal_sentences_split(cleaned) if s]


def sentences_diff(
    article_sentences: List[str],
    source_embeddings,
    reference_embeddings,
    similarity_threshold: float,
) -> Tuple[List[str], List[int]]:
    unmatched_sentences: List[str] = []
    unmatched_indices: List[int] = []
    sim_matrix = cosine_similarity(source_embeddings, reference_embeddings)
    for i, similarities in enumerate(sim_matrix):
        if max(similarities) < similarity_threshold:
            unmatched_sentences.append(article_sentences[i])
            unmatched_indices.append(i)
    return unmatched_sentences, unmatched_indices


def semantic_compare(
    original_blob: str,
    translated_blob: str,
    source_language: str,
    target_language: str,
    sim_threshold: Optional[float],
    model_name: str,
) -> dict:
    if not model_name:
        model_name = DEFAULT_MODEL

    try:
        model = _get_model(model_name)
    except Exception as exc:
        logger.error("Error loading model %s: %s", model_name, exc)
        return {
            "original_sentences": [original_blob],
            "translated_sentences": [translated_blob],
            "missing_info": [],
            "extra_info": [],
            "missing_info_indices": [],
            "extra_info_indices": [],
            "success": False,
        }

    try:
        original_sentences = preprocess_input(original_blob, source_language) or []
        translated_sentences = preprocess_input(translated_blob, target_language) or []
    except Exception as exc:
        logger.error("Error preprocessing input: %s", exc)
        original_sentences = [original_blob]
        translated_sentences = [translated_blob]

    if not original_sentences or not translated_sentences:
        return {
            "original_sentences": [],
            "translated_sentences": [],
            "missing_info": [],
            "extra_info": [],
            "missing_info_indices": [],
            "extra_info_indices": [],
            "success": False,
        }

    if sim_threshold is None:
        sim_threshold = _DEFAULT_SIMILARITY_THRESHOLD

    try:
        original_embeddings = model.encode(original_sentences)
        translated_embeddings = model.encode(translated_sentences)
        missing_info, missing_info_indices = sentences_diff(
            original_sentences,
            original_embeddings,
            translated_embeddings,
            sim_threshold,
        )
        extra_info, extra_info_indices = sentences_diff(
            translated_sentences,
            translated_embeddings,
            original_embeddings,
            sim_threshold,
        )
        success = True
    except Exception as exc:
        logger.error("Error during semantic comparison: %s", exc)
        missing_info, extra_info = [], []
        missing_info_indices, extra_info_indices = [], []
        success = False

    return {
        "original_sentences": original_sentences,
        "translated_sentences": translated_sentences,
        "missing_info": missing_info,
        "extra_info": extra_info,
        "missing_info_indices": missing_info_indices,
        "extra_info_indices": extra_info_indices,
        "success": success,
    }


def perform_semantic_comparison(request_data: dict) -> dict:
    source_article = request_data["original_article_content"]
    target_article = request_data["translated_article_content"]
    source_language = request_data["original_language"]
    target_language = request_data["translated_language"]
    sim_threshold = request_data.get(
        "comparison_threshold", _DEFAULT_SIMILARITY_THRESHOLD
    )
    model_name = request_data.get("model_name", DEFAULT_MODEL)

    if model_name == "similarity_prototype" and _ArticleComparator is not None:
        return _run_prototype_comparison(
            source_article,
            target_article,
            source_language,
            target_language,
            sim_threshold,
        )

    left = preprocess_input(source_article, source_language) or []
    right = preprocess_input(target_article, target_language) or []

    if not left or not right:
        return {"comparisons": []}

    try:
        model = _get_model(model_name)
        left_emb = model.encode(left)
        right_emb = model.encode(right)
        sim_matrix = cosine_similarity(left_emb, right_emb)

        _, missing_idx = sentences_diff(left, left_emb, right_emb, sim_threshold)
        _, extra_idx = sentences_diff(right, right_emb, left_emb, sim_threshold)

        pairs = sorted(
            [
                {
                    "score": float(round(float(sim_matrix[i][j]), 4)),
                    "sentence_a": left[i],
                    "sentence_b": right[j],
                }
                for i in range(len(left))
                for j in range(len(right))
            ],
            key=lambda x: x["score"],
            reverse=True,
        )
        best_ab = [
            {
                "sentence": s,
                "best_match": right[int(sim_matrix[i].argmax())],
                "score": float(round(float(sim_matrix[i].max()), 4)),
            }
            for i, s in enumerate(left)
        ]
        best_ba = [
            {
                "sentence": s,
                "best_match": left[int(sim_matrix[:, j].argmax())],
                "score": float(round(float(sim_matrix[:, j].max()), 4)),
            }
            for j, s in enumerate(right)
        ]
        avg_ab = sum(b["score"] for b in best_ab) / len(best_ab) if best_ab else 0.0
        avg_ba = sum(b["score"] for b in best_ba) / len(best_ba) if best_ba else 0.0

        return {
            "comparisons": [
                {
                    "left_article_array": left,
                    "right_article_array": right,
                    "left_article_missing_info_index": missing_idx,
                    "right_article_extra_info_index": extra_idx,
                    "success": True,
                    "score": round((avg_ab + avg_ba) / 2, 4),
                    "details": {
                        "top_matches": pairs[:50],
                        "best_matches_ab": best_ab,
                        "best_matches_ba": best_ba,
                    },
                }
            ]
        }
    except Exception as exc:
        logger.exception("Transformer comparison failed: %s", exc)
        return {"comparisons": []}


def _run_prototype_comparison(
    source_article: str,
    target_article: str,
    source_language: str,
    target_language: str,
    sim_threshold: float,
) -> dict:
    try:
        from app.ai.translation import translate

        if source_language != "en":
            source_article = translate(source_article, source_language, "en")
        if target_language != "en":
            target_article = translate(target_article, target_language, "en")

        comparator = _ArticleComparator()
        left_raw = preprocess_input(source_article, "en") or []
        right_raw = preprocess_input(target_article, "en") or []
        left = [
            s
            for s in (comparator.clean_sentence(s) for s in left_raw)
            if comparator.is_valid_sentence(s)
        ]
        right = [
            s
            for s in (comparator.clean_sentence(s) for s in right_raw)
            if comparator.is_valid_sentence(s)
        ]

        if not left or not right:
            return {"comparisons": []}

        matrix = comparator.build_score_matrix(left, right)
        ab_scores = comparator.best_match_scores(matrix, direction="AB")
        ba_scores = comparator.best_match_scores(matrix, direction="BA")
        avg_ab = sum(ab_scores) / len(ab_scores) if ab_scores else 0.0
        avg_ba = sum(ba_scores) / len(ba_scores) if ba_scores else 0.0

        pairs = sorted(
            [
                {"score": matrix[i][j], "sentence_a": left[i], "sentence_b": right[j]}
                for i in range(len(left))
                for j in range(len(right))
            ],
            key=lambda x: x["score"],
            reverse=True,
        )
        best_ab = []
        for i, s in enumerate(left):
            best_j = max(range(len(right)), key=lambda j: matrix[i][j])
            best_ab.append({
                "sentence": s,
                "best_match": right[best_j],
                "score": matrix[i][best_j],
            })
        best_ba = [
            {
                "sentence": s,
                "best_match": left[max(range(len(left)), key=lambda i: matrix[i][j])],
                "score": matrix[max(range(len(left)), key=lambda i: matrix[i][j])][j],
            }
            for j, s in enumerate(right)
        ]

        return {
            "comparisons": [
                {
                    "left_article_array": left,
                    "right_article_array": right,
                    "left_article_missing_info_index": [
                        i for i, sc in enumerate(ab_scores) if sc < sim_threshold
                    ],
                    "right_article_extra_info_index": [
                        i for i, sc in enumerate(ba_scores) if sc < sim_threshold
                    ],
                    "success": True,
                    "score": round((avg_ab + avg_ba) / 2, 4),
                    "details": {
                        "top_matches": pairs[:20],
                        "best_matches_ab": best_ab,
                        "best_matches_ba": best_ba,
                    },
                }
            ]
        }
    except Exception as exc:
        logger.exception("similarity_prototype comparison failed: %s", exc)
        return {"comparisons": []}
