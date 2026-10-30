from . import fake  # noqa: F401  (registers the "fake" adapter)
from . import local_slm  # noqa: F401  (registers the "local_slm" adapter)
from .base import GenerationRequest, GenerationResult, ModelAdapter
from .errors import (
    AdapterConfigError,
    AdapterError,
    AdapterRequestError,
    AdapterResponseError,
    AdapterTimeoutError,
    UnknownAdapterError,
)
from .registry import get_adapter, list_adapters, register_adapter

__all__ = [
    "AdapterConfigError",
    "AdapterError",
    "AdapterRequestError",
    "AdapterResponseError",
    "AdapterTimeoutError",
    "GenerationRequest",
    "GenerationResult",
    "ModelAdapter",
    "UnknownAdapterError",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
