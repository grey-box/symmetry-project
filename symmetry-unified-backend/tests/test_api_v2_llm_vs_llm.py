"""Tests for POST /symmetry/v2/compare/llm-vs-llm.

The embedding model is replaced by a deterministic bag-of-words embedder through
the endpoint's dependency, so these tests run offline. Every response is
validated against the published JSON Schema (docs/api-v2/api-v2-schema.json)
and the cross-field rules of the schema document.
"""

import json
import math
import re

import pytest
from jsonschema import Draft202012Validator

from app.main import app
from app.routers.api_v2 import get_llm_vs_llm_service
from app.services.llm_vs_llm import LlmVsLlmService
from tests.api_v2_examples import SCHEMA_DOC

PATH = "/symmetry/v2/compare/llm-vs-llm"

SCHEMA = json.loads(
    (SCHEMA_DOC.parent / "api-v2-schema.json").read_text(encoding="utf-8")
)

ANSWER_A = "The Eiffel Tower was completed in 1889. It is in Paris."
ANSWER_B = "The Eiffel Tower was completed in 1889. It was built for the World's Fair."


# Bag-of-words vectors over the words of each call: identical sentences score 1.0,
# sentences sharing no words 0.0. Fails on any sentence containing "boom".
class WordEmbedder:
    def encode(self, sentences):
        if any("boom" in s for s in sentences):
            raise RuntimeError("model file missing")
        tokens = [re.findall(r"\w+", s.lower()) for s in sentences]
        vocabulary = {
            w: i for i, w in enumerate(sorted({w for t in tokens for w in t}))
        }
        vectors = []
        for words in tokens:
            vector = [0.0] * len(vocabulary)
            for word in words:
                vector[vocabulary[word]] += 1.0
            vectors.append(vector)
        return vectors


# Cosine similarity of two sentences under WordEmbedder, for expected values.
def _cosine(a: str, b: str) -> float:
    wa, wb = re.findall(r"\w+", a.lower()), re.findall(r"\w+", b.lower())
    dot = sum(wa.count(w) * wb.count(w) for w in set(wa) & set(wb))
    norm = math.sqrt(sum(wa.count(w) ** 2 for w in set(wa))) * math.sqrt(
        sum(wb.count(w) ** 2 for w in set(wb))
    )
    return dot / norm


def _request(*answers: str, **overrides) -> dict:
    body = {
        "mode": "llm_vs_llm",
        "prompt": "Tell me about the Eiffel Tower.",
        "sources": [
            {"id": source_id, "kind": "llm_output", "language": "en", "text": text}
            for source_id, text in zip("abcdef", answers, strict=False)
        ],
    }
    body.update(overrides)
    return body


@pytest.fixture
def use_service():
    def install():
        service = LlmVsLlmService(
            strategy_config={
                "semantic_similarity": {
                    "embedder": WordEmbedder(),
                    "model_name": "test-embedder",
                }
            }
        )
        app.dependency_overrides[get_llm_vs_llm_service] = lambda: service

    install()
    yield
    app.dependency_overrides.pop(get_llm_vs_llm_service, None)


