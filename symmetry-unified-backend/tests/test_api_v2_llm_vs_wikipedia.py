"""Tests for POST /symmetry/v2/compare/llm-vs-wikipedia.

Engines and Wikipedia are replaced by fakes through the endpoint's dependency,
so these tests run offline. Every response is validated against the published
JSON Schema (docs/api-v2/api-v2-schema.json) and the cross-field rules of the
schema document.
"""

import json
import re

import pytest
from jsonschema import Draft202012Validator

from app.engines import (
    AdapterRequestError,
    AdapterTimeoutError,
    GenerationRequest,
    GenerationResult,
    ModelAdapter,
)
from app.main import app
from app.routers.api_v2 import get_llm_vs_wikipedia_service
from app.services.llm_vs_wikipedia import LlmVsWikipediaService
from app.services.v2_engines import (
    EngineHandle,
    EngineResolver,
    NoEngineError,
    UnknownEngineError,
)
from app.services.wikipedia_reference import (
    ArticleNotFoundError,
    ArticleRef,
    WikipediaArticle,
    WikipediaReader,
    WikipediaUnavailableError,
)
from tests.api_v2_examples import SCHEMA_DOC

PATH = "/symmetry/v2/compare/llm-vs-wikipedia"

SCHEMA = json.loads(
    (SCHEMA_DOC.parent / "api-v2-schema.json").read_text(encoding="utf-8")
)

ANSWER = (
    "The Eiffel Tower was completed in 1889. It is 400 metres tall. "
    "It is painted every seven years."
)
ARTICLE = WikipediaArticle(
    title="Eiffel Tower",
    language="en",
    text="The Eiffel Tower was completed in 1889.\n\nThe tower is 330 metres tall.",
)
VERDICTS = {
    "The Eiffel Tower was completed in 1889.": {
        "label": "supported",
        "confidence": 0.96,
        "evidence": "The Eiffel Tower was completed in 1889.",
    },
    "It is 400 metres tall.": {
        "label": "contradicted",
        "confidence": 0.91,
        "evidence": "The tower is 330 metres tall.",
    },
    "It is painted every seven years.": {
        "label": "not_found",
        "confidence": 0.8,
        "evidence": "",
    },
}


def _request(**overrides) -> dict:
    body = {
        "mode": "llm_vs_wikipedia",
        "sources": [
            {"id": "a", "kind": "llm_output", "language": "en", "text": ANSWER},
            {
                "id": "b",
                "kind": "wikipedia",
                "url": "https://en.wikipedia.org/wiki/Eiffel_Tower",
            },
        ],
    }
    body.update(overrides)
    return body


# Answers each statement with the verdict scripted for it, or fails with an error.
class ScriptedAdapter(ModelAdapter):
    provider = "test"

    def __init__(self, verdicts=None, error=None, raw_reply=None):
        super().__init__("judge-model")
        self.verdicts = verdicts or VERDICTS
        self.error = error
        self.raw_reply = raw_reply

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.error is not None:
            raise self.error
        if self.raw_reply is not None:
            return GenerationResult(
                text=self.raw_reply, model=self.model_name, provider="test"
            )
        statement = request.prompt.split("Statement:\n", 1)[1]
        verdict = self.verdicts[statement]
        return GenerationResult(
            text=json.dumps(verdict), model=self.model_name, provider="test"
        )


def _engine(engine_id="judge", adapter=None, error=None) -> EngineHandle:
    return EngineHandle(
        id=engine_id,
        type="cloud_llm",
        model="judge-model",
        provider="example-provider",
        adapter=adapter
        if adapter is not None or error is not None
        else ScriptedAdapter(),
        error=error,
    )


class FakeResolver(EngineResolver):
    def __init__(self, *engines: EngineHandle, raises: Exception | None = None):
        self.engines = list(engines) or [_engine()]
        self.raises = raises
        self.requested = None

    def resolve(self, engine_ids):
        self.requested = engine_ids
        if self.raises is not None:
            raise self.raises
        if not engine_ids:
            return self.engines[:1]
        by_id = {e.id: e for e in self.engines}
        unknown = [i for i in engine_ids if i not in by_id]
        if unknown:
            raise UnknownEngineError(unknown, sorted(by_id))
        return [by_id[i] for i in engine_ids]


