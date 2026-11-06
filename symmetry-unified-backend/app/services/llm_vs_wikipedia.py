"""LLM vs Wikipedia comparison for API v2.

Checks each statement of an LLM answer against a Wikipedia article and labels
it ``supported``, ``contradicted`` or ``not_found``, with the engine's
confidence and, when the engine quotes one, the Wikipedia passage it relied on.

The labelling itself is the ``factual_consistency`` strategy, run through the
generic comparison pipeline once per requested engine. This module validates
the request, obtains the article, and maps the pipeline output onto the
published v2 response (``docs/api-v2/api-v2-response-schema.md``).

Known limits:
- Only the first ``max_reference_chars`` (12,000 by default) characters of the
  article reach the engine, so claims backed later in a long article can come
  back ``not_found``. Per-statement evidence retrieval will remove this limit.
- ``not_found`` means the article text did not address the statement. It does
  not mean the statement is false.
- Statements are not aligned to Wikipedia statements yet (``alignments`` is
  empty); evidence is given as quoted passages instead.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from app.engines import (
    AdapterError,
    AdapterResponseError,
    AdapterTimeoutError,
    GenerationRequest,
    GenerationResult,
    ModelAdapter,
)
from app.engines.errors import AdapterConfigError
from app.models.v2 import (
    API_VERSION,
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
    MAX_TEXT_CHARS,
    ComparisonPipeline,
    PipelineConfigError,
    PipelineResult,
    StrategySpec,
    TextInput,
    keep_order,
    to_schema_label,
)
from app.services.v2_engines import (
    EngineHandle,
    EngineResolver,
    NoEngineError,
    UnknownEngineError,
)
from app.services.v2_responses import (
    ERROR_CODES,
    V2Failure,
    engine_model,
    error_detail,
    fail,
    failed_result,
    latency_usage,
)
from app.services.wikipedia_reference import (
    WIKIPEDIA_LICENSE,
    ArticleNotFoundError,
    WikipediaArticle,
    WikipediaReader,
    WikipediaUnavailableError,
    article_ref,
)
from app.strategies import list_strategies

logger = logging.getLogger(__name__)

MODE = "llm_vs_wikipedia"
DIRECTION = "first_to_second"
DEFAULT_STRATEGY = "factual_consistency"
# Strategies that can label LLM statements against a reference on this endpoint.
SUPPORTED_STRATEGIES = ("factual_consistency",)
DEFAULT_TIMEOUT_S = 120.0


# Wraps an engine to remember its last failure, so the API can report the precise
# error code (timeout, bad output, unavailable) after the strategy has wrapped it.
class _RecordingAdapter(ModelAdapter):
    def __init__(self, inner: ModelAdapter) -> None:
        super().__init__(inner.get_model_name())
        self.provider = inner.provider
        self.inner = inner
        self.failure: AdapterError | None = None

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        try:
            return await self.inner.generate(request)
        except AdapterError as exc:
            self.failure = exc
            raise


# What one engine produced: the pipeline output, or only errors if it never ran.
@dataclass
class _EngineRun:
    handle: EngineHandle
    outcome: PipelineResult | None
    errors: list[ErrorDetail] = field(default_factory=list)
    latency_ms: float = 0.0


# Validates an LLM vs Wikipedia request, runs it on every engine and builds the response.
class LlmVsWikipediaService:
    def __init__(
        self,
        reader: WikipediaReader,
        engines: EngineResolver,
        pipeline: ComparisonPipeline | None = None,
    ) -> None:
        self.reader = reader
        self.engines = engines
        # Statements are reported in text order, so no significance ranking is needed.
        self.pipeline = pipeline or ComparisonPipeline(ranker=keep_order)

    # Returns the response, or raises V2Failure when nothing usable was produced.
    async def compare(
        self, body: ComparisonRequest, request_id: str
    ) -> ComparisonResponse:
        started = time.perf_counter()
        strategy = self._check_request(body)
        claim_input = next(s for s in body.sources if s.kind == "llm_output")
        wiki_input = next(s for s in body.sources if s.kind == "wikipedia")
        if claim_input.generate_with is not None:
            raise fail(
                "invalid_request",
                "Generating the LLM answer on the server (generate_with) is not "
                "supported by this endpoint yet. Send the answer as text.",
                "source",
                source_id=claim_input.id,
            )
        try:
            ref = article_ref(
                wiki_input.url,
                wiki_input.title,
                wiki_input.language,
                wiki_input.revision_id,
            )
        except ValueError as exc:
            raise fail(
                "invalid_request", str(exc), "source", source_id=wiki_input.id
            ) from None

        engines = self._resolve_engines(body.engines)
        article = await self._read_article(ref, wiki_input.id)
        claims, reference = self._texts(claim_input, wiki_input, article)

        timeout_s = body.options.timeout_seconds or DEFAULT_TIMEOUT_S
        runs = await asyncio.gather(
            *(
                self._run(engine, strategy, reference, claims, timeout_s)
                for engine in engines
            )
        )

        source_ids = (claim_input.id, wiki_input.id)
        results, errors = [], []
        for run in runs:
            errors.extend(run.errors)
            if run.outcome is not None and run.outcome.results:
                results.append(
                    self._ok_result(run, source_ids, claims.text, article, body)
                )
            else:
                results.append(
                    failed_result(source_ids, run.handle, DIRECTION, run.latency_ms)
                )
        errors = _unique(errors)
        if not any(result.status == "ok" for result in results):
            raise V2Failure(
                errors
                or [error_detail("internal_error", "No engine produced a result.")]
            )

        include_text = body.options.include_source_text
        sources = [
            _wiki_source(s, article, include_text)
            if s.kind == "wikipedia"
            else _claim_source(s, include_text)
            for s in body.sources
        ]
        return ComparisonResponse(
            api_version=API_VERSION,
            request_id=request_id,
            status="partial" if errors else "success",
            mode=MODE,
            strategy=strategy,
            prompt=body.prompt,
            duration_ms=round((time.perf_counter() - started) * 1000),
            sources=sources,
            results=results,
            errors=errors,
        )

    # Checks the parts of the request this endpoint handles and returns the strategy id.
    @staticmethod
    def _check_request(body: ComparisonRequest) -> str:
        if body.mode != MODE:
            raise fail(
                "invalid_request",
                f"This endpoint only accepts mode '{MODE}', got '{body.mode}'.",
                details={"field": "mode"},
            )
        strategy = body.strategy or DEFAULT_STRATEGY
        if strategy not in list_strategies() or strategy not in SUPPORTED_STRATEGIES:
            known = strategy in list_strategies()
            raise fail(
                "unsupported_strategy",
                f"Strategy '{strategy}' "
                + (
                    "cannot label statements against Wikipedia."
                    if known
                    else "is not available."
                )
                + f" Supported here: {', '.join(SUPPORTED_STRATEGIES)}.",
                details={"strategy": strategy, "supported": list(SUPPORTED_STRATEGIES)},
            )
        options = body.options
        if options.direction not in (None, DIRECTION):
            raise fail(
                "invalid_request",
                f"Only direction '{DIRECTION}' is supported for {MODE}: the LLM's "
                "statements are checked, the article's are not.",
                details={"field": "options.direction"},
            )
        if options.pivot_language is not None:
            raise fail(
                "invalid_request",
                "pivot_language is not supported by this endpoint yet.",
                details={"field": "options.pivot_language"},
            )
        return strategy

    def _resolve_engines(self, engine_ids: list[str]) -> list[EngineHandle]:
        try:
            return self.engines.resolve(list(engine_ids))
        except UnknownEngineError as exc:
            raise fail(
                "unsupported_engine",
                f"Unknown engine ids: {', '.join(exc.engine_ids)}.",
                details={"unknown": exc.engine_ids, "available": exc.available},
            ) from None
        except NoEngineError as exc:
            raise fail("engine_unavailable", str(exc), retryable=False) from None
        except AdapterConfigError as exc:
            logger.error("model catalog could not be loaded: %s", exc)
            raise fail(
                "internal_error",
                "The server's model catalog is invalid.",
                retryable=False,
            ) from None

    async def _read_article(self, ref, source_id: str) -> WikipediaArticle:
        try:
            return await self.reader.read(ref)
        except ArticleNotFoundError as exc:
            raise fail(
                "source_not_found", exc.message, "source", source_id=source_id
            ) from None
        except WikipediaUnavailableError as exc:
            # The schema has no code for an unreachable source, so this uses
            # internal_error; the scope and source_id still say which source failed.
            raise fail(
                "internal_error", exc.message, "source", source_id=source_id
            ) from None

    # The texts handed to the pipeline: the article is the reference (pipeline source),
    # the LLM answer holds the statements to check (pipeline target).
    @staticmethod
    def _texts(
        claim_input: SourceInput, wiki_input: SourceInput, article: WikipediaArticle
    ) -> tuple[TextInput, TextInput]:
        try:
            claims = TextInput(
                text=claim_input.text,
                id=claim_input.id,
                kind="llm_output",
                language=claim_input.language,
            )
        except ValueError as exc:
            raise fail(
                "invalid_request",
                f"LLM answer: {exc}.",
                "source",
                source_id=claim_input.id,
            ) from None
        reference = TextInput(
            text=article.text[:MAX_TEXT_CHARS],
            label=article.title,
            id=wiki_input.id,
            kind="wikipedia",
            language=article.language,
            url=article.url,
            revision_id=article.revision_id,
        )
        return claims, reference

    async def _run(
        self,
        handle: EngineHandle,
        strategy: str,
        reference: TextInput,
        claims: TextInput,
        timeout_s: float,
    ) -> _EngineRun:
        if handle.adapter is None:
            reason = handle.error.message if handle.error else "it could not be built"
            error = error_detail(
                "engine_unavailable",
                f"Engine '{handle.id}' is not usable: {reason}",
                "engine",
                engine_id=handle.id,
                retryable=False,
            )
            return _EngineRun(handle, None, [error])

        recorder = _RecordingAdapter(handle.adapter)
        spec = StrategySpec(
            strategy, config={"model_adapter": recorder}, timeout_s=timeout_s
        )
        started = time.perf_counter()
        try:
            outcome = await self.pipeline.run(reference, claims, [spec])
        except PipelineConfigError as exc:
            code = exc.code if exc.code in ERROR_CODES else "invalid_request"
            return _EngineRun(handle, None, [error_detail(code, exc.message)])
        latency_ms = (time.perf_counter() - started) * 1000
        errors = [_engine_error(entry, recorder, handle.id) for entry in outcome.errors]
        return _EngineRun(handle, outcome, errors, latency_ms)

    # Builds the result of an engine that finished: one labelled statement per sentence.
    @staticmethod
    def _ok_result(
        run: _EngineRun,
        source_ids: tuple[str, str],
        claim_text: str,
        article: WikipediaArticle,
        body: ComparisonRequest,
    ) -> Result:
        strategy_result = run.outcome.results[0]
        if strategy_result.details.get("reference_truncated"):
            logger.info(
                "article %r was truncated before checking; later passages were not seen",
                article.title,
            )
        statements = _statements(
            strategy_result.details.get("statements", []),
            claim_text,
            claim_id=source_ids[0],
            wiki_id=source_ids[1],
            evidence_url=article.url,
            include_evidence=body.options.include_evidence,
        )
        return Result(
            source_ids=source_ids,
            engine=engine_model(run.handle),
            status="ok",
            direction=DIRECTION,
            comparison_language=None,
            overall_score=_overall_score(statements),
            score_basis="model_reported",
            statements=statements,
            alignments=[],
            usage=latency_usage(run.latency_ms),
        )


# Turns the strategy's per-statement rows into schema statements with exact spans.
def _statements(
    rows: list[dict],
    claim_text: str,
    *,
    claim_id: str,
    wiki_id: str,
    evidence_url: str,
    include_evidence: bool,
) -> list[Statement]:
    statements = []
    cursor = 0
    for index, row in enumerate(rows):
        text = row["statement"]
        start = claim_text.find(text, cursor)
        if start == -1:
            start = claim_text.find(text)
        if start == -1:
            logger.warning("statement %r not found in the LLM answer; skipped", text)
            continue
        cursor = start + len(text)
        label = to_schema_label(row["label"])
        evidence = []
        if include_evidence and row.get("evidence"):
            evidence.append(
                Evidence(
                    kind="wikipedia_passage",
                    source_id=wiki_id,
                    statement_id=None,
                    text=row["evidence"],
                    url=evidence_url,
                )
            )
        statements.append(
            Statement(
                id=f"{claim_id}-{index}",
                source_id=claim_id,
                index=index,
                text=text,
                translated_text=None,
                span=Span(start=start, end=start + len(text)),
                section_ref=None,
                block_id=None,
                label=label,
                confidence=None if label == "unverifiable" else row.get("confidence"),
                best_match_similarity=None,
                evidence=evidence,
            )
        )
    return statements


# Share of judged statements labelled supported, ignoring unverifiable (schema section 6).
def _overall_score(statements: list[Statement]) -> float | None:
    judged = [s for s in statements if s.label not in (None, "unverifiable")]
    if not judged:
        return None
    return sum(s.label == "supported" for s in judged) / len(judged)


# Maps a pipeline error entry for one engine onto the v2 error model.
def _engine_error(
    entry: dict, recorder: _RecordingAdapter, engine_id: str
) -> ErrorDetail:
    message = str(entry.get("message") or "The engine failed.")
    if entry.get("code") == "invalid_request":
        return error_detail("invalid_request", message)
    failure = recorder.failure
    if entry.get("code") == "engine_timeout" or isinstance(
        failure, AdapterTimeoutError
    ):
        code = "engine_timeout"
    elif isinstance(failure, AdapterResponseError):
        code = "engine_bad_output"
    elif failure is not None:
        code = "engine_unavailable"
    elif message.startswith("unexpected "):
        code = "internal_error"
    else:
        # The engine answered but its reply could not be read as a verdict.
        code = "engine_bad_output"
    retryable = failure.retryable if failure is not None else None
    return error_detail(
        code, message, "engine", engine_id=engine_id, retryable=retryable
    )


# Drops repeated errors, such as the same invalid input reported by every engine.
def _unique(errors: list[ErrorDetail]) -> list[ErrorDetail]:
    seen, unique = set(), []
    for error in errors:
        key = (error.code, error.scope, error.engine_id, error.source_id, error.message)
        if key not in seen:
            seen.add(key)
            unique.append(error)
    return unique


def _claim_source(source: SourceInput, include_text: bool) -> Source:
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


def _wiki_source(
    source: SourceInput, article: WikipediaArticle, include_text: bool
) -> Source:
    return Source(
        id=source.id,
        kind="wikipedia",
        label=article.title,
        language=article.language,
        url=article.url,
        revision_id=article.revision_id,
        license=WIKIPEDIA_LICENSE,
        attribution=article.attribution,
        generated_by=None,
        text=article.text if include_text else None,
        blocks=None,
    )
