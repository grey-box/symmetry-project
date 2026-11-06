"""Acceptance tests for the API v2 LLM-vs-Wikipedia endpoint.

Covers Prashant's Sprint 5 acceptance criteria:
valid input, bad Wikipedia title/URL, and empty LLM text.
"""

import pytest

from app.main import app
from app.routers.api_v2 import get_llm_vs_wikipedia_service
from app.services.llm_vs_wikipedia import LlmVsWikipediaService
from app.services.v2_engines import EngineHandle, EngineResolver
from app.services.wikipedia_reference import (
    ArticleNotFoundError,
    ArticleRef,
    WikipediaArticle,
    WikipediaReader,
)
from tests.test_api_v2_llm_vs_wikipedia import ScriptedAdapter

PATH = "/symmetry/v2/compare/llm-vs-wikipedia"

ARTICLE = WikipediaArticle(
    title="Eiffel Tower",
    language="en",
    text="The Eiffel Tower was completed in 1889.",
)


class AcceptanceReader(WikipediaReader):
    def __init__(self, *, missing=False):
        self.missing = missing

    async def read(self, ref: ArticleRef) -> WikipediaArticle:
        if self.missing:
            raise ArticleNotFoundError("Wikipedia article not found")
        return ARTICLE


class AcceptanceResolver(EngineResolver):
    def resolve(self, engine_ids):
        return [
            EngineHandle(
                id="judge",
                type="cloud_llm",
                model="judge-model",
                provider="test",
                adapter=ScriptedAdapter(),
            )
        ]


@pytest.fixture
def install_service():
    def install(*, missing_article=False):
        service = LlmVsWikipediaService(
            AcceptanceReader(missing=missing_article),
            AcceptanceResolver(),
        )
        app.dependency_overrides[get_llm_vs_wikipedia_service] = lambda: service

    yield install
    app.dependency_overrides.pop(get_llm_vs_wikipedia_service, None)


def valid_request():
    return {
        "mode": "llm_vs_wikipedia",
        "sources": [
            {
                "id": "claim",
                "kind": "llm_output",
                "language": "en",
                "text": "The Eiffel Tower was completed in 1889.",
            },
            {
                "id": "wiki",
                "kind": "wikipedia",
                "url": "https://en.wikipedia.org/wiki/Eiffel_Tower",
            },
        ],
    }


@pytest.mark.unit
def test_valid_llm_vs_wikipedia_input_returns_success(client, install_service):
    install_service()

    response = client.post(PATH, json=valid_request())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["mode"] == "llm_vs_wikipedia"
    assert body["errors"] == []


@pytest.mark.unit
def test_missing_wikipedia_title_returns_source_not_found(client, install_service):
    install_service(missing_article=True)

    response = client.post(PATH, json=valid_request())

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "failed"
    assert body["errors"][0]["code"] == "source_not_found"
    assert body["errors"][0]["scope"] == "source"
    assert body["errors"][0]["source_id"] == "wiki"


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_url",
    [
        "https://example.com/wiki/Eiffel_Tower",
        "not-a-url",
    ],
)
def test_bad_wikipedia_url_is_rejected(client, install_service, bad_url):
    install_service()
    request = valid_request()
    request["sources"][1]["url"] = bad_url

    response = client.post(PATH, json=request)

    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.parametrize("empty_text", ["", "   "])
def test_empty_llm_text_is_rejected(client, install_service, empty_text):
    install_service()
    request = valid_request()
    request["sources"][0]["text"] = empty_text

    response = client.post(PATH, json=request)

    assert response.status_code == 422