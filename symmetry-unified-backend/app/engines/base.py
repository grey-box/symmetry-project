from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# Provider-neutral input for one generation call.
@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    system_prompt: str | None = None
    max_tokens: int = 256
    temperature: float = 0.0
    timeout_s: float = 120.0

    def __post_init__(self):
        if not self.prompt or not self.prompt.strip():
            raise ValueError("prompt must not be empty")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")


# Provider-neutral output returned by every engine.
@dataclass(frozen=True)
class GenerationResult:
    text: str
    model: str
    provider: str
    latency_ms: float = 0.0
    usage: dict = field(default_factory=dict)


# The single interface the pipeline uses to call any text-generating engine.
class ModelAdapter(ABC):
    provider: str = ""

    def __init__(self, model_name: str, **config):
        self.model_name = model_name
        self.config = config

    # Runs one generation and raises an AdapterError subclass on any failure.
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult: ...

    # Returns True when the engine is ready to serve requests.
    async def health_check(self) -> bool:
        return True

    # Returns the model name this adapter was created with.
    def get_model_name(self) -> str:
        return self.model_name
