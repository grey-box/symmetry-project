import asyncio

import pytest

from app.pipeline import (
    LABEL_WEIGHTS,
    SCHEMA_LABELS,
    ComparisonPipeline,
    Difference,
    RankingConfig,
    TextInput,
    keep_order,
    rank_differences,
    score_difference,
)
from app.strategies import (
    ComparisonStrategy,
    Finding,
    StrategyResult,
    register_strategy,
    registry,
)


# Builds a difference with only the fields a test cares about.
def diff(schema_label="contradicted", confidence=1.0, span="x" * 200, **kwargs):
    return Difference(
        strategy="s",
        label=schema_label,
        schema_label=schema_label,
        confidence=confidence,
        source_span=span,
        **kwargs,
    )


# Every API v2 label has a weight, so none falls back silently.
@pytest.mark.unit
def test_every_schema_label_has_a_weight():
    assert set(LABEL_WEIGHTS) == set(SCHEMA_LABELS)


# A contradiction ranks above a missing statement of equal confidence.
@pytest.mark.unit
def test_label_severity_orders_differences():
    labels = ["unverifiable", "partial", "not_found", "contradicted"]
    ranked = rank_differences([diff(label) for label in labels])
    assert [d.schema_label for d in ranked] == [
        "contradicted",
        "not_found",
        "partial",
        "unverifiable",
    ]


# Higher confidence ranks higher for the same label.
@pytest.mark.unit
def test_confidence_orders_differences():
    ranked = rank_differences([diff(confidence=0.3), diff(confidence=0.9)])
    assert [d.confidence for d in ranked] == [0.9, 0.3]


# A difference covering more text ranks higher than a tiny one.
@pytest.mark.unit
def test_longer_spans_rank_higher():
    ranked = rank_differences([diff(span="a"), diff(span="a" * 200)])
    assert [len(d.source_span) for d in ranked] == [200, 1]


# Ranks start at 1, significance is filled in, and the order is descending.
@pytest.mark.unit
def test_ranks_and_significance_are_assigned():
    ranked = rank_differences([diff(confidence=0.2), diff(confidence=0.8), diff()])
    assert [d.rank for d in ranked] == [1, 2, 3]
    scores = [d.significance for d in ranked]
    assert scores == sorted(scores, reverse=True) and scores[0] == 1.0


# Equal scores keep the order the strategies reported them in.
@pytest.mark.unit
def test_ties_keep_original_order():
    first, second = diff(message="first"), diff(message="second")
    assert [d.message for d in rank_differences([first, second])] == ["first", "second"]


# Findings with no confidence use the configured default.
@pytest.mark.unit
def test_missing_confidence_uses_default():
    config = RankingConfig(unknown_confidence=0.5)
    assert score_difference(diff(confidence=None), config) == pytest.approx(0.5)


# Supported statements are not differences, so they are left out.
@pytest.mark.unit
def test_supported_statements_are_left_out():
    assert rank_differences([diff("supported")]) == []
    ranked = rank_differences([diff("supported"), diff("partial")])
    assert [d.schema_label for d in ranked] == ["partial"]


# Custom label weights change the order.
@pytest.mark.unit
def test_custom_weights_change_the_order():
    config = RankingConfig(label_weights={"partial": 0.9, "not_found": 0.1})
    ranked = rank_differences([diff("not_found"), diff("partial")], config)
    assert [d.schema_label for d in ranked] == ["partial", "not_found"]


# Spans may be missing, and the target span counts as well.
@pytest.mark.unit
def test_span_less_and_target_span_differences():
    config = RankingConfig()
    bare = Difference(
        strategy="s", label="contradicted", schema_label="contradicted", confidence=1.0
    )
    target_only = Difference(
        strategy="s",
        label="contradicted",
        schema_label="contradicted",
        confidence=1.0,
        target_span="y" * 200,
    )
    assert score_difference(bare, config) == pytest.approx(0.5)
    assert score_difference(target_only, config) == pytest.approx(1.0)


# Ranking does not change the input list or its items.
@pytest.mark.unit
def test_input_is_not_mutated():
    original = [diff(confidence=0.2), diff(confidence=0.9)]
    rank_differences(original)
    assert [d.rank for d in original] == [None, None]
    assert [d.significance for d in original] == [0.0, 0.0]


# An empty list ranks to an empty list.
@pytest.mark.unit
def test_empty_input():
    assert rank_differences([]) == []


# Invalid settings are rejected.
@pytest.mark.unit
def test_config_validation():
    with pytest.raises(ValueError):
        RankingConfig(long_span_chars=0)
    with pytest.raises(ValueError):
        RankingConfig(unknown_confidence=1.5)
    with pytest.raises(ValueError):
        RankingConfig(label_weights={"made_up": 0.5})
    with pytest.raises(ValueError):
        RankingConfig(label_weights={"partial": 2.0})


# The pipeline returns differences in ranked order by default, whatever labels the
# strategy uses, because the ranking works on the mapped API v2 label.
@pytest.mark.unit
def test_pipeline_returns_ranked_differences(monkeypatch):
    monkeypatch.setattr(registry, "_STRATEGIES", dict(registry._STRATEGIES))

    @register_strategy("mixed")
    class Mixed(ComparisonStrategy):
        async def compare(self, request):
            findings = [
                Finding(label="missing_in_target", confidence=0.4, source_span="a"),
                Finding(label="contradicted", confidence=0.9, source_span="b" * 80),
            ]
            return StrategyResult(strategy=self.name, findings=findings)

    result = asyncio.run(
        ComparisonPipeline().run(TextInput("one"), TextInput("two"), ["mixed"])
    )
    assert [d.schema_label for d in result.differences] == [
        "contradicted",
        "not_found",
    ]
    assert [d.rank for d in result.differences] == [1, 2]


# A pipeline built with keep_order still returns the strategy order.
@pytest.mark.unit
def test_pipeline_can_opt_out_of_ranking():
    result = asyncio.run(
        ComparisonPipeline(ranker=keep_order).run(
            TextInput("a b c"), TextInput("a"), ["fake"]
        )
    )
    assert [d.rank for d in result.differences] == [None, None]
