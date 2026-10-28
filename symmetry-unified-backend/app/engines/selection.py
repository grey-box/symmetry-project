import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .base import GenerationRequest, GenerationResult, ModelAdapter
from .errors import AdapterConfigError, AdapterError
from .registry import get_adapter

logger = logging.getLogger(__name__)

# Providers that run locally and may omit prices; every other model must state its prices,
# so a model with a forgotten price is never mistaken for a free one.
UNPRICED_PROVIDERS = {"local_slm", "fake"}
LLM_MODELS_PATH_ENV = "LLM_MODELS_PATH"
DEFAULT_CATALOG = "llm_models.toml"


# One entry in the model catalog: which adapter and model to call, and what it costs.
@dataclass(frozen=True)
class ModelSpec:
    id: str
    provider: str
    model: str
    tier: int = 1
    price_per_1m_input: float = 0.0
    price_per_1m_output: float = 0.0
    config: dict = field(default_factory=dict)

    # Blended USD price used to rank models: input plus output price per 1M tokens.
    @property
    def cost_per_1m(self) -> float:
        return self.price_per_1m_input + self.price_per_1m_output

    # Adapter settings, with this entry's prices so results can report cost_usd.
    def adapter_config(self) -> dict:
        return {
            **self.config,
            "price_per_1m_input": self.price_per_1m_input,
            "price_per_1m_output": self.price_per_1m_output,
        }


# Picks which model to call: the cheapest usable one by default, and the models named in
# language_overrides for the language pairs where a cheaper model is known to underperform.
# Override keys are "<source>-><target>" language codes, e.g. "en->sw"; values are ordered model ids.
class ModelSelector:
    def __init__(
        self,
        specs: list[ModelSpec],
        language_overrides: dict[str, list[str]] | None = None,
    ):
        self.specs = {}
        for spec in specs:
            if spec.id in self.specs:
                raise _config_error(f"duplicate model id {spec.id!r}")
            self.specs[spec.id] = spec
        self.overrides = {}
        for pair, ids in (language_overrides or {}).items():
            unknown = [i for i in ids if i not in self.specs]
            if not ids or unknown:
                raise _config_error(
                    f"language override {pair!r} must list known model ids (unknown: {unknown})"
                )
            self.overrides[_pair_key(pair)] = list(ids)

    # Returns the models to try, in order. A pair with an override uses only that list;
    # every other pair uses all models, cheapest first (ties go to the lower tier, then id).
    def candidates(
        self, source_lang: str | None = None, target_lang: str | None = None
    ) -> list[ModelSpec]:
        if source_lang and target_lang:
            ids = self.overrides.get(_pair_key(f"{source_lang}->{target_lang}"))
            if ids:
                return [self.specs[i] for i in ids]
        return sorted(self.specs.values(), key=lambda s: (s.cost_per_1m, s.tier, s.id))

    # Builds the adapter for one catalog entry.
    def build(self, spec: ModelSpec) -> ModelAdapter:
        return get_adapter(spec.provider, spec.model, **spec.adapter_config())

    # Returns the adapter for the first candidate that can be built, skipping any whose
    # configuration is unusable (for example a missing API key).
    def select(
        self, source_lang: str | None = None, target_lang: str | None = None
    ) -> ModelAdapter:
        adapter, _ = self._first_usable(self.candidates(source_lang, target_lang))
        return adapter

    # Generates with the selected model. With fallback=True a retryable failure moves on to the
    # next candidate; other failures always raise. The result names the model that answered.
    async def generate(
        self,
        request: GenerationRequest,
        source_lang: str | None = None,
        target_lang: str | None = None,
        *,
        fallback: bool = False,
    ) -> GenerationResult:
        pending = self.candidates(source_lang, target_lang)
        last_error = None
        while True:
            adapter, pending = self._first_usable(
                pending, raise_if_none=last_error is None
            )
            if adapter is None:
                raise last_error
            try:
                return await adapter.generate(request)
            except AdapterError as e:
                if not (fallback and e.retryable):
                    raise
                logger.warning("model %s failed (%s); trying next", e.model, e.message)
                last_error = e

    # Builds the first usable adapter and returns it with the candidates after it.
    def _first_usable(self, specs, raise_if_none=True):
        skipped = []
        for index, spec in enumerate(specs):
            try:
                return self.build(spec), specs[index + 1 :]
            except AdapterConfigError as e:
                skipped.append(f"{spec.id}: {e.message}")
        if not raise_if_none:
            return None, []
        detail = "; ".join(skipped) or "no models are configured"
        raise _config_error(f"no usable model ({detail})")

    # Builds a selector from parsed catalog data (see llm_models.example.toml).
    @classmethod
    def from_dict(cls, data: dict) -> "ModelSelector":
        specs = [_parse_spec(entry) for entry in data.get("models", [])]
        return cls(specs, data.get("language_overrides"))


# Loads the model catalog from a TOML file. The path is the argument, else LLM_MODELS_PATH,
# else llm_models.toml in the backend folder. A missing file gives a selector with no models.
def load_selector(path: str | Path | None = None) -> ModelSelector:
    if path is None:
        backend_root = Path(__file__).resolve().parents[2]
        path = os.environ.get(LLM_MODELS_PATH_ENV) or backend_root / DEFAULT_CATALOG
    path = Path(path)
    if not path.is_file():
        return ModelSelector([])
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise _config_error(f"cannot read model catalog {path.name}: {e}") from None
    return ModelSelector.from_dict(data)


def _config_error(message: str) -> AdapterConfigError:
    return AdapterConfigError(message, provider="selector")


# Normalizes "En -> SW" to "en->sw"; a key without both languages is a config error.
def _pair_key(pair: str) -> str:
    source, arrow, target = str(pair).partition("->")
    source, target = source.strip().lower(), target.strip().lower()
    if not arrow or not source or not target:
        raise _config_error(
            f"language override key {pair!r} must look like 'en->sw' (source->target)"
        )
    return f"{source}->{target}"


# Turns one [[models]] table into a ModelSpec, rejecting missing or malformed fields.
def _parse_spec(entry) -> ModelSpec:
    if not isinstance(entry, dict):
        raise _config_error("each [[models]] entry must be a table")
    fields = dict(entry)
    parts = {k: fields.pop(k, None) for k in ("id", "provider", "model")}
    for key, value in parts.items():
        if not isinstance(value, str) or not value.strip():
            raise _config_error(f"model entry is missing a text value for {key!r}")
    tier = fields.pop("tier", 1)
    if isinstance(tier, bool) or not isinstance(tier, int):
        raise _config_error(f"{parts['id']}: tier must be an integer")
    prices = {
        k: fields.pop(k, None) for k in ("price_per_1m_input", "price_per_1m_output")
    }
    if parts["provider"] in UNPRICED_PROVIDERS:
        prices = {k: 0.0 if v is None else v for k, v in prices.items()}
    for key, value in prices.items():
        if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
            raise _config_error(f"{parts['id']}: {key} must be a number >= 0")
    return ModelSpec(
        **parts, tier=tier, **{k: float(v) for k, v in prices.items()}, config=fields
    )
