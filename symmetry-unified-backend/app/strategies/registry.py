from collections.abc import Callable
from typing import Any

from .base import ComparisonStrategy
from .errors import StrategyConfigError, UnknownStrategyError

_STRATEGIES: dict[str, type[ComparisonStrategy]] = {}


# Class decorator that registers a strategy under a name.
def register_strategy(
    name: str,
) -> Callable[[type[ComparisonStrategy]], type[ComparisonStrategy]]:
    def decorator(cls: type[ComparisonStrategy]) -> type[ComparisonStrategy]:
        if not (isinstance(cls, type) and issubclass(cls, ComparisonStrategy)):
            raise TypeError(f"{cls!r} must subclass ComparisonStrategy")
        if name in _STRATEGIES and _STRATEGIES[name] is not cls:
            raise ValueError(f"strategy '{name}' is already registered")
        cls.name = name
        _STRATEGIES[name] = cls
        return cls

    return decorator


# Builds the strategy registered under a name or raises a StrategyError.
def get_strategy(name: str, **config: Any) -> ComparisonStrategy:
    try:
        cls = _STRATEGIES[name]
    except KeyError:
        raise UnknownStrategyError(
            f"unknown strategy; available: {sorted(_STRATEGIES)}", strategy=name
        ) from None
    missing = [key for key in cls.requires if key not in config]
    if missing:
        raise StrategyConfigError(
            f"missing required settings: {missing}", strategy=name
        )
    return cls(**config)


# Returns the sorted names of all registered strategies.
def list_strategies() -> list[str]:
    return sorted(_STRATEGIES)
