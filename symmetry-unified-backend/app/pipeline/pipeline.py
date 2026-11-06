import asyncio
import dataclasses
import logging
import time
from collections.abc import Callable, Sequence

from app.strategies import (
    ComparisonStrategy,
    StrategyError,
    StrategyExecutionError,
    StrategyInput,
    StrategyResult,
    UnknownStrategyError,
    get_strategy,
)

from .errors import PipelineConfigError
from .models import Difference, PipelineResult, StrategySpec, TextInput
from .v2_terms import error_entry, find_span

logger = logging.getLogger(__name__)

Ranker = Callable[[list[Difference]], list[Difference]]


# Default ranker: leaves the differences in the order the strategies reported them.
def keep_order(differences: list[Difference]) -> list[Difference]:
    return list(differences)


# Stage 1: adds character offsets into the original texts to each difference.
def locate_differences(
    differences: list[Difference], source_text: str, target_text: str
) -> list[Difference]:
    taken_source: set[int] = set()
    taken_target: set[int] = set()
    located = []
    for item in differences:
        located.append(
            dataclasses.replace(
                item,
                source_range=find_span(source_text, item.source_span, taken_source),
                target_range=find_span(target_text, item.target_span, taken_target),
            )
        )
    return located


# Stage 2: turns names or specs into ready strategies, failing early on bad requests.
def build_strategies(
    strategies: Sequence[str | StrategySpec],
) -> list[tuple[StrategySpec, ComparisonStrategy]]:
    if not strategies:
        raise PipelineConfigError("at least one strategy is required")
    specs = [s if isinstance(s, StrategySpec) else StrategySpec(s) for s in strategies]
    names = [spec.name for spec in specs]
    if len(set(names)) != len(names):
        raise PipelineConfigError(f"strategies must not repeat: {names}")
    built = []
    for spec in specs:
        try:
            built.append((spec, get_strategy(spec.name, **spec.config)))
        except UnknownStrategyError as exc:
            raise PipelineConfigError(
                str(exc), code="unsupported_strategy"
            ) from exc
        except StrategyError as exc:
            raise PipelineConfigError(str(exc)) from exc
    return built


# Runs one strategy and returns its result, or an error entry if it fails.
async def run_strategy(
    spec: StrategySpec, strategy: ComparisonStrategy, request: StrategyInput
) -> StrategyResult | dict:
    try:
        result = await asyncio.wait_for(strategy.compare(request), spec.timeout_s)
    except StrategyError as exc:
        return error_entry(exc, spec.name)
    except (asyncio.TimeoutError, TimeoutError):  # noqa: UP041  (Python 3.10 needs both)
        error = StrategyExecutionError(
            f"timed out after {spec.timeout_s} seconds", strategy=spec.name
        )
        error.retryable = True
        entry = error_entry(error)
        entry["code"], entry["scope"] = "engine_timeout", "engine"
        return entry
    except Exception as exc:
        logger.exception("strategy %s failed unexpectedly", spec.name)
        error = StrategyExecutionError(
            f"unexpected {type(exc).__name__}: {exc}", strategy=spec.name
        )
        return error_entry(error)
    if not isinstance(result, StrategyResult):
        error = StrategyExecutionError(
            "strategy did not return a StrategyResult", strategy=spec.name
        )
        return error_entry(error)
    return result


# Compares any two texts by running the chosen strategies and assembling one result.
# The texts reach the strategies unchanged, so offsets in the result match the
# originals. The pipeline accepts several strategies; the API layer decides how many
# a request may use.
class ComparisonPipeline:
    def __init__(self, ranker: Ranker | None = None) -> None:
        self.ranker = ranker or keep_order

    # Runs the strategies together; one failing strategy does not fail the others.
    async def run(
        self,
        source: TextInput,
        target: TextInput,
        strategies: Sequence[str | StrategySpec],
    ) -> PipelineResult:
        started = time.perf_counter()
        built = build_strategies(strategies)
        request = StrategyInput(
            source_text=source.text,
            target_text=target.text,
            context={"source": source, "target": target},
        )
        outcomes = await asyncio.gather(
            *(run_strategy(spec, strategy, request) for spec, strategy in built)
        )
        results = [o for o in outcomes if isinstance(o, StrategyResult)]
        errors = [o for o in outcomes if isinstance(o, dict)]
        differences = [
            Difference.from_finding(result.strategy, finding)
            for result in results
            for finding in result.findings
        ]
        return PipelineResult(
            source=source,
            target=target,
            results=results,
            errors=errors,
            differences=self.ranker(
                locate_differences(differences, source.text, target.text)
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
