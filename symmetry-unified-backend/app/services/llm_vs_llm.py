"""LLM vs LLM comparison for API v2.

Compares two or more LLM answers to the same prompt. Every pair of answers gets
one result (3 answers give 3 pairs). Within a pair, each sentence of both
answers is labelled against the other answer (direction ``both``):
``supported`` when the other answer says something very similar, ``partial``
when it is close (only with ``options.partial_threshold``), ``not_found``
otherwise. Matching sentences cite each other as ``counterpart_statement``
evidence, and the pair's ``alignments`` mark them ``equal``, ``modified``,
``missing`` or ``added``: the highlighted disagreements of schema section 7.

The comparison is the ``semantic_similarity`` strategy, run through the generic
comparison pipeline in both directions. Similar meaning is not agreement on
facts, and agreement between models is not proof that they are right.

Not supported yet: generating the answers on the server (``generate_with``),
which needs the multi-engine fan-out with per-engine errors; direction
``first_to_second``; ``pivot_language``.
"""

import dataclasses
import itertools
import logging
import time
from dataclasses import dataclass, field

from app.models.v2 import (
    API_VERSION,
    Alignment,
    ComparisonRequest,
    ComparisonResponse,
    ErrorDetail,
    Evidence,
    Result,
    Source,
    SourceInput,
    Span,
    Statement,
)
from app.pipeline import (
    ComparisonPipeline,
    PipelineConfigError,
    StrategySpec,
    TextInput,
    keep_order,
)
from app.services.v2_engines import EngineHandle
from app.services.v2_responses import (
    ERROR_CODES,
    V2Failure,
    engine_model,
    error_detail,
    fail,
    failed_result,
    latency_usage,
)
from app.services.v2_similarity import (
    embedding_engine,
    embedding_error,
    similarity_rows,
)
from app.services.v2_strategies import StrategyProfile, choose_strategy
from app.strategies.text import split_sentences

logger = logging.getLogger(__name__)

MODE = "llm_vs_llm"
DIRECTION = "both"
DEFAULT_TIMEOUT_S = 120.0

# Alignment category of a paired statement, by the label of the statement it starts from.
_PAIRED_CATEGORY = {"supported": "equal", "partial": "modified"}


# What comparing one pair produced: per-sentence rows for each answer, or errors.
@dataclass
class _PairRun:
    source_ids: tuple[str, str]
    rows: tuple[list[dict], list[dict]] | None = None
    model: str | None = None
    errors: list[ErrorDetail] = field(default_factory=list)
    latency_ms: float = 0.0


