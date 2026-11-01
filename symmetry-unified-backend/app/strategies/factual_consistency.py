import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from .base import ComparisonStrategy, Finding, StrategyInput, StrategyResult
from .errors import StrategyError, StrategyExecutionError, StrategyInputError
from .registry import register_strategy
from .text import split_sentences

LABELS = ("supported", "contradicted", "not_found")
DEFAULT_MAX_CONCURRENCY = 4
DEFAULT_MAX_STATEMENTS = 100
DEFAULT_MAX_REFERENCE_CHARS = 12_000

SYSTEM_PROMPT = (
    "You check one statement against a reference text. Use only the reference, "
    "not your own knowledge. Reply with a single JSON object and nothing else: "
    '{"label": "supported" | "contradicted" | "not_found", '
    '"confidence": a number from 0 to 1, '
    '"evidence": an exact quote from the reference, or "" if there is none}. '
    "supported: the reference states the statement or clearly implies it. "
    "contradicted: the reference says something that conflicts with it. "
    "not_found: the reference does not address it."
)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


# Loads the engine types when a check runs, so this module imports without the engines package.
def _engine_types() -> tuple[type, type]:
    try:
        from app.engines import AdapterError, GenerationRequest
    except ImportError as exc:
        raise StrategyExecutionError(
            f"engine support is not installed: {exc}",
            strategy="factual_consistency",
        ) from exc
    return AdapterError, GenerationRequest


# Collapses whitespace and case so a quote can be matched against the reference.
def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


# Reads the engine's JSON reply into a label, a confidence and a verified quote.
def parse_verdict(reply: str, reference: str) -> tuple[str, float | None, str | None]:
    match = _JSON_OBJECT.search(reply)
    if not match:
        raise ValueError("reply contains no JSON object")
    data = json.loads(match.group(0))
    label = str(data.get("label", "")).strip().lower()
    if label not in LABELS:
        raise ValueError(f"unknown label {label!r}")
    raw = data.get("confidence")
    confidence = None if raw is None else min(1.0, max(0.0, float(raw)))
    quote = str(data.get("evidence") or "").strip()
    verified = quote if quote and _normalize(quote) in _normalize(reference) else None
    return label, confidence, verified


# Checks each statement in the target text against the source text with an engine.
# The source text is the reference (for example a Wikipedia article), the target
# text holds the statements to check (for example LLM output).
@register_strategy("factual_consistency")
class FactualConsistencyStrategy(ComparisonStrategy):
    description = "Labels each target statement supported, contradicted or not found."
    requires = ("model_adapter",)

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)
        self.adapter = config["model_adapter"]
        self.max_concurrency = config.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
        self.max_statements = config.get("max_statements", DEFAULT_MAX_STATEMENTS)
        self.max_reference_chars = config.get(
            "max_reference_chars", DEFAULT_MAX_REFERENCE_CHARS
        )
        self.splitter: Callable[[str], list[str]] = config.get(
            "splitter", split_sentences
        )

    # Asks the engine about one statement and returns its verdict.
    async def _check(
        self, statement: str, reference: str, limit: asyncio.Semaphore
    ) -> tuple[str, float | None, str | None]:
        adapter_error, generation_request = _engine_types()
        request = generation_request(
            prompt=f"Reference:\n{reference}\n\nStatement:\n{statement}",
            system_prompt=SYSTEM_PROMPT,
            max_tokens=300,
            temperature=0.0,
        )
        async with limit:
            try:
                reply = (await self.adapter.generate(request)).text
            except adapter_error as exc:
                error = StrategyExecutionError(
                    f"engine failed: {exc.message}", strategy=self.name
                )
                error.retryable = exc.retryable
                raise error from exc
        try:
            return parse_verdict(reply, reference)
        except (ValueError, TypeError) as exc:
            raise StrategyExecutionError(
                f"could not read the engine's reply for {statement!r}: {exc}",
                strategy=self.name,
            ) from exc

    # Labels every statement in the target text and reports the ones not supported.
    async def compare(self, request: StrategyInput) -> StrategyResult:
        statements = self.splitter(request.target_text)
        if len(statements) > self.max_statements:
            raise StrategyInputError(
                f"{len(statements)} statements exceed the limit of "
                f"{self.max_statements}",
                strategy=self.name,
            )
        reference = request.source_text
        truncated = len(reference) > self.max_reference_chars
        reference = reference[: self.max_reference_chars]
        limit = asyncio.Semaphore(self.max_concurrency)
        outcomes = await asyncio.gather(
            *(self._check(s, reference, limit) for s in statements),
            return_exceptions=True,
        )
        for outcome in outcomes:
            if isinstance(outcome, BaseException):
                if isinstance(outcome, StrategyError):
                    raise outcome
                raise StrategyExecutionError(
                    f"unexpected {type(outcome).__name__}: {outcome}",
                    strategy=self.name,
                ) from outcome
        rows = [
            {
                "statement": statement,
                "label": label,
                "confidence": confidence,
                "evidence": evidence,
            }
            for statement, (label, confidence, evidence) in zip(
                statements, outcomes, strict=True
            )
        ]
        findings = [
            Finding(
                label=row["label"],
                confidence=row["confidence"],
                target_span=row["statement"],
                evidence=row["evidence"],
            )
            for row in rows
            if row["label"] != "supported"
        ]
        supported = sum(row["label"] == "supported" for row in rows)
        return StrategyResult(
            strategy=self.name,
            score=supported / len(rows),
            findings=findings,
            details={
                "statements": rows,
                "counts": {
                    label: sum(r["label"] == label for r in rows) for label in LABELS
                },
                "reference_truncated": truncated,
                "model": self.adapter.get_model_name(),
            },
        )
