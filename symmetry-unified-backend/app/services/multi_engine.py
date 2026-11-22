from collections.abc import Sequence
from dataclasses import dataclass, field

from app.engines.base import (
    GenerationRequest,
    GenerationResult,
    ModelAdapter,
)
from app.engines.errors import AdapterError


@dataclass(frozen=True)
class MultiEngineResult:
    """Successful generations and per-engine failures from one fan-out."""

    results: list[GenerationResult] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


async def generate_from_engines(
    request: GenerationRequest,
    engines: Sequence[ModelAdapter],
) -> MultiEngineResult:
    """Send one request to every engine without one failure stopping the others."""
    engines = tuple(engines)

    if len(engines) < 2:
        raise ValueError("At least two engines are required")

    identities = [(engine.provider, engine.model_name) for engine in engines]
    if len(set(identities)) != len(identities):
        raise ValueError("Each engine must have a distinct provider/model pair")

    results = []
    errors = []

    for engine in engines:
        try:
            results.append(await engine.generate(request))
        except AdapterError as exc:
            errors.append(exc.to_dict())

    return MultiEngineResult(results=results, errors=errors)