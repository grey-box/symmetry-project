from .base import ModelAdapter
from .errors import UnknownAdapterError

_ADAPTERS: dict[str, type[ModelAdapter]] = {}


# Class decorator that registers an adapter under a provider name.
def register_adapter(name: str):
    def decorator(cls: type[ModelAdapter]) -> type[ModelAdapter]:
        if not issubclass(cls, ModelAdapter):
            raise TypeError(f"{cls.__name__} must subclass ModelAdapter")
        if name in _ADAPTERS and _ADAPTERS[name] is not cls:
            raise ValueError(f"adapter '{name}' is already registered")
        cls.provider = name
        _ADAPTERS[name] = cls
        return cls

    return decorator


# Builds the adapter registered for a provider or raises UnknownAdapterError.
def get_adapter(provider: str, model_name: str, **config) -> ModelAdapter:
    try:
        cls = _ADAPTERS[provider]
    except KeyError:
        raise UnknownAdapterError(
            f"unknown provider; available: {sorted(_ADAPTERS)}",
            provider=provider,
            model=model_name,
        ) from None
    return cls(model_name, **config)


# Returns the sorted names of all registered adapters.
def list_adapters():
    return sorted(_ADAPTERS)