# Validates an LLM vs LLM request, compares every pair of answers and builds the response.
class LlmVsLlmService:
    # strategy_config adds settings per strategy id, for example a test embedder
    # for semantic_similarity: {"semantic_similarity": {"embedder": ...}}.
    def __init__(
        self,
        pipeline: ComparisonPipeline | None = None,
        strategy_config: dict[str, dict] | None = None,
    ) -> None:
        self.pipeline = pipeline or ComparisonPipeline(ranker=keep_order)
        self.strategy_config = strategy_config or {}

    # Returns the response, or raises V2Failure when no pair could be compared.
    async def compare(
        self, body: ComparisonRequest, request_id: str
    ) -> ComparisonResponse:
        started = time.perf_counter()
        profile = self._check_request(body)
        texts = {source.id: _text_input(source) for source in body.sources}
        config = dict(self.strategy_config.get(profile.id, {}))
        if body.options.similarity_threshold is not None:
            config["threshold"] = body.options.similarity_threshold
        handle = embedding_engine(config.get("model_name"))

        # Pairs run one after another: they share one CPU-bound embedding model, and
        # running them in parallel can load several copies of it before the
        # model cache is filled.
        pairs = list(itertools.combinations([s.id for s in body.sources], 2))
        runs = [
            await self._compare_pair(profile, config, handle, texts[a], texts[b], body)
            for a, b in pairs
        ]

        results, errors = [], []
        for run in runs:
            if run.rows is None:
                errors.extend(run.errors)
                results.append(
                    failed_result(run.source_ids, handle, DIRECTION, run.latency_ms)
                )
            else:
                results.append(_ok_result(run, handle, texts, body, profile))
        errors = _unique(errors)
        if not any(result.status == "ok" for result in results):
            raise V2Failure(
                errors or [error_detail("internal_error", "No pair was compared.")]
            )

        include_text = body.options.include_source_text
        return ComparisonResponse(
            api_version=API_VERSION,
            request_id=request_id,
            status="partial" if errors else "success",
            mode=MODE,
            strategy=profile.id,
            prompt=body.prompt,
            duration_ms=round((time.perf_counter() - started) * 1000),
            sources=[_source(s, include_text) for s in body.sources],
            results=results,
            errors=errors,
        )

    # Checks the parts of the request this endpoint handles and returns the strategy.
    @staticmethod
    def _check_request(body: ComparisonRequest) -> StrategyProfile:
        if body.mode != MODE:
            raise fail(
                "invalid_request",
                f"This endpoint only accepts mode '{MODE}', got '{body.mode}'.",
                details={"field": "mode"},
            )
        profile = choose_strategy(MODE, body.strategy, body.engines)
        if profile.engine != "embedding":
            raise fail(
                "unsupported_strategy",
                f"Strategy '{profile.id}' is not supported by this endpoint yet.",
                details={"strategy": profile.id},
            )
        for source in body.sources:
            if source.generate_with is not None:
                raise fail(
                    "invalid_request",
                    "Generating answers on the server (generate_with) is not "
                    "supported yet. Send each answer as text.",
                    "source",
                    source_id=source.id,
                )
        options = body.options
        if options.direction not in (None, DIRECTION):
            raise fail(
                "invalid_request",
                f"Only direction '{DIRECTION}' is supported for {MODE}.",
                details={"field": "options.direction"},
            )
        if options.pivot_language is not None:
            raise fail(
                "invalid_request",
                "pivot_language is not supported by this endpoint yet.",
                details={"field": "options.pivot_language"},
            )
        return profile

    # Compares one pair in both directions, so every sentence of both answers is judged.
    async def _compare_pair(
        self,
        profile: StrategyProfile,
        config: dict,
        handle: EngineHandle,
        first: TextInput,
        second: TextInput,
        body: ComparisonRequest,
    ) -> _PairRun:
        source_ids = (first.id, second.id)
        timeout_s = body.options.timeout_seconds or DEFAULT_TIMEOUT_S
        spec = StrategySpec(profile.id, config=config, timeout_s=timeout_s)
        started = time.perf_counter()
        try:
            forward = await self.pipeline.run(first, second, [spec])
            backward = await self.pipeline.run(second, first, [spec])
        except PipelineConfigError as exc:
            code = exc.code if exc.code in ERROR_CODES else "invalid_request"
            return _PairRun(source_ids, errors=[error_detail(code, exc.message)])
        latency_ms = (time.perf_counter() - started) * 1000
        failures = forward.errors + backward.errors
        if failures:
            details = {"source_ids": list(source_ids)}
            errors = [embedding_error(e, handle.id, details) for e in failures]
            return _PairRun(source_ids, errors=errors, latency_ms=latency_ms)
        rows = tuple(
            similarity_rows(
                outcome.results[0].details,
                outcome.results[0].findings,
                text.text,
                partial_threshold=body.options.partial_threshold,
            )
            for outcome, text in ((forward, first), (backward, second))
        )
        return _PairRun(
            source_ids,
            rows=rows,
            model=forward.results[0].details.get("model"),
            latency_ms=latency_ms,
        )


# Builds the result of a compared pair: statements of both answers plus alignments.
def _ok_result(
    run: _PairRun,
    handle: EngineHandle,
    texts: dict[str, TextInput],
    body: ComparisonRequest,
    profile: StrategyProfile,
) -> Result:
    first_id, second_id = run.source_ids
    include_evidence = body.options.include_evidence
    first = _statements(
        run.rows[0], texts[first_id], texts[second_id], include_evidence
    )
    second = _statements(
        run.rows[1], texts[second_id], texts[first_id], include_evidence
    )
    if run.model:
        handle = dataclasses.replace(handle, model=run.model)
    statements = [statement for statement, _ in first + second]
    scores = [s.best_match_similarity for s in statements]
    return Result(
        source_ids=run.source_ids,
        engine=engine_model(handle),
        status="ok",
        direction=DIRECTION,
        comparison_language=None,
        overall_score=round(sum(scores) / len(scores), 4) if scores else None,
        score_basis=profile.score_basis,
        statements=statements,
        alignments=_alignments(first, second),
        usage=latency_usage(run.latency_ms),
    )


