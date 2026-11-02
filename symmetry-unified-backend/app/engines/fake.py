from .base import GenerationRequest, GenerationResult, ModelAdapter
from .errors import AdapterTimeoutError
from .registry import register_adapter


# Offline test engine that echoes the prompt, returns a fixed reply, or fails on demand.
@register_adapter("fake")
class FakeAdapter(ModelAdapter):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.config.get("fail") == "timeout":
            raise AdapterTimeoutError(
                "simulated timeout", provider=self.provider, model=self.model_name
            )
        text = self.config.get("reply", f"echo: {request.prompt}")
        return GenerationResult(
            text=text, model=self.model_name, provider=self.provider, latency_ms=0.0
        )
