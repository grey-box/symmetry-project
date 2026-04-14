import pytest
import anyio
import torch
from types import SimpleNamespace

from app.models.extraction import engine as fact_extraction


class DummyTokenizer:
    def __init__(self):
        self.pad_token_id = 0
        self.eos_token_id = 1
        self.pad_token = None

    def __call__(self, prompt, return_tensors=None, truncation=None):
        return {"input_ids": torch.tensor([[1]])}

    def decode(self, output, skip_special_tokens=True):
        return "Extracted fact"


class DummyModel:
    def __init__(self):
        self.config = SimpleNamespace(pad_token_id=None)
        self.device = "cpu"

    def eval(self):
        return self

    def to(self, device):
        self.device = device
        return self

    def generate(self, **kwargs):
        return torch.tensor([[1]])


class DummyConfig:
    def __init__(self, is_encoder_decoder=True):
        self.is_encoder_decoder = is_encoder_decoder


@pytest.fixture(autouse=True)
def patch_model_loading(monkeypatch):
    monkeypatch.setattr(
        fact_extraction,
        "AutoTokenizer",
        SimpleNamespace(from_pretrained=lambda model_name: DummyTokenizer()),
    )
    monkeypatch.setattr(
        fact_extraction,
        "AutoConfig",
        SimpleNamespace(
            from_pretrained=lambda model_name: DummyConfig(is_encoder_decoder=True)
        ),
    )
    monkeypatch.setattr(
        fact_extraction,
        "AutoModelForSeq2SeqLM",
        SimpleNamespace(from_pretrained=lambda model_name: DummyModel()),
    )
    monkeypatch.setattr(
        fact_extraction,
        "AutoModelForCausalLM",
        SimpleNamespace(from_pretrained=lambda model_name: DummyModel()),
    )
    monkeypatch.setattr(fact_extraction.torch.cuda, "is_available", lambda: False)
    yield
    fact_extraction._model_cache.clear()


@pytest.mark.anyio
async def test_model_cache_eviction_lru_order(monkeypatch):
    monkeypatch.setattr(
        fact_extraction,
        "get_model_config",
        lambda model_id: {
            "model_name": model_id,
            "prompt_style": "plain",
            "repetition_penalty": 1.0,
        },
    )

    # Confirm the configured cache size is used.
    assert fact_extraction.MODEL_CACHE_MAX_SIZE == 3

    # Warm up the cache with three models.
    await fact_extraction.extract_facts("text A", "model_a")
    await fact_extraction.extract_facts("text B", "model_b")
    await fact_extraction.extract_facts("text C", "model_c")

    assert list(fact_extraction._model_cache.keys()) == [
        "model_a",
        "model_b",
        "model_c",
    ]

    # Access model_a again to update its recency.
    await fact_extraction.extract_facts("text A", "model_a")
    assert list(fact_extraction._model_cache.keys()) == [
        "model_b",
        "model_c",
        "model_a",
    ]

    # Adding a fourth model should evict the least recently used model_b.
    await fact_extraction.extract_facts("text D", "model_d")
    assert list(fact_extraction._model_cache.keys()) == [
        "model_c",
        "model_a",
        "model_d",
    ]
    assert "model_b" not in fact_extraction._model_cache


@pytest.mark.anyio
async def test_model_cache_reuses_cached_model(monkeypatch):
    monkeypatch.setattr(
        fact_extraction,
        "get_model_config",
        lambda model_id: {
            "model_name": model_id,
            "prompt_style": "plain",
            "repetition_penalty": 1.0,
        },
    )

    await fact_extraction.extract_facts("text", "model_x")
    first_model = fact_extraction._model_cache["model_x"][0]

    await fact_extraction.extract_facts("text", "model_x")
    second_model = fact_extraction._model_cache["model_x"][0]

    assert first_model is second_model
