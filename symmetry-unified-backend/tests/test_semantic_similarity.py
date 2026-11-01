import asyncio

import pytest

from app.pipeline import ComparisonPipeline, StrategySpec, TextInput
from app.strategies import (
    StrategyConfigError,
    StrategyExecutionError,
    StrategyInput,
    get_strategy,
    list_strategies,
)
from app.strategies.text import split_sentences

TOPICS = ["cat", "dog", "sky", "tax"]


# Embeds a sentence as a one-hot vector for the first topic word it contains.
class TopicEmbedder:
    def encode(self, sentences):
        vectors = []
        for sentence in sentences:
            vector = [0.0] * len(TOPICS)
            for i, topic in enumerate(TOPICS):
                if topic in sentence.lower():
                    vector[i] = 1.0
                    break
            vectors.append(vector)
        return vectors


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


# Builds the strategy with the topic embedder.
def make(**config):
    return get_strategy("semantic_similarity", embedder=TopicEmbedder(), **config)


# Compares two texts with the topic embedder.
def compare(source, target, **config):
    return run(make(**config).compare(StrategyInput(source, target)))


@pytest.mark.unit
def test_split_sentences_keeps_exact_text():
    text = "The cat sat. The dog ran!\nIs the sky blue? Yes."
    parts = split_sentences(text)
    assert parts == ["The cat sat.", "The dog ran!", "Is the sky blue?", "Yes."]
    assert all(part in text for part in parts)


@pytest.mark.unit
def test_split_sentences_handles_cjk_and_blank_text():
    assert split_sentences("猫がいる。犬もいる。") == ["猫がいる。", "犬もいる。"]
    assert split_sentences("  \n ") == []


@pytest.mark.unit
def test_registered():
    assert "semantic_similarity" in list_strategies()


@pytest.mark.unit
def test_identical_texts_score_one_with_no_findings():
    result = compare("The cat sat. The dog ran.", "The cat sat. The dog ran.")
    assert result.strategy == "semantic_similarity"
    assert result.score == pytest.approx(1.0)
    assert result.findings == []
    assert len(result.details["alignments"]) == 2


@pytest.mark.unit
def test_unmatched_sentences_are_reported_both_ways():
    result = compare("The cat sat. Taxes rose.", "The cat slept. The sky is blue.")
    labels = {f.label: f for f in result.findings}
    assert set(labels) == {"no_match_in_target", "no_match_in_source"}
    assert labels["no_match_in_target"].source_span == "Taxes rose."
    assert labels["no_match_in_source"].target_span == "The sky is blue."
    assert labels["no_match_in_target"].confidence == pytest.approx(1.0)
    assert 0.0 < result.score < 1.0


@pytest.mark.unit
def test_alignments_point_at_best_match():
    result = compare("The dog ran. The cat sat.", "The cat slept. The dog barked.")
    pairs = {
        (a["source_index"], a["target_index"]) for a in result.details["alignments"]
    }
    assert pairs == {(0, 1), (1, 0)}


@pytest.mark.unit
def test_threshold_controls_findings():
    # Vectors that overlap partially: similarity between "cat" and "dog" is 0.
    strict = compare("The cat sat.", "The dog ran.", threshold=0.0)
    assert strict.findings == []
    default = compare("The cat sat.", "The dog ran.")
    assert len(default.findings) == 2


@pytest.mark.unit
def test_default_threshold_comes_from_settings():
    from app.core.settings import SIMILARITY_THRESHOLD

    assert make().threshold == SIMILARITY_THRESHOLD


@pytest.mark.unit
@pytest.mark.parametrize("bad", [-0.1, 1.5, "high", True])
def test_bad_threshold_rejected(bad):
    with pytest.raises(StrategyConfigError):
        make(threshold=bad)


@pytest.mark.unit
def test_zero_vectors_do_not_crash():
    result = compare("Nothing here.", "Nothing there.")
    assert result.score == 0.0
    assert len(result.findings) == 2


@pytest.mark.unit
def test_embedder_failure_becomes_execution_error():
    class Broken:
        def encode(self, sentences):
            raise RuntimeError("boom")

    strategy = get_strategy("semantic_similarity", embedder=Broken())
    with pytest.raises(StrategyExecutionError):
        run(strategy.compare(StrategyInput("A cat.", "A dog.")))


@pytest.mark.unit
def test_wrong_embedding_shape_becomes_execution_error():
    class Short:
        def encode(self, sentences):
            return [[1.0, 0.0]]

    strategy = get_strategy("semantic_similarity", embedder=Short())
    with pytest.raises(StrategyExecutionError):
        run(strategy.compare(StrategyInput("A cat. A dog.", "A sky.")))


@pytest.mark.unit
def test_custom_splitter_is_used():
    result = compare("cat;dog", "cat;dog", splitter=lambda t: t.split(";"))
    assert len(result.details["alignments"]) == 2


@pytest.mark.integration
def test_runs_inside_pipeline_with_offsets():
    source = "The cat sat. Taxes rose."
    spec = StrategySpec("semantic_similarity", {"embedder": TopicEmbedder()})
    result = run(
        ComparisonPipeline().run(TextInput(source), TextInput("The cat slept."), [spec])
    )
    assert result.errors == []
    difference = result.differences[0]
    assert difference.source_span == "Taxes rose."
    start, end = difference.source_range
    assert source[start:end] == "Taxes rose."


@pytest.mark.slow
@pytest.mark.external
def test_real_model_paraphrase_scores_higher_than_unrelated():
    pytest.importorskip("sentence_transformers")
    strategy = get_strategy("semantic_similarity")
    same = run(
        strategy.compare(
            StrategyInput(
                "The cat is sleeping on the sofa.", "A cat naps on the couch."
            )
        )
    )
    different = run(
        strategy.compare(
            StrategyInput(
                "The cat is sleeping on the sofa.", "Interest rates rose in March."
            )
        )
    )
    assert same.score > different.score