class FakeReader(WikipediaReader):
    def __init__(self, article=ARTICLE, raises: Exception | None = None):
        self.article = article
        self.raises = raises
        self.refs: list[ArticleRef] = []

    async def read(self, ref: ArticleRef) -> WikipediaArticle:
        self.refs.append(ref)
        if self.raises is not None:
            raise self.raises
        return self.article


@pytest.fixture
def use_service():
    def install(reader=None, resolver=None, strategy_config=None):
        reader = reader or FakeReader()
        resolver = resolver or FakeResolver()
        service = LlmVsWikipediaService(
            reader, resolver, strategy_config=strategy_config
        )
        app.dependency_overrides[get_llm_vs_wikipedia_service] = lambda: service
        return reader, resolver

    yield install
    app.dependency_overrides.pop(get_llm_vs_wikipedia_service, None)


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
            if statement["label"] == "unverifiable":
                assert statement["confidence"] is None
            for evidence in statement["evidence"]:
                assert evidence["source_id"] in (None, *result["source_ids"])
    if body["status"] == "success":
        assert body["errors"] == []
    else:
        assert body["errors"]
    return body


# Checks an error response against the JSON Schema and returns its body.
def _check_error(response, status_code: int) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    _validator("ErrorResponse").validate(body)
    assert body["status"] == "failed"
    assert response.headers["X-Request-ID"] == body["request_id"]
    return body


@pytest.mark.unit
class TestSuccess:
    def test_labels_every_statement(self, client, use_service):
        use_service()
        body = _check_comparison(client.post(PATH, json=_request()))

        assert body["status"] == "success"
        assert body["mode"] == "llm_vs_wikipedia"
        assert body["strategy"] == "factual_consistency"
        [result] = body["results"]
        assert result["status"] == "ok"
        assert result["source_ids"] == ["a", "b"]
        assert result["direction"] == "first_to_second"
        assert result["score_basis"] == "model_reported"
        assert result["engine"] == {
            "id": "judge",
            "type": "cloud_llm",
            "provider": "example-provider",
            "model": "judge-model",
            "fallback_from": None,
        }
        labels = [
            (s["id"], s["text"], s["label"], s["confidence"])
            for s in result["statements"]
        ]
        assert labels == [
            ("a-0", "The Eiffel Tower was completed in 1889.", "supported", 0.96),
            ("a-1", "It is 400 metres tall.", "contradicted", 0.91),
            ("a-2", "It is painted every seven years.", "not_found", 0.8),
        ]
        assert result["overall_score"] == pytest.approx(1 / 3)

    def test_evidence_quotes_the_article(self, client, use_service):
        use_service()
        body = _check_comparison(client.post(PATH, json=_request()))
        statements = body["results"][0]["statements"]
        assert statements[1]["evidence"] == [
            {
                "kind": "wikipedia_passage",
                "source_id": "b",
                "statement_id": None,
                "text": "The tower is 330 metres tall.",
                "url": "https://en.wikipedia.org/wiki/Eiffel_Tower",
            }
        ]
        # No quote for a statement the article does not address.
        assert statements[2]["evidence"] == []

    def test_wikipedia_source_carries_licence_and_attribution(
        self, client, use_service
    ):
        use_service()
        body = _check_comparison(client.post(PATH, json=_request()))
        claim, wiki = body["sources"]
        assert claim["text"] == ANSWER
        assert claim["license"] is None
        assert wiki["label"] == "Eiffel Tower"
        assert wiki["text"] == ARTICLE.text
        assert wiki["license"] == "CC BY-SA 4.0"
        assert "Eiffel Tower" in wiki["attribution"]

    def test_sources_keep_request_order(self, client, use_service):
        use_service()
        request = _request()
        request["sources"].reverse()
        body = _check_comparison(client.post(PATH, json=request))
        assert [s["id"] for s in body["sources"]] == ["b", "a"]
        # The LLM answer is still the side being checked.
        assert body["results"][0]["source_ids"] == ["a", "b"]

    def test_article_by_title_and_revision(self, client, use_service):
        reader, _ = use_service(reader=FakeReader(ARTICLE))
        request = _request()
        request["sources"][1] = {
            "id": "b",
            "kind": "wikipedia",
            "title": "Eiffel Tower",
            "language": "en",
            "revision_id": 123,
        }
        _check_comparison(client.post(PATH, json=request))
        assert reader.refs == [
            ArticleRef(language="en", title="Eiffel Tower", revision_id=123)
        ]

    def test_options_can_leave_out_text_and_evidence(self, client, use_service):
        use_service()
        request = _request(
            options={"include_source_text": False, "include_evidence": False}
        )
        body = _check_comparison(client.post(PATH, json=request))
        assert [s["text"] for s in body["sources"]] == [None, None]
        assert all(s["evidence"] == [] for s in body["results"][0]["statements"])

    def test_named_engines_are_passed_to_the_resolver(self, client, use_service):
        _, resolver = use_service(resolver=FakeResolver(_engine("one"), _engine("two")))
        body = _check_comparison(client.post(PATH, json=_request(engines=["two"])))
        assert resolver.requested == ["two"]
        assert [r["engine"]["id"] for r in body["results"]] == ["two"]


