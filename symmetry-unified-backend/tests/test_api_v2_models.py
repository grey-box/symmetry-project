"""Tests for the API v2 Pydantic models in app.models.v2."""

import pytest
from pydantic import ValidationError

from app.models.v2 import ComparisonResponse, ErrorResponse, Span
from tests.api_v2_examples import example

RESPONSE_EXAMPLES = ["10.2", "10.3"]


def _error(**overrides):
    error = {
        "code": "engine_timeout",
        "message": "The engine did not respond in time.",
        "scope": "engine",
        "source_id": None,
        "engine_id": "openrouter-default",
        "retryable": True,
        "details": None,
    }
    error.update(overrides)
    return error


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("number", RESPONSE_EXAMPLES)
def test_response_example_round_trips(number):
    payload = example(number)
    response = ComparisonResponse.model_validate(payload)
    assert response.model_dump(mode="json") == payload


@pytest.mark.unit
def test_response_nullable_field_is_still_required():
    payload = example("10.2")
    del payload["sources"][0]["label"]
    with pytest.raises(ValidationError, match="label"):
        ComparisonResponse.model_validate(payload)


@pytest.mark.unit
def test_response_rejects_unknown_field():
    payload = example("10.2")
    payload["results"][0]["engine"]["temperature"] = 0.2
    with pytest.raises(ValidationError, match="temperature"):
        ComparisonResponse.model_validate(payload)


@pytest.mark.unit
def test_response_rejects_score_out_of_range():
    payload = example("10.3")
    payload["results"][0]["statements"][0]["confidence"] = 1.5
    with pytest.raises(ValidationError, match="confidence"):
        ComparisonResponse.model_validate(payload)


@pytest.mark.unit
def test_response_rejects_unknown_label():
    payload = example("10.3")
    payload["results"][0]["statements"][0]["label"] = "maybe"
    with pytest.raises(ValidationError, match="label"):
        ComparisonResponse.model_validate(payload)


@pytest.mark.unit
def test_response_accepts_any_strategy_id():
    payload = example("10.2")
    payload["strategy"] = "custom_strategy"
    assert ComparisonResponse.model_validate(payload).strategy == "custom_strategy"


@pytest.mark.unit
def test_result_must_compare_exactly_two_sources():
    payload = example("10.2")
    payload["results"][0]["source_ids"] = ["a", "b", "c"]
    with pytest.raises(ValidationError, match="source_ids"):
        ComparisonResponse.model_validate(payload)


@pytest.mark.unit
def test_span_end_must_not_be_before_start():
    with pytest.raises(ValidationError, match="before start"):
        Span(start=10, end=5)


@pytest.mark.unit
def test_error_response_accepts_failed_request():
    response = ErrorResponse.model_validate(
        {
            "api_version": "2.0",
            "request_id": "req_1",
            "status": "failed",
            "errors": [_error()],
        }
    )
    assert response.errors[0].code == "engine_timeout"


@pytest.mark.unit
def test_error_response_needs_at_least_one_error():
    with pytest.raises(ValidationError, match="errors"):
        ErrorResponse.model_validate(
            {
                "api_version": "2.0",
                "request_id": "req_1",
                "status": "failed",
                "errors": [],
            }
        )


@pytest.mark.unit
def test_error_response_status_is_failed():
    with pytest.raises(ValidationError, match="status"):
        ErrorResponse.model_validate(
            {
                "api_version": "2.0",
                "request_id": "req_1",
                "status": "partial",
                "errors": [_error()],
            }
        )


@pytest.mark.unit
def test_error_detail_rejects_unknown_code():
    with pytest.raises(ValidationError, match="code"):
        ErrorResponse.model_validate(
            {
                "api_version": "2.0",
                "request_id": "req_1",
                "status": "failed",
                "errors": [_error(code="teapot")],
            }
        )
