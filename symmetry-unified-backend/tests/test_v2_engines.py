"""Tests for resolving API v2 engine ids against the model catalog."""

import pytest

from app.engines.selection import ModelSelector, ModelSpec
from app.services.v2_engines import (
    CatalogEngineResolver,
    NoEngineError,
    UnknownEngineError,
)


def _local(spec_id: str, base_url: str = "http://localhost:11434/v1") -> ModelSpec:
    return ModelSpec(
        id=spec_id,
        provider="local_slm",
        model=f"{spec_id}-model",
        config={"base_url": base_url},
    )


def _cloud(spec_id: str, price: float) -> ModelSpec:
    return ModelSpec(
        id=spec_id,
        provider="cloud_llm",
        model=f"{spec_id}-model",
        price_per_1m_input=price,
        price_per_1m_output=price,
        config={
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_key_env": "SYMMETRY_TEST_UNSET_KEY",
        },
    )


@pytest.fixture(autouse=True)
def _no_test_key(monkeypatch):
    monkeypatch.delenv("SYMMETRY_TEST_UNSET_KEY", raising=False)


@pytest.mark.unit
class TestCatalogEngineResolver:
    def test_default_is_the_cheapest_usable_engine(self):
        resolver = CatalogEngineResolver(
            ModelSelector([_cloud("cloud", 0.0), _local("local")])
        )
        # The cloud model sorts first (same price, same tier, "cloud" < "local"),
        # but its key is missing, so the local one is chosen.
        [engine] = resolver.resolve([])
        assert engine.id == "local"
        assert engine.type == "local_slm"
        assert engine.model == "local-model"
        assert engine.provider == "localhost"
        assert engine.adapter is not None

    def test_no_usable_engine_raises(self):
        resolver = CatalogEngineResolver(ModelSelector([_cloud("cloud", 1.0)]))
        with pytest.raises(NoEngineError, match="SYMMETRY_TEST_UNSET_KEY"):
            resolver.resolve([])

    def test_empty_catalog_raises(self):
        with pytest.raises(NoEngineError, match="no engines"):
            CatalogEngineResolver(ModelSelector([])).resolve([])

    def test_named_engines_keep_request_order_without_duplicates(self):
        resolver = CatalogEngineResolver(
            ModelSelector([_local("a"), _local("b", "http://127.0.0.1:8080/v1")])
        )
        engines = resolver.resolve(["b", "a", "b"])
        assert [e.id for e in engines] == ["b", "a"]
        assert engines[0].provider == "127.0.0.1"

    def test_named_engine_that_cannot_be_built_carries_its_error(self):
        resolver = CatalogEngineResolver(ModelSelector([_cloud("cloud", 1.0)]))
        [engine] = resolver.resolve(["cloud"])
        assert engine.adapter is None
        assert "SYMMETRY_TEST_UNSET_KEY" in engine.error.message
        assert engine.provider == "integrate.api.nvidia.com"

    def test_unknown_engine_ids_are_rejected(self):
        resolver = CatalogEngineResolver(ModelSelector([_local("a")]))
        with pytest.raises(UnknownEngineError) as caught:
            resolver.resolve(["a", "nope"])
        assert caught.value.engine_ids == ["nope"]
        assert caught.value.available == ["a"]

    def test_test_only_providers_are_not_engines(self):
        fake = ModelSpec(id="fake", provider="fake", model="echo")
        resolver = CatalogEngineResolver(ModelSelector([fake]))
        with pytest.raises(UnknownEngineError):
            resolver.resolve(["fake"])
        with pytest.raises(NoEngineError):
            resolver.resolve([])
