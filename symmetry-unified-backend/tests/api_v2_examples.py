"""Loads the JSON examples from the API v2 schema document.

Tests validate the v2 models against these examples so that the document and
the models cannot drift apart.
"""

import json
import re
from functools import cache
from pathlib import Path

SCHEMA_DOC = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "api-v2"
    / "api-v2-response-schema.md"
)

_EXAMPLE = re.compile(
    r"^### (10\.\d+)[^\n]*\n.*?```json\n(.*?)```", re.DOTALL | re.MULTILINE
)


@cache
def _examples() -> dict[str, dict]:
    text = SCHEMA_DOC.read_text(encoding="utf-8")
    return {number: json.loads(body) for number, body in _EXAMPLE.findall(text)}


def example(number: str) -> dict:
    """Return a fresh copy of the example in section ``number``, e.g. "10.2"."""
    return json.loads(json.dumps(_examples()[number]))
