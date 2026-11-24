import asyncio
import zlib

import numpy as np
import pytest

import app.ai.comparison as legacy
from app.pipeline import MAX_TEXT_CHARS, ComparisonPipeline
from app.services import pipeline_comparison
from app.services.pipeline_comparison import perform_semantic_comparison

SOURCE = (
    "The cat sat on the mat. The dog chased the ball. "
    "Taxes were raised in spring. The sky was clear."
)
TARGET = (
    "The cat sat on a mat. The dog chased the ball quickly. "
    "Rain fell all night. The sky was clear."
)


# Embeds a sentence as hashed word counts, so similar sentences get similar vectors.
# crc32 keeps the vectors the same on every run.
class WordEmbedder:
    def encode(self, sentences):
        vectors = np.zeros((len(sentences), 256))
        for row, sentence in enumerate(sentences):
            for word in sentence.lower().replace(".", "").split():
                vectors[row, zlib.crc32(word.encode()) % 256] += 1.0
        return vectors


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    monkeypatch.setattr(legacy, "_get_model", lambda name: WordEmbedder())


# The sentence splitter keeps or drops the final full stop depending on whether the
# spaCy model is installed, so the tests compare sentences without it.
def bare(sentences):
    return [sentence.rstrip(".") for sentence in sentences]


def request(source=SOURCE, target=TARGET, threshold=0.6, model="fake-model"):
    return {
        "original_article_content": source,
        "translated_article_content": target,
        "original_language": "en",
        "translated_language": "en",
        "comparison_threshold": threshold,
        "model_name": model,
    }


@pytest.mark.unit
def test_pipeline_result_matches_the_old_engine():
    new = perform_semantic_comparison(request())["comparisons"][0]
    old = legacy.perform_semantic_comparison(request())["comparisons"][0]
    assert new["left_article_array"] == old["left_article_array"]
    assert new["right_article_array"] == old["right_article_array"]
    assert (
        new["left_article_missing_info_index"] == old["left_article_missing_info_index"]
    )
    assert (
        new["right_article_extra_info_index"] == old["right_article_extra_info_index"]
    )
    assert new["success"] is True
    assert new["score"] == pytest.approx(old["score"], abs=1e-3)
    assert [m["sentence"] for m in new["details"]["best_matches_ab"]] == [
        m["sentence"] for m in old["details"]["best_matches_ab"]
    ]
    assert [m["best_match"] for m in new["details"]["best_matches_ba"]] == [
        m["best_match"] for m in old["details"]["best_matches_ba"]
    ]
    assert len(new["details"]["top_matches"]) == len(old["details"]["top_matches"])


@pytest.mark.unit
def test_differences_are_the_sentences_without_a_match():
    entry = perform_semantic_comparison(request())["comparisons"][0]
    left, right = entry["left_article_array"], entry["right_article_array"]
    missing = [left[i] for i in entry["left_article_missing_info_index"]]
    extra = [right[i] for i in entry["right_article_extra_info_index"]]
    assert bare(missing) == ["Taxes were raised in spring"]
    assert bare(extra) == ["Rain fell all night"]


@pytest.mark.unit
def test_comparison_runs_through_the_pipeline(monkeypatch):
    calls = []
    run = ComparisonPipeline.run

    async def spy(self, source, target, strategies):
        calls.append([getattr(s, "name", s) for s in strategies])
        return await run(self, source, target, strategies)

    monkeypatch.setattr(ComparisonPipeline, "run", spy)
    perform_semantic_comparison(request())
    assert calls == [["semantic_similarity"]]


@pytest.mark.unit
def test_threshold_decides_which_sentences_are_missing():
    strict = perform_semantic_comparison(request(threshold=0.99))["comparisons"][0]
    loose = perform_semantic_comparison(request(threshold=0.1))["comparisons"][0]
    assert len(strict["left_article_missing_info_index"]) > len(
        loose["left_article_missing_info_index"]
    )


@pytest.mark.unit
def test_each_text_is_split_with_its_own_language(monkeypatch):
    seen = []
    real = pipeline_comparison.preprocess_input

    def spy(text, language):
        seen.append(language)
        return real(text, language)

    monkeypatch.setattr(pipeline_comparison, "preprocess_input", spy)
    body = request()
    body["translated_language"] = "fr"
    perform_semantic_comparison(body)
    assert seen == ["en", "fr"]


@pytest.mark.unit
def test_prototype_model_still_uses_the_old_engine(monkeypatch):
    monkeypatch.setattr(
        pipeline_comparison, "_legacy_comparison", lambda data: {"comparisons": ["old"]}
    )
    out = perform_semantic_comparison(request(model="similarity_prototype"))
    assert out == {"comparisons": ["old"]}


@pytest.mark.unit
@pytest.mark.parametrize("source", ["", "   \n "])
def test_empty_text_gives_no_comparisons(source):
    assert perform_semantic_comparison(request(source=source)) == {"comparisons": []}


@pytest.mark.unit
def test_text_over_the_pipeline_limit_falls_back_to_the_old_engine(monkeypatch):
    monkeypatch.setattr(
        pipeline_comparison, "_legacy_comparison", lambda data: {"comparisons": ["old"]}
    )
    long_text = "A fact. " * (MAX_TEXT_CHARS // 8 + 1)
    assert perform_semantic_comparison(request(source=long_text)) == {
        "comparisons": ["old"]
    }


@pytest.mark.unit
def test_a_failing_model_gives_no_comparisons(monkeypatch):
    def broken(name):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(legacy, "_get_model", broken)
    assert perform_semantic_comparison(request()) == {"comparisons": []}


@pytest.mark.unit
def test_works_when_called_from_a_running_event_loop():
    async def call():
        return perform_semantic_comparison(request())

    assert asyncio.run(call())["comparisons"]


@pytest.mark.unit
def test_v1_endpoint_response_keeps_its_format(client):
    response = client.post(
        "/symmetry/v1/articles/compare",
        json={
            "original_article_content": SOURCE,
            "translated_article_content": TARGET,
            "original_language": "en",
            "translated_language": "en",
            "similarity_threshold": 0.6,
            "model_name": "sentence-transformers/LaBSE",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert bare(d["sentence"] for d in data["missing_info"]) == [
        "Taxes were raised in spring"
    ]
    assert bare(d["sentence"] for d in data["extra_info"]) == ["Rain fell all night"]
    assert data["error_message"] is None
    assert data["comparisons"][0]["left_article_array"][0].startswith("The cat sat")


@pytest.mark.unit
def test_semantic_endpoint_response_keeps_its_format(client):
    response = client.post(
        "/symmetry/v1/comparison/semantic",
        json={
            "original_article_content": SOURCE,
            "translated_article_content": TARGET,
            "similarity_threshold": 0.6,
            "model_name": "sentence-transformers/LaBSE",
        },
    )
    assert response.status_code == 200
    missing = response.json()["missing_info"]
    assert bare(m["sentence"] for m in missing) == ["Taxes were raised in spring"]