@pytest.mark.unit
class TestPartialFailure:
    def test_one_engine_timing_out_gives_a_partial_response(self, client, use_service):
        slow = ScriptedAdapter(error=AdapterTimeoutError("no reply", provider="test"))
        use_service(resolver=FakeResolver(_engine("ok"), _engine("slow", slow)))
        body = _check_comparison(
            client.post(PATH, json=_request(engines=["ok", "slow"]))
        )

        assert body["status"] == "partial"
        ok, failed = body["results"]
        assert ok["status"] == "ok"
        assert failed["status"] == "failed"
        assert failed["engine"]["id"] == "slow"
        assert failed["statements"] == [] and failed["alignments"] == []
        assert failed["overall_score"] is None and failed["score_basis"] is None
        [error] = body["errors"]
        assert error["code"] == "engine_timeout"
        assert error["scope"] == "engine"
        assert error["engine_id"] == "slow"
        assert error["retryable"] is True

    def test_engine_that_could_not_be_built_is_reported(self, client, use_service):
        broken = _engine(
            "broken", error=AdapterRequestError("CLOUD_LLM_API_KEY is not set")
        )
        use_service(resolver=FakeResolver(_engine("ok"), broken))
        body = _check_comparison(
            client.post(PATH, json=_request(engines=["ok", "broken"]))
        )
        assert body["status"] == "partial"
        [error] = body["errors"]
        assert error["code"] == "engine_unavailable"
        assert error["engine_id"] == "broken"
        assert error["retryable"] is False
        assert "CLOUD_LLM_API_KEY is not set" in error["message"]


@pytest.mark.unit
class TestFailure:
    def test_every_engine_timing_out_returns_504(self, client, use_service):
        slow = ScriptedAdapter(error=AdapterTimeoutError("no reply", provider="test"))
        use_service(resolver=FakeResolver(_engine("slow", slow)))
        body = _check_error(client.post(PATH, json=_request()), 504)
        [error] = body["errors"]
        assert (error["code"], error["engine_id"]) == ("engine_timeout", "slow")

    def test_unreadable_engine_reply_returns_502(self, client, use_service):
        use_service(
            resolver=FakeResolver(_engine("judge", ScriptedAdapter(raw_reply="maybe?")))
        )
        body = _check_error(client.post(PATH, json=_request()), 502)
        assert body["errors"][0]["code"] == "engine_bad_output"

    def test_mixed_engine_failures_return_502(self, client, use_service):
        slow = ScriptedAdapter(error=AdapterTimeoutError("no reply", provider="test"))
        rejected = ScriptedAdapter(
            error=AdapterRequestError("HTTP 401", provider="test")
        )
        use_service(
            resolver=FakeResolver(_engine("slow", slow), _engine("rejected", rejected))
        )
        body = _check_error(
            client.post(PATH, json=_request(engines=["slow", "rejected"])), 502
        )
        assert {e["code"] for e in body["errors"]} == {
            "engine_timeout",
            "engine_unavailable",
        }

    def test_missing_article_returns_404(self, client, use_service):
        use_service(
            reader=FakeReader(
                raises=ArticleNotFoundError("Wikipedia article not found")
            )
        )
        body = _check_error(client.post(PATH, json=_request()), 404)
        [error] = body["errors"]
        assert (error["code"], error["scope"], error["source_id"]) == (
            "source_not_found",
            "source",
            "b",
        )

    def test_unreachable_wikipedia_is_a_retryable_source_error(
        self, client, use_service
    ):
        use_service(reader=FakeReader(raises=WikipediaUnavailableError("offline")))
        body = _check_error(client.post(PATH, json=_request()), 500)
        [error] = body["errors"]
        assert (error["scope"], error["source_id"], error["retryable"]) == (
            "source",
            "b",
            True,
        )

    def test_no_engine_configured_returns_503(self, client, use_service):
        use_service(resolver=FakeResolver(raises=NoEngineError("no comparison engine")))
        body = _check_error(client.post(PATH, json=_request()), 503)
        assert body["errors"][0]["code"] == "engine_unavailable"

    def test_unknown_engine_returns_422(self, client, use_service):
        use_service()
        body = _check_error(client.post(PATH, json=_request(engines=["nope"])), 422)
        [error] = body["errors"]
        assert error["code"] == "unsupported_engine"
        assert error["details"]["unknown"] == ["nope"]

    def test_unexpected_errors_return_an_error_response(self, client, use_service):
        use_service(reader=FakeReader(raises=RuntimeError("bug")))
        body = _check_error(client.post(PATH, json=_request()), 500)
        assert body["errors"][0]["code"] == "internal_error"
        assert "bug" not in body["errors"][0]["message"]


