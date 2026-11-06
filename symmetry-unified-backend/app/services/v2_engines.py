"""Turns the engine ids of an API v2 request into ready model adapters.

Engine ids are the ``id`` values of the model catalog (``llm_models.toml``, see
``llm_models.example.toml``). An empty list means the server default: the
cheapest catalog model that can be built, as chosen by ``ModelSelector``.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.engines import AdapterConfigError, AdapterError, ModelAdapter
from app.engines.selection import ModelSelector, ModelSpec, load_selector

# Adapter providers that can appear as an engine, mapped to the schema's engine type.
ENGINE_TYPES = {
    "cloud_llm": "cloud_llm",
    "local_slm": "local_slm",
    "openrouter": "openrouter",
}


# Raised when a requested engine id is not in the catalog.
class UnknownEngineError(Exception):
    def __init__(self, engine_ids: list[str], available: list[str]) -> None:
        self.engine_ids = engine_ids
        self.available = available
        super().__init__(
            f"unknown engine ids {engine_ids}; available: {available or 'none'}"
        )


# Raised when the request names no engine and no catalog model can be used.
class NoEngineError(Exception):
    pass


# One comparing engine. adapter is None when the engine could not be built (for
# example a missing API key); error then says why.
@dataclass(frozen=True)
class EngineHandle:
    id: str
    type: str
    model: str
    provider: str | None = None
    adapter: ModelAdapter | None = None
    error: AdapterError | None = None


# The interface the v2 endpoints use to get their engines, so tests can supply fakes.
class EngineResolver(ABC):
    @abstractmethod
    def resolve(self, engine_ids: list[str]) -> list[EngineHandle]: ...


# Resolves engine ids against the model catalog.
class CatalogEngineResolver(EngineResolver):
    def __init__(self, selector: ModelSelector | None = None) -> None:
        self._selector = selector

    def resolve(self, engine_ids: list[str]) -> list[EngineHandle]:
        selector = self._selector or load_selector()
        engines = {
            spec_id: spec
            for spec_id, spec in selector.specs.items()
            if spec.provider in ENGINE_TYPES
        }
        if not engine_ids:
            return [self._default(selector, engines)]
        unknown = [i for i in engine_ids if i not in engines]
        if unknown:
            raise UnknownEngineError(unknown, sorted(engines))
        return [self._build(selector, engines[i]) for i in dict.fromkeys(engine_ids)]

    # The cheapest catalog engine that can be built.
    def _default(self, selector: ModelSelector, engines: dict) -> EngineHandle:
        reasons = []
        for spec in selector.candidates():
            if spec.id not in engines:
                continue
            handle = self._build(selector, spec)
            if handle.adapter is not None:
                return handle
            reasons.append(f"{spec.id}: {handle.error.message}")
        detail = "; ".join(reasons) or "the model catalog has no engines"
        raise NoEngineError(f"no comparison engine is available ({detail})")

    @staticmethod
    def _build(selector: ModelSelector, spec: ModelSpec) -> EngineHandle:
        base_url = str(spec.config.get("base_url") or "")
        provider = urlsplit(base_url).hostname if base_url else None
        try:
            adapter, error = selector.build(spec), None
        except AdapterConfigError as exc:
            adapter, error = None, exc
        return EngineHandle(
            id=spec.id,
            type=ENGINE_TYPES[spec.provider],
            model=spec.model,
            provider=provider or spec.provider,
            adapter=adapter,
            error=error,
        )
