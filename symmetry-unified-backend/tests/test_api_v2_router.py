"""Tests for the API v2 router skeleton under /symmetry/v2."""

import pytest

from tests.api_v2_examples import example

V2_ENDPOINTS = [
    "/symmetry/v2/compare",
    "/symmetry/v2/compare/llm-vs-wikipedia",
    "/symmetry/v2/compare/llm-vs-llm",
]

LLM_VS_WIKIPEDIA_REQUEST = {
    "mode": "llm_vs_wikipedia",
    "sources": [
        {
            "id": "a",
            "kind": "llm_output",
            "text": "The Eiffel Tower is 400 metres tall.",
        },
        {
            "id": "b",
            "kind": "wikipedia",
            "url": "https://en.wikipedia.org/wiki/Eiffel_Tower",
        },
    ],
}

VALID_REQUESTS = {
    "/symmetry/v2/compare": LLM_VS_WIKIPEDIA_REQUEST,
    "/symmetry/v2/compare/llm-vs-wikipedia": LLM_VS_WIKIPEDIA_REQUEST,
    "/symmetry/v2/compare/llm-vs-llm": example("10.1"),
}


@pytest.mark.unit
@pytest.mark.parametrize("path", V2_ENDPOINTS)
def test_v2_endpoint_returns_501_for_valid_request(client, path):
    response = client.post(path, json=VALID_REQUESTS[path])
    assert response.status_code == 501
    assert "not implemented" in response.json()["detail"]


@pytest.mark.unit
@pytest.mark.parametrize("path", V2_ENDPOINTS)
def test_v2_endpoint_validates_request(client, path):
    response = client.post(path, json={})
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.parametrize("path", V2_ENDPOINTS)
def test_v2_endpoint_rejects_non_wikipedia_url(client, path):
    request = {
        "mode": "llm_vs_wikipedia",
        "sources": [
            LLM_VS_WIKIPEDIA_REQUEST["sources"][0],
            {"id": "b", "kind": "wikipedia", "url": "http://169.254.169.254/wiki/x"},
        ],
    }
    response = client.post(path, json=request)
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.parametrize("path", V2_ENDPOINTS)
def test_v2_endpoint_is_in_openapi(client, path):
    paths = client.get("/openapi.json").json()["paths"]
    assert "post" in paths[path]
    assert paths[path]["post"]["tags"] == ["v2"]


@pytest.mark.unit
@pytest.mark.parametrize("path", V2_ENDPOINTS)
def test_v2_endpoint_documents_models(client, path):
    operation = client.get("/openapi.json").json()["paths"][path]["post"]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert request_schema == {"$ref": "#/components/schemas/ComparisonRequest"}
    assert response_schema == {"$ref": "#/components/schemas/ComparisonResponse"}


@pytest.mark.unit
def test_v1_routes_unchanged(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/symmetry/v1/articles/compare" in paths
    assert "/symmetry/v1/comparison/semantic" in paths
    assert client.get("/health").json() == {"status": "healthy"}


@pytest.mark.unit
def test_v1_schema_names_unchanged(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "WordToken" in schemas
    assert "WordDiffToken" in schemas
