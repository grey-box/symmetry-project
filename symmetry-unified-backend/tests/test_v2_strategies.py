"""Tests for choosing a comparison strategy in an API v2 request."""

import pytest

from app.services.v2_responses import V2Failure
from app.services.v2_strategies import (
    MODE_DEFAULTS,
    PROFILES,
    available_strategies,
    choose_strategy,
)
from app.strategies import list_strategies


def _error(exc: pytest.ExceptionInfo) -> dict:
    [error] = exc.value.errors
    return error.model_dump()


@pytest.mark.unit
class TestChooseStrategy:
    def test_null_uses_the_mode_default(self):
        assert choose_strategy("llm_vs_wikipedia", None).id == "factual_consistency"

    def test_request_can_pick_another_strategy(self):
        profile = choose_strategy("llm_vs_wikipedia", "semantic_similarity")
        assert (profile.id, profile.engine, profile.score_basis) == (
            "semantic_similarity",
            "embedding",
            "cosine_similarity",
        )

    def test_llm_strategy_accepts_engines(self):
        profile = choose_strategy("llm_vs_wikipedia", "factual_consistency", ["a"])
        assert profile.engine == "llm"

    def test_unknown_strategy_lists_the_available_ones(self):
        with pytest.raises(V2Failure) as caught:
            choose_strategy("llm_vs_wikipedia", "style_check")
        error = _error(caught)
        assert error["code"] == "unsupported_strategy"
        assert "not available" in error["message"]
        assert error["details"]["available"] == [
            "factual_consistency",
            "semantic_similarity",
        ]

    def test_registered_strategies_without_a_profile_are_not_offered(self):
        assert "fake" in list_strategies()
        with pytest.raises(V2Failure):
            choose_strategy("llm_vs_wikipedia", "fake")

    def test_strategy_not_offered_for_the_mode(self):
        with pytest.raises(V2Failure) as caught:
            choose_strategy("text_vs_text", "semantic_similarity")
        assert "not available for mode 'text_vs_text'" in _error(caught)["message"]

    def test_mode_without_a_default_needs_a_strategy(self):
        with pytest.raises(V2Failure) as caught:
            choose_strategy("llm_vs_llm", None)
        assert _error(caught)["code"] == "unsupported_strategy"

    def test_embedding_strategy_cannot_run_on_catalog_engines(self):
        with pytest.raises(V2Failure) as caught:
            choose_strategy("llm_vs_wikipedia", "semantic_similarity", ["judge"])
        error = _error(caught)
        assert error["code"] == "unsupported_strategy"
        assert error["details"]["engines"] == ["judge"]


@pytest.mark.unit
class TestProfiles:
    def test_every_profile_is_a_registered_strategy(self):
        assert set(PROFILES) <= set(list_strategies())

    def test_every_mode_default_is_offered_for_its_mode(self):
        for mode, strategy in MODE_DEFAULTS.items():
            assert strategy in available_strategies(mode)

    def test_profiles_use_schema_score_bases(self):
        assert {p.score_basis for p in PROFILES.values()} <= {
            "cosine_similarity",
            "model_reported",
            "rule_based",
        }
