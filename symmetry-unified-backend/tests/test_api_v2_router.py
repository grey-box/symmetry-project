"""Tests for the API v2 router skeleton under /symmetry/v2."""

import pytest

V2_ENDPOINTS = [
    "/symmetry/v2/compare",
    "/symmetry/v2/compare/llm-vs-wikipedia",
    "/symmetry/v2/compare/llm-vs-llm",
]


@pytest.mark.unit
@pytest.mark.parametrize("path", V2_ENDPOINTS)
def test_v2_endpoint_returns_501(client, path):
    response = client.post(path, json={})
    assert response.status_code == 501
    assert "not implemented" in response.json()["detail"]


@pytest.mark.unit
@pytest.mark.parametrize("path", V2_ENDPOINTS)
def test_v2_endpoint_is_in_openapi(client, path):
    paths = client.get("/openapi.json").json()["paths"]
    assert "post" in paths[path]
    assert paths[path]["post"]["tags"] == ["v2"]


@pytest.mark.unit
def test_v1_routes_unchanged(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/symmetry/v1/articles/compare" in paths
    assert "/symmetry/v1/comparison/semantic" in paths
    assert client.get("/health").json() == {"status": "healthy"}