@pytest.mark.unit
class TestRequestChecks:
    @pytest.mark.parametrize("strategy", ["no_such_strategy", "fake"])
    def test_unknown_and_internal_strategies_are_unsupported(
        self, client, use_service, strategy
    ):
        use_service()
        body = _check_error(client.post(PATH, json=_request(strategy=strategy)), 422)
        [error] = body["errors"]
        assert error["code"] == "unsupported_strategy"
        assert error["details"]["available"] == [
            "factual_consistency",
            "semantic_similarity",
        ]

    def test_explicit_factual_consistency_is_accepted(self, client, use_service):
        use_service()
        _check_comparison(
            client.post(PATH, json=_request(strategy="factual_consistency"))
        )

    def test_other_modes_are_rejected(self, client, use_service):
        use_service()
        request = {
            "mode": "llm_vs_llm",
            "sources": [
                {"id": "a", "kind": "llm_output", "text": "One."},
                {"id": "b", "kind": "llm_output", "text": "Two."},
            ],
        }
        body = _check_error(client.post(PATH, json=request), 422)
        assert body["errors"][0]["code"] == "invalid_request"

    @pytest.mark.parametrize(
        "options",
        [{"direction": "both"}, {"pivot_language": "en"}],
    )
    def test_unsupported_options_are_rejected(self, client, use_service, options):
        use_service()
        body = _check_error(client.post(PATH, json=_request(options=options)), 422)
        assert body["errors"][0]["code"] == "invalid_request"

    def test_generating_the_answer_is_not_supported_yet(self, client, use_service):
        use_service()
        request = _request(prompt="How tall is the Eiffel Tower?")
        request["sources"][0] = {
            "id": "a",
            "kind": "llm_output",
            "generate_with": "judge",
        }
        body = _check_error(client.post(PATH, json=request), 422)
        [error] = body["errors"]
        assert (error["code"], error["source_id"]) == ("invalid_request", "a")

    def test_title_without_language_is_rejected(self, client, use_service):
        use_service()
        request = _request()
        request["sources"][1] = {
            "id": "b",
            "kind": "wikipedia",
            "title": "Eiffel Tower",
        }
        body = _check_error(client.post(PATH, json=request), 422)
        assert body["errors"][0]["source_id"] == "b"

    def test_too_many_statements_is_an_invalid_request(self, client, use_service):
        use_service(
            resolver=FakeResolver(_engine("judge", ScriptedAdapter(verdicts={})))
        )
        request = _request()
        request["sources"][0]["text"] = " ".join(f"Claim {i}." for i in range(101))
        body = _check_error(client.post(PATH, json=request), 422)
        [error] = body["errors"]
        assert (error["code"], error["scope"]) == ("invalid_request", "request")


# Deterministic stand-in for the embedding model: bag-of-words vectors, so
# identical sentences score 1.0 and sentences sharing no words score 0.0.
class WordEmbedder:
    def __init__(self, fail: bool = False):
        self.fail = fail

    def encode(self, sentences):
        if self.fail:
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


