"""Negative contract tests for API v2 response payloads.

These tests validate response payloads directly against the published
API v2 JSON Schema. They ensure CI fails when a response breaks the
external API contract.
"""

import json

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from tests.api_v2_examples import SCHEMA_DOC, example

SCHEMA = json.loads(
    (SCHEMA_DOC.parent / "api-v2-schema.json").read_text(encoding="utf-8")
)


def _response_validator() -> Draft202012Validator:
    """Return a validator for the published ComparisonResponse contract."""
    return Draft202012Validator(
        {
            "$schema": SCHEMA["$schema"],
            "$defs": SCHEMA["$defs"],
            "$ref": "#/$defs/ComparisonResponse",
        }
    )


@pytest.mark.unit
def test_valid_response_satisfies_published_contract():
    payload = example("10.2")

    _response_validator().validate(payload)


@pytest.mark.unit
def test_contract_rejects_missing_required_request_id():
    payload = example("10.2")
    del payload["request_id"]

    with pytest.raises(ValidationError):
        _response_validator().validate(payload)


@pytest.mark.unit
def test_contract_rejects_invalid_response_status():
    payload = example("10.2")
    payload["status"] = "failed"

    with pytest.raises(ValidationError):
        _response_validator().validate(payload)


@pytest.mark.unit
def test_contract_rejects_response_with_only_one_source():
    payload = example("10.2")
    payload["sources"] = payload["sources"][:1]

    with pytest.raises(ValidationError):
        _response_validator().validate(payload)


@pytest.mark.unit
def test_contract_rejects_invalid_confidence_score():
    payload = example("10.3")
    payload["results"][0]["statements"][0]["confidence"] = 1.5

    with pytest.raises(ValidationError):
        _response_validator().validate(payload)