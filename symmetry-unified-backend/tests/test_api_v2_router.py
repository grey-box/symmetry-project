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


@pytest.mark.unit
def test_v2_compare_rate_limit(client):
    """The generic v2 endpoint should reject request 61 within one minute."""
    from app.routers.api_v2 import limiter

    limiter.reset()

    try:
        for _ in range(60):
            response = client.post("/symmetry/v2/compare", json={})
            assert response.status_code == 501

        response = client.post("/symmetry/v2/compare", json={})

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
    finally:
        limiter.reset()

@pytest.mark.unit
def test_v2_rate_limit_does_not_affect_v1(client):
    """Exhausting a v2 limit must not rate-limit existing v1 routes."""
    from app.routers.api_v2 import limiter

    limiter.reset()

    try:
        for _ in range(61):
            client.post("/symmetry/v2/compare", json={})

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    finally:
        limiter.reset()