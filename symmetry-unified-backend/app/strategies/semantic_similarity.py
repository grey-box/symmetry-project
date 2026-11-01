import asyncio
from collections.abc import Callable
from typing import Any

import numpy as np

from app.core.settings import SIMILARITY_THRESHOLD

from .base import ComparisonStrategy, Finding, StrategyInput, StrategyResult
from .errors import (
    StrategyConfigError,
    StrategyError,
    StrategyExecutionError,
    StrategyInputError,
)
from .registry import register_strategy
from .text import split_sentences


# Loads the embedding model the v1 comparison uses, so it is loaded once per process
# and shared with the v1 endpoints. The heavy imports happen here, not at import time.
def _load_default_embedder(model_name: str | None) -> tuple[Any, str]:
    try:
        from app.ai.comparison import _get_model
        from app.models.comparison.registry import DEFAULT_MODEL
    except ModuleNotFoundError as exc:
        raise StrategyExecutionError(
            f"embedding model support is not installed: {exc.name}",
            strategy="semantic_similarity",
        ) from exc
    name = model_name or DEFAULT_MODEL
    try:
        return _get_model(name), name
    except Exception as exc:
        raise StrategyExecutionError(
            f"could not load embedding model {name!r}: {type(exc).__name__}",
            strategy="semantic_similarity",
        ) from exc


# Scores how close two texts are in meaning. Each sentence is matched to its closest
# sentence in the other text by embedding similarity; sentences with no match above
# the threshold are reported as differences.
# Config: threshold (defaults to the SIMILARITY_THRESHOLD setting), model_name
# (defaults to the default comparison model), embedder (any object with
# encode(list[str]), for tests) and splitter (a function from text to sentences).
@register_strategy("semantic_similarity")
class SemanticSimilarityStrategy(ComparisonStrategy):
    description = "Sentence-level meaning similarity using embeddings."

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)
        threshold = config.get("threshold")
        self.threshold = SIMILARITY_THRESHOLD if threshold is None else threshold
        if isinstance(self.threshold, bool) or not isinstance(
            self.threshold, int | float
        ):
            raise StrategyConfigError(
                "threshold must be a number", strategy="semantic_similarity"
            )
        if not 0.0 <= self.threshold <= 1.0:
            raise StrategyConfigError(
                "threshold must be between 0 and 1", strategy="semantic_similarity"
            )
        self.model_name: str | None = config.get("model_name")
        self.embedder: Any = config.get("embedder")
        self.splitter: Callable[[str], list[str]] = (
            config.get("splitter") or split_sentences
        )

    # Embeds the sentences and returns unit vectors; runs in a worker thread because
    # loading and running a model blocks.
    def _embed(self, sentences: list[str]) -> tuple[np.ndarray, str]:
        if self.embedder is not None:
            embedder, name = self.embedder, self.model_name or "custom embedder"
        else:
            embedder, name = _load_default_embedder(self.model_name)
        vectors = np.asarray(embedder.encode(sentences), dtype=float)
        if vectors.ndim != 2 or vectors.shape[0] != len(sentences):
            raise StrategyExecutionError(
                "embedder must return one vector per sentence", strategy=self.name
            )
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1.0, norms), name

    # Matches each sentence to its closest sentence in the other text.
    async def compare(self, request: StrategyInput) -> StrategyResult:
        source = self.splitter(request.source_text)
        target = self.splitter(request.target_text)
        if not source or not target:
            raise StrategyInputError(
                "both texts need at least one sentence", strategy=self.name
            )
        try:
            vectors, model = await asyncio.to_thread(self._embed, source + target)
        except StrategyError:
            raise
        except Exception as exc:
            raise StrategyExecutionError(
                f"embedding failed: {type(exc).__name__}: {exc}", strategy=self.name
            ) from exc
        similarity = vectors[: len(source)] @ vectors[len(source) :].T
        closest_target = similarity.argmax(axis=1)
        closest_source = similarity.argmax(axis=0)
        best_for_source = similarity.max(axis=1)
        best_for_target = similarity.max(axis=0)
        score = (best_for_source.mean() + best_for_target.mean()) / 2
        findings = [
            _unmatched(
                "no_match_in_target", sentence, sim, target[int(j)], self.threshold
            )
            for sentence, sim, j in zip(
                source, best_for_source, closest_target, strict=True
            )
            if sim < self.threshold
        ] + [
            _unmatched(
                "no_match_in_source", sentence, sim, source[int(i)], self.threshold
            )
            for sentence, sim, i in zip(
                target, best_for_target, closest_source, strict=True
            )
            if sim < self.threshold
        ]
        alignments = [
            {
                "source_index": i,
                "target_index": int(j),
                "source_text": source[i],
                "target_text": target[int(j)],
                "score": round(float(sim), 4),
            }
            for i, (sim, j) in enumerate(
                zip(best_for_source, closest_target, strict=True)
            )
            if sim >= self.threshold
        ]
        return StrategyResult(
            strategy=self.name,
            score=float(np.clip(score, 0.0, 1.0)),
            findings=findings,
            details={
                "model": model,
                "threshold": self.threshold,
                "source_sentences": len(source),
                "target_sentences": len(target),
                "alignments": alignments,
            },
        )


# Builds the finding for a sentence with no close match in the other text. The
# confidence is higher the less similar the closest sentence is.
def _unmatched(
    label: str, sentence: str, similarity: float, closest: str, threshold: float
) -> Finding:
    from_source = label == "no_match_in_target"
    return Finding(
        label=label,
        message=f"closest match scores {similarity:.2f}, below {threshold:.2f}",
        confidence=float(np.clip(1.0 - similarity, 0.0, 1.0)),
        source_span=sentence if from_source else None,
        target_span=None if from_source else sentence,
        evidence=closest,
    )
