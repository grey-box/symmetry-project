"""Which comparison strategies API v2 requests can choose, and how each is served.

A request picks a strategy with the ``strategy`` field; ``null`` means the
default for its mode. The routes never change: a new strategy is offered by
registering it in ``app.strategies`` and adding a ``StrategyProfile`` here.

Strategies registered without a profile (such as the ``fake`` test strategy)
are not offered through the API.
"""

from dataclasses import dataclass

from app.services.v2_responses import fail
from app.strategies import list_strategies


# How the API serves one strategy.
#   engine       "llm" for strategies that call a model adapter from the catalog,
#                "embedding" for strategies that use the server's embedding model
#   score_basis  what the result's scores mean (schema section 6)
#   modes        comparison modes the strategy can serve
#   description  one line for API users, shown in the OpenAPI docs
@dataclass(frozen=True)
class StrategyProfile:
    id: str
    engine: str
    score_basis: str
    modes: tuple[str, ...]
    description: str


PROFILES: dict[str, StrategyProfile] = {
    profile.id: profile
    for profile in (
        StrategyProfile(
            id="factual_consistency",
            engine="llm",
            score_basis="model_reported",
            modes=("llm_vs_wikipedia",),
            description=(
                "A language model labels each statement supported, contradicted "
                "or not found, with its confidence and a quoted passage."
            ),
        ),
        StrategyProfile(
            id="semantic_similarity",
            engine="embedding",
            score_basis="cosine_similarity",
            modes=("llm_vs_wikipedia",),
            description=(
                "An embedding model finds the closest article sentence to each "
                "statement. Fast and needs no API key, but it measures similar "
                "meaning, not truth: it never reports contradicted."
            ),
        ),
    )
}

# Strategy used when a request leaves strategy null.
MODE_DEFAULTS: dict[str, str] = {"llm_vs_wikipedia": "factual_consistency"}


# Ids of the strategies a mode offers: profiled, registered, and serving the mode.
def available_strategies(mode: str) -> list[str]:
    registered = set(list_strategies())
    return sorted(
        sid for sid, p in PROFILES.items() if sid in registered and mode in p.modes
    )


# Returns the profile for the requested strategy, or the mode's default. Raises a
# V2Failure (422 unsupported_strategy) when the strategy is unknown, not offered for
# the mode, or cannot be served by the requested engines.
def choose_strategy(
    mode: str, requested: str | None, engine_ids: list[str] | None = None
) -> StrategyProfile:
    available = available_strategies(mode)
    strategy = requested or MODE_DEFAULTS.get(mode)
    details = {"strategy": strategy, "available": available}
    if strategy is None or strategy not in available:
        if (
            strategy is not None
            and strategy in PROFILES
            and strategy in list_strategies()
        ):
            reason = f"Strategy '{strategy}' is not available for mode '{mode}'."
        else:
            reason = f"Strategy '{strategy}' is not available."
        raise fail(
            "unsupported_strategy",
            f"{reason} Available for {mode}: {', '.join(available) or 'none'}.",
            details=details,
        )
    profile = PROFILES[strategy]
    if profile.engine == "embedding" and engine_ids:
        # Catalog engines are language models; they cannot compute embeddings.
        raise fail(
            "unsupported_strategy",
            f"Strategy '{strategy}' uses the server's embedding model and cannot run "
            f"on the requested engines ({', '.join(engine_ids)}). Leave engines empty.",
            details={**details, "engines": list(engine_ids)},
        )
    return profile
