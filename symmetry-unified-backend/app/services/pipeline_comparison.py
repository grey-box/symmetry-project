"""Runs the v1 sentence comparison on the generic comparison pipeline.

The v1 compare endpoints (`/articles/compare` and `/comparison/semantic`) used to call
the Wikipedia-focused engine in `app.ai.comparison` directly. This module keeps that
function's name, input and output, but does the work through `ComparisonPipeline` and
the `semantic_similarity` strategy, so v1 and v2 share one comparison path. The
response format of v1 does not change.

Three cases still use the old engine, because the pipeline cannot take them:
the `similarity_prototype` model, and texts that are empty or longer than the
pipeline's input limit (`MAX_TEXT_CHARS`).
"""

import asyncio
import logging
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.ai.comparison import perform_semantic_comparison as _legacy_comparison
from app.ai.comparison import preprocess_input
from app.core.settings import SIMILARITY_THRESHOLD
from app.models.comparison.registry import DEFAULT_MODEL
from app.pipeline import ComparisonPipeline, StrategySpec, TextInput, keep_order

logger = logging.getLogger(__name__)

STRATEGY = "semantic_similarity"

# The desktop app waits up to 10 minutes for a large article, so the pipeline does too.
TIMEOUT_S = 600.0

# How many of the closest sentence pairs v1 reports in details["top_matches"].
TOP_MATCHES = 50


# Runs a coroutine to the end. Normally called from a worker thread, which has no
# event loop; if one is running, the coroutine runs on a thread of its own.
def _run(coro: Coroutine[Any, Any, Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


# Builds one v1 `comparisons` entry from the strategy's details.
def _comparison_entry(score: float, details: dict) -> dict:
    left = details["source_sentence_list"]
    right = details["target_sentence_list"]
    best_ab = [
        {
            "sentence": sentence,
            "best_match": right[match["best_index"]],
            "score": round(match["score"], 4),
        }
        for sentence, match in zip(left, details["best_for_source"], strict=True)
    ]
    best_ba = [
        {
            "sentence": sentence,
            "best_match": left[match["best_index"]],
            "score": round(match["score"], 4),
        }
        for sentence, match in zip(right, details["best_for_target"], strict=True)
    ]
    pairs = sorted(
        (
            {
                "score": round(value, 4),
                "sentence_a": left[i],
                "sentence_b": right[j],
            }
            for i, row in enumerate(details["similarity_matrix"])
            for j, value in enumerate(row)
        ),
        key=lambda pair: pair["score"],
        reverse=True,
    )
    avg_ab = sum(m["score"] for m in best_ab) / len(best_ab)
    avg_ba = sum(m["score"] for m in best_ba) / len(best_ba)
    return {
        "left_article_array": left,
        "right_article_array": right,
        "left_article_missing_info_index": details["source_unmatched"],
        "right_article_extra_info_index": details["target_unmatched"],
        "success": True,
        "score": round((avg_ab + avg_ba) / 2, 4),
        "details": {
            "top_matches": pairs[:TOP_MATCHES],
            "best_matches_ab": best_ab,
            "best_matches_ba": best_ba,
        },
    }


# Same input and output as app.ai.comparison.perform_semantic_comparison: returns
# {"comparisons": [entry]} on success and {"comparisons": []} when nothing could be
# compared.
def perform_semantic_comparison(request_data: dict) -> dict:
    model_name = request_data.get("model_name", DEFAULT_MODEL)
    if model_name == "similarity_prototype":
        return _legacy_comparison(request_data)

    source_language = request_data["original_language"]
    target_language = request_data["translated_language"]
    threshold = request_data.get("comparison_threshold", SIMILARITY_THRESHOLD)
    try:
        source = TextInput(
            text=request_data["original_article_content"],
            language=source_language,
            kind="text",
        )
        target = TextInput(
            text=request_data["translated_article_content"],
            language=target_language,
            kind="text",
        )
    except ValueError:
        # Empty, or longer than the pipeline accepts: keep the old behaviour.
        return _legacy_comparison(request_data)

    spec = StrategySpec(
        STRATEGY,
        config={
            "threshold": threshold,
            "model_name": model_name,
            "source_splitter": lambda text: preprocess_input(text, source_language),
            "target_splitter": lambda text: preprocess_input(text, target_language),
            "include_matrix": True,
        },
        timeout_s=TIMEOUT_S,
    )
    pipeline = ComparisonPipeline(ranker=keep_order)
    try:
        outcome = _run(pipeline.run(source, target, [spec]))
    except Exception:
        logger.exception("pipeline comparison failed")
        return {"comparisons": []}

    if outcome.errors or not outcome.results:
        logger.warning("pipeline comparison returned errors: %s", outcome.errors)
        return {"comparisons": []}
    result = outcome.results[0]
    return {"comparisons": [_comparison_entry(result.score or 0.0, result.details)]}