def _validator(definition: str) -> Draft202012Validator:
    return Draft202012Validator(
        {
            "$schema": SCHEMA["$schema"],
            "$defs": SCHEMA["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
    )


# Checks a 200 response against the JSON Schema and the document's cross-field rules.
def _check_comparison(response) -> dict:
    assert response.status_code == 200, response.text
    body = response.json()
    _validator("ComparisonResponse").validate(body)
    assert response.headers["X-Request-ID"] == body["request_id"]
    texts = {s["id"]: s["text"] for s in body["sources"]}
    for result in body["results"]:
        ids = [s["id"] for s in result["statements"]]
        assert len(ids) == len(set(ids))
        for statement in result["statements"]:
            assert statement["source_id"] in result["source_ids"]
            text = texts[statement["source_id"]]
            if text is not None:
                span = statement["span"]
                assert text[span["start"] : span["end"]] == statement["text"]
            assert statement["confidence"] is None  # cosine_similarity results
            for evidence in statement["evidence"]:
                assert evidence["statement_id"] in ids
        for alignment in result["alignments"]:
            refs = [alignment["source_ref"], alignment["target_ref"]]
            assert all(ref is None or ref in ids for ref in refs)
        alignment_ids = [a["id"] for a in result["alignments"]]
        assert len(alignment_ids) == len(set(alignment_ids))
    if body["status"] == "success":
        assert body["errors"] == []
    else:
        assert body["errors"]
    return body


def _check_error(response, status_code: int) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    _validator("ErrorResponse").validate(body)
    assert body["status"] == "failed"
    assert response.headers["X-Request-ID"] == body["request_id"]
    return body


@pytest.mark.unit
@pytest.mark.usefixtures("use_service")
class TestComparison:
    def test_labels_both_answers_against_each_other(self, client):
        body = _check_comparison(client.post(PATH, json=_request(ANSWER_A, ANSWER_B)))

        assert body["status"] == "success"
        assert (body["mode"], body["strategy"]) == ("llm_vs_llm", "semantic_similarity")
        assert body["prompt"] == "Tell me about the Eiffel Tower."
        [result] = body["results"]
        assert result["source_ids"] == ["a", "b"]
        assert result["direction"] == "both"
        assert result["score_basis"] == "cosine_similarity"
        assert result["engine"] == {
            "id": "embedding-default",
            "type": "embedding",
            "provider": "local",
            "model": "test-embedder",
            "fallback_from": None,
        }
        statements = {s["id"]: s for s in result["statements"]}
        assert [(i, s["label"]) for i, s in statements.items()] == [
            ("a-0", "supported"),
            ("a-1", "not_found"),
            ("b-0", "supported"),
            ("b-1", "not_found"),
        ]
        assert statements["a-0"]["best_match_similarity"] == 1.0
        assert statements["a-1"]["best_match_similarity"] == pytest.approx(
            _cosine("It is in Paris.", "The Eiffel Tower was completed in 1889."),
            abs=1e-4,
        )

    def test_matching_sentences_cite_each_other(self, client):
        body = _check_comparison(client.post(PATH, json=_request(ANSWER_A, ANSWER_B)))
        statements = {s["id"]: s for s in body["results"][0]["statements"]}
        assert statements["a-0"]["evidence"] == [
            {
                "kind": "counterpart_statement",
                "source_id": "b",
                "statement_id": "b-0",
                "text": "The Eiffel Tower was completed in 1889.",
                "url": None,
            }
        ]
        assert statements["b-0"]["evidence"][0]["statement_id"] == "a-0"
        # A sentence the other answer does not say cites nothing.
        assert statements["a-1"]["evidence"] == []

    def test_alignments_highlight_the_disagreements(self, client):
        body = _check_comparison(client.post(PATH, json=_request(ANSWER_A, ANSWER_B)))
        alignments = [
            (a["source_ref"], a["target_ref"], a["category"], a["similarity"])
            for a in body["results"][0]["alignments"]
        ]
        assert alignments == [
            ("a-0", "b-0", "equal", 1.0),
            ("a-1", None, "missing", None),
            (None, "b-1", "added", None),
        ]

    def test_overall_score_is_the_mean_similarity(self, client):
        body = _check_comparison(client.post(PATH, json=_request(ANSWER_A, ANSWER_B)))
        [result] = body["results"]
        scores = [s["best_match_similarity"] for s in result["statements"]]
        assert result["overall_score"] == pytest.approx(
            sum(scores) / len(scores), abs=1e-3
        )

    def test_close_sentences_are_partial_and_modified(self, client):
        request = _request(
            "The tower is 330 metres tall.",
            "The tower is 400 metres tall.",
            options={"similarity_threshold": 0.9, "partial_threshold": 0.7},
        )
        body = _check_comparison(client.post(PATH, json=request))
        [result] = body["results"]
        assert [s["label"] for s in result["statements"]] == ["partial", "partial"]
        assert result["statements"][0]["best_match_similarity"] == pytest.approx(
            5 / 6, abs=1e-4
        )
        assert [
            (a["source_ref"], a["target_ref"], a["category"])
            for a in result["alignments"]
        ] == [("a-0", "b-0", "modified")]

    def test_three_answers_give_three_pairs(self, client):
        third = "The Eiffel Tower was completed in 1889. It is painted every 7 years."
        body = _check_comparison(
            client.post(PATH, json=_request(ANSWER_A, ANSWER_B, third))
        )
        assert [r["source_ids"] for r in body["results"]] == [
            ["a", "b"],
            ["a", "c"],
            ["b", "c"],
        ]
        assert [s["id"] for s in body["sources"]] == ["a", "b", "c"]

    def test_options_can_leave_out_text_and_evidence(self, client):
        request = _request(
            ANSWER_A,
            ANSWER_B,
            options={"include_source_text": False, "include_evidence": False},
        )
        body = _check_comparison(client.post(PATH, json=request))
        assert [s["text"] for s in body["sources"]] == [None, None]
        assert all(s["evidence"] == [] for s in body["results"][0]["statements"])


@pytest.mark.unit
@pytest.mark.usefixtures("use_service")
class TestFailures:
    def test_one_failing_pair_gives_a_partial_response(self, client):
        body = _check_comparison(
            client.post(PATH, json=_request(ANSWER_A, ANSWER_B, "Kaboom happened."))
        )
        assert body["status"] == "partial"
        assert [(r["source_ids"], r["status"]) for r in body["results"]] == [
            (["a", "b"], "ok"),
            (["a", "c"], "failed"),
            (["b", "c"], "failed"),
        ]
        failed = body["results"][1]
        assert failed["statements"] == [] and failed["alignments"] == []
        assert {tuple(e["details"]["source_ids"]) for e in body["errors"]} == {
            ("a", "c"),
            ("b", "c"),
        }
        assert all(
            (e["code"], e["scope"], e["engine_id"])
            == ("engine_unavailable", "engine", "embedding-default")
            for e in body["errors"]
        )

    def test_no_comparable_pair_returns_503(self, client):
        body = _check_error(client.post(PATH, json=_request(ANSWER_A, "boom.")), 503)
        assert body["errors"][0]["code"] == "engine_unavailable"


@pytest.mark.unit
@pytest.mark.usefixtures("use_service")
class TestRequestChecks:
    def test_generating_answers_is_not_supported_yet(self, client):
        request = _request(ANSWER_A)
        request["sources"].append(
            {"id": "b", "kind": "llm_output", "generate_with": "model-b"}
        )
        body = _check_error(client.post(PATH, json=request), 422)
        [error] = body["errors"]
        assert (error["code"], error["scope"], error["source_id"]) == (
            "invalid_request",
            "source",
            "b",
        )

    @pytest.mark.parametrize("strategy", ["factual_consistency", "nope", "fake"])
    def test_other_strategies_are_unsupported(self, client, strategy):
        request = _request(ANSWER_A, ANSWER_B, strategy=strategy)
        body = _check_error(client.post(PATH, json=request), 422)
        [error] = body["errors"]
        assert error["code"] == "unsupported_strategy"
        assert error["details"]["available"] == ["semantic_similarity"]

    def test_catalog_engines_are_rejected(self, client):
        request = _request(ANSWER_A, ANSWER_B, engines=["judge"])
        body = _check_error(client.post(PATH, json=request), 422)
        assert body["errors"][0]["code"] == "unsupported_strategy"

    def test_other_modes_are_rejected(self, client):
        request = {
            "mode": "text_vs_text",
            "sources": [
                {"id": "a", "kind": "text", "text": "One."},
                {"id": "b", "kind": "text", "text": "Two."},
            ],
        }
        body = _check_error(client.post(PATH, json=request), 422)
        assert body["errors"][0]["code"] == "invalid_request"

    @pytest.mark.parametrize(
        "options", [{"direction": "first_to_second"}, {"pivot_language": "en"}]
    )
    def test_unsupported_options_are_rejected(self, client, options):
        request = _request(ANSWER_A, ANSWER_B, options=options)
        body = _check_error(client.post(PATH, json=request), 422)
        assert body["errors"][0]["code"] == "invalid_request"

    def test_one_answer_is_not_enough(self, client):
        response = client.post(PATH, json=_request(ANSWER_A))
        assert response.status_code == 422

    def test_openapi_lists_the_available_strategies(self, client):
        operation = client.get("/openapi.json").json()["paths"][PATH]["post"]
        assert "`semantic_similarity` (cosine_similarity)" in operation["description"]
        assert "`factual_consistency`" not in operation["description"]
