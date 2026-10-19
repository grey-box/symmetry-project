"""Checks the API v2 models against the published JSON Schema.

``docs/api-v2/api-v2-schema.json`` is the contract. These tests make sure the
Pydantic models declare exactly the fields it lists, and that what they
produce validates against it.
"""

import json

import pytest
from jsonschema import Draft202012Validator

from app.models import v2
from tests.api_v2_examples import SCHEMA_DOC, example

SCHEMA = json.loads(
    (SCHEMA_DOC.parent / "api-v2-schema.json").read_text(encoding="utf-8")
)

# JSON Schema definition name -> model, where the class name differs.
RENAMED = {"WordToken": v2.WordDiffToken}


def _model(definition: str):
    return RENAMED.get(definition) or getattr(v2, definition)


def _validator(definition: str) -> Draft202012Validator:
    return Draft202012Validator(
        {
            "$schema": SCHEMA["$schema"],
            "$defs": SCHEMA["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
    )


@pytest.mark.unit
def test_schema_file_is_valid_json_schema():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.unit
@pytest.mark.parametrize("definition", sorted(SCHEMA["$defs"]))
def test_model_fields_match_schema(definition):
    expected = SCHEMA["$defs"][definition]
    actual = _model(definition).model_json_schema()
    assert set(actual["properties"]) == set(expected["properties"])
    assert set(actual.get("required", [])) == set(expected.get("required", []))


@pytest.mark.unit
def test_request_example_matches_schema():
    request = v2.ComparisonRequest.model_validate(example("10.1"))
    _validator("ComparisonRequest").validate(request.model_dump(mode="json"))


@pytest.mark.unit
@pytest.mark.parametrize("number", ["10.2", "10.3"])
def test_response_examples_match_schema(number):
    response = v2.ComparisonResponse.model_validate(example(number))
    _validator("ComparisonResponse").validate(response.model_dump(mode="json"))


@pytest.mark.unit
def test_error_response_matches_schema():
    response = v2.ErrorResponse(
        api_version=v2.API_VERSION,
        request_id="req_1",
        status="failed",
        errors=[
            v2.ErrorDetail(
                code="invalid_request",
                message="At least two sources are required.",
                scope="request",
                source_id=None,
                engine_id=None,
                retryable=False,
                details={"fields": ["sources"]},
            )
        ],
    )
    _validator("ErrorResponse").validate(response.model_dump(mode="json"))