# Turns one answer's rows into statements with exact spans, each paired with the
# statement id of its closest sentence in the other answer. Statement ids are
# "<source id>-<sentence index>"; evidence cites that closest sentence by its id.
def _statements(
    rows: list[dict], own: TextInput, other: TextInput, include_evidence: bool
) -> list[tuple[Statement, str | None]]:
    sentences = split_sentences(own.text)
    other_index: dict[str, int] = {}
    for index, sentence in enumerate(split_sentences(other.text)):
        other_index.setdefault(sentence, index)
    statements, position, cursor = [], 0, 0
    for row in rows:
        while position < len(sentences) and sentences[position] != row["statement"]:
            position += 1
        if position == len(sentences):
            logger.warning("statement %r not found in %s", row["statement"], own.id)
            break
        start = own.text.find(row["statement"], cursor)
        cursor = start + len(row["statement"])
        closest = other_index.get(row["closest"])
        counterpart = f"{other.id}-{closest}" if closest is not None else None
        evidence = []
        if include_evidence and row["evidence"] and counterpart:
            evidence.append(
                Evidence(
                    kind="counterpart_statement",
                    source_id=other.id,
                    statement_id=counterpart,
                    text=row["evidence"],
                    url=None,
                )
            )
        statement = Statement(
            id=f"{own.id}-{position}",
            source_id=own.id,
            index=position,
            text=row["statement"],
            translated_text=None,
            span=Span(start=start, end=cursor),
            section_ref=None,
            block_id=None,
            label=row["label"],
            confidence=None,
            best_match_similarity=row["similarity"],
            evidence=evidence,
        )
        statements.append((statement, counterpart))
        position += 1
    return statements


# Builds the pair's alignments (schema section 7). Each first-answer statement is
# equal, modified or missing; second-answer statements with no counterpart are added,
# and matched ones not already paired from the first answer get their own pair.
def _alignments(
    first: list[tuple[Statement, str | None]],
    second: list[tuple[Statement, str | None]],
) -> list[Alignment]:
    alignments: list[Alignment] = []
    paired: set[tuple[str, str]] = set()

    def add(source_ref, target_ref, category, similarity) -> None:
        alignments.append(
            Alignment(
                id=f"m-{len(alignments)}",
                source_ref=source_ref,
                target_ref=target_ref,
                category=category,
                similarity=similarity,
                word_diff=None,
            )
        )

    for statement, counterpart in first:
        category = _PAIRED_CATEGORY.get(statement.label)
        if category and counterpart:
            paired.add((statement.id, counterpart))
            add(statement.id, counterpart, category, statement.best_match_similarity)
        else:
            add(statement.id, None, "missing", None)
    for statement, counterpart in second:
        category = _PAIRED_CATEGORY.get(statement.label)
        if not (category and counterpart):
            add(None, statement.id, "added", None)
        elif (counterpart, statement.id) not in paired:
            paired.add((counterpart, statement.id))
            add(counterpart, statement.id, category, statement.best_match_similarity)
    return alignments


# Drops repeated errors, such as one failure reported for both directions of a pair.
def _unique(errors: list[ErrorDetail]) -> list[ErrorDetail]:
    seen, unique = set(), []
    for error in errors:
        key = (
            error.code,
            error.scope,
            error.engine_id,
            error.message,
            str(error.details),
        )
        if key not in seen:
            seen.add(key)
            unique.append(error)
    return unique


# The text handed to the pipeline for one answer.
def _text_input(source: SourceInput) -> TextInput:
    try:
        return TextInput(
            text=source.text, id=source.id, kind="llm_output", language=source.language
        )
    except ValueError as exc:
        raise fail(
            "invalid_request",
            f"Answer '{source.id}': {exc}.",
            "source",
            source_id=source.id,
        ) from None


def _source(source: SourceInput, include_text: bool) -> Source:
    return Source(
        id=source.id,
        kind="llm_output",
        label=None,
        language=source.language,
        url=None,
        revision_id=None,
        license=None,
        attribution=None,
        generated_by=None,
        text=source.text if include_text else None,
        blocks=None,
    )
