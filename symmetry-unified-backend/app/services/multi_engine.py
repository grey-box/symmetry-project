from collections.abc import Sequence

from app.engines.base import (
    GenerationRequest,
    GenerationResult,
    ModelAdapter,
)


async def generate_from_engines(
    request: GenerationRequest,
    engines: Sequence[ModelAdapter],
) -> list[GenerationResult]:
    """Send the same request to each engine and return results in input order."""
    engines = tuple(engines)

    if len(engines) < 2:
        raise ValueError("At least two engines are required")

    identities = [(engine.provider, engine.model_name) for engine in engines]
    if len(set(identities)) != len(identities):
        raise ValueError("Each engine must have a distinct provider/model pair")

    results = []
    for engine in engines:
        results.append(await engine.generate(request))

    return results