SIMILARITY_ANSWER = (
    "The Eiffel Tower was completed in 1889. "
    "The tower is 400 metres tall. "
    "Bananas grow on trees."
)


def _semantic_config(fail: bool = False) -> dict:
    return {
        "semantic_similarity": {
            "embedder": WordEmbedder(fail),
            "model_name": "test-embedder",
        }
    }


def _semantic_request(**options) -> dict:
    request = _request(strategy="semantic_similarity", options=options)
    request["sources"][0]["text"] = SIMILARITY_ANSWER
    return request


@pytest.mark.unit
class TestStrategySelection:
    def test_semantic_similarity_is_chosen_by_the_request(self, client, use_service):
        use_service(strategy_config=_semantic_config())
        request = _semantic_request(similarity_threshold=0.9, partial_threshold=0.7)
        body = _check_comparison(client.post(PATH, json=request))

        assert body["strategy"] == "semantic_similarity"
        [result] = body["results"]
        assert result["score_basis"] == "cosine_similarity"
        assert result["engine"] == {
            "id": "embedding-default",
            "type": "embedding",
            "provider": "local",
            "model": "test-embedder",
            "fallback_from": None,
        }
        rows = [
            (s["label"], s["best_match_similarity"], s["confidence"])
            for s in result["statements"]
        ]
        assert rows == [
            ("supported", 1.0, None),
            ("partial", pytest.approx(5 / 6, abs=1e-4), None),
            ("not_found", 0.0, None),
        ]
        assert result["overall_score"] == pytest.approx((1 + 5 / 6 + 0) / 3, abs=1e-3)

    def test_evidence_is_the_closest_article_sentence(self, client, use_service):
        use_service(strategy_config=_semantic_config())
        request = _semantic_request(similarity_threshold=0.9, partial_threshold=0.7)
        statements = _check_comparison(client.post(PATH, json=request))["results"][0][
            "statements"
        ]
        assert [e["text"] for s in statements for e in s["evidence"]] == [
            "The Eiffel Tower was completed in 1889.",
            "The tower is 330 metres tall.",
        ]
        # No passage is offered for a statement the article does not address.
        assert statements[2]["evidence"] == []

    def test_server_threshold_applies_when_none_is_requested(self, client, use_service):
        use_service(strategy_config=_semantic_config())
        body = _check_comparison(client.post(PATH, json=_semantic_request()))
        labels = [s["label"] for s in body["results"][0]["statements"]]
        # 0.83 is above the default threshold of 0.65.
        assert labels == ["supported", "supported", "not_found"]

    def test_semantic_similarity_needs_no_language_model(self, client, use_service):
        use_service(
            resolver=FakeResolver(raises=NoEngineError("no engine")),
            strategy_config=_semantic_config(),
        )
        _check_comparison(client.post(PATH, json=_semantic_request()))

    def test_embedding_strategy_rejects_catalog_engines(self, client, use_service):
        use_service(strategy_config=_semantic_config())
        request = _semantic_request()
        request["engines"] = ["judge"]
        body = _check_error(client.post(PATH, json=request), 422)
        [error] = body["errors"]
        assert error["code"] == "unsupported_strategy"
        assert error["details"]["engines"] == ["judge"]

    def test_embedding_model_failure_returns_503(self, client, use_service):
        use_service(strategy_config=_semantic_config(fail=True))
        body = _check_error(client.post(PATH, json=_semantic_request()), 503)
        [error] = body["errors"]
        assert (error["code"], error["scope"], error["engine_id"]) == (
            "engine_unavailable",
            "engine",
            "embedding-default",
        )

    def test_default_strategy_is_factual_consistency(self, client, use_service):
        use_service()
        body = _check_comparison(client.post(PATH, json=_request(strategy=None)))
        assert body["strategy"] == "factual_consistency"
        assert body["results"][0]["score_basis"] == "model_reported"

    def test_openapi_lists_the_available_strategies(self, client):
        operation = client.get("/openapi.json").json()["paths"][PATH]["post"]
        assert "`factual_consistency` (model_reported)" in operation["description"]
        assert "`semantic_similarity` (cosine_similarity)" in operation["description"]
