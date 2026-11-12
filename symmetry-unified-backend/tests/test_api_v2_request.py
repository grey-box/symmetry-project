"""Tests for the API v2 request model and its validation rules."""

import pytest
from pydantic import ValidationError

from app.models.v2 import ComparisonRequest
from app.models.v2.request import is_wikipedia_article_url
from tests.api_v2_examples import example

WIKI_URL = "https://en.wikipedia.org/wiki/Eiffel_Tower"


def _llm(source_id="a", **fields):
    return {"id": source_id, "kind": "llm_output", "text": "Some text.", **fields}


def _wiki(source_id="b", **fields):
    source = {"id": source_id, "kind": "wikipedia", "url": WIKI_URL}
    source.update(fields)
    return source


def _text(source_id, **fields):
    return {"id": source_id, "kind": "text", "text": "Some text.", **fields}


def _llm_vs_wikipedia(**overrides):
    request = {"mode": "llm_vs_wikipedia", "sources": [_llm(), _wiki()]}
    request.update(overrides)
    return request


def _rejected(payload, match):
    with pytest.raises(ValidationError, match=match):
        ComparisonRequest.model_validate(payload)


# ---------------------------------------------------------------------------
# Valid requests and defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_request_example_is_valid():
    request = ComparisonRequest.model_validate(example("10.1"))
    assert request.mode == "llm_vs_llm"
    assert [s.generate_with for s in request.sources] == [
        "model-a",
        "model-b",
        "model-c",
    ]


@pytest.mark.unit
def test_request_defaults():
    request = ComparisonRequest.model_validate(_llm_vs_wikipedia())
    assert request.engines == []
    assert request.strategy is None
    assert request.prompt is None
    assert request.options.similarity_threshold is None
    assert request.options.include_source_text is True
    assert request.options.include_word_diff is False


@pytest.mark.unit
def test_request_accepts_any_strategy_id():
    request = ComparisonRequest.model_validate(
        _llm_vs_wikipedia(strategy="custom_strategy")
    )
    assert request.strategy == "custom_strategy"


@pytest.mark.unit
def test_request_rejects_empty_strategy():
    _rejected(_llm_vs_wikipedia(strategy=""), "strategy")


@pytest.mark.unit
def test_request_rejects_unknown_field():
    _rejected(_llm_vs_wikipedia(temperature=0.2), "temperature")


@pytest.mark.unit
def test_source_rejects_unknown_field():
    _rejected(_llm_vs_wikipedia(sources=[_llm(colour="red"), _wiki()]), "colour")


@pytest.mark.unit
def test_wikipedia_source_by_title_and_revision():
    source = {
        "id": "b",
        "kind": "wikipedia",
        "title": "Eiffel Tower",
        "language": "en",
        "revision_id": 123,
    }
    request = ComparisonRequest.model_validate(
        _llm_vs_wikipedia(sources=[_llm(), source])
    )
    assert request.sources[1].revision_id == 123


# ---------------------------------------------------------------------------
# Rule 1: at least two sources, unique ids
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rule1_needs_two_sources():
    _rejected({"mode": "text_vs_text", "sources": [_text("a")]}, "at least 2")


@pytest.mark.unit
def test_rule1_ids_must_be_unique():
    _rejected(
        {"mode": "text_vs_text", "sources": [_text("a"), _text("a")]},
        "unique",
    )


@pytest.mark.unit
def test_rule1_id_must_not_be_empty():
    _rejected({"mode": "text_vs_text", "sources": [_text(""), _text("b")]}, "id")


# ---------------------------------------------------------------------------
# Rule 2: exactly one content field per source
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rule2_source_needs_content():
    _rejected(
        _llm_vs_wikipedia(sources=[{"id": "a", "kind": "llm_output"}, _wiki()]),
        "exactly one",
    )


@pytest.mark.unit
def test_rule2_source_cannot_set_two_content_fields():
    _rejected(
        _llm_vs_wikipedia(sources=[_llm(), _wiki(title="Eiffel Tower")]),
        "exactly one",
    )


# ---------------------------------------------------------------------------
# Rule 3: Wikipedia-only fields, Wikipedia article URLs only
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "field, value",
    [("url", WIKI_URL), ("title", "Eiffel Tower"), ("revision_id", 1)],
)
def test_rule3_wikipedia_fields_rejected_on_other_kinds(field, value):
    source = {"id": "a", "kind": "text", field: value}
    if field == "revision_id":
        source["text"] = "Some text."
    _rejected(
        {"mode": "text_vs_text", "sources": [source, _text("b")]},
        "only allowed for kind 'wikipedia'",
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "url",
    [
        "https://en.wikipedia.org/wiki/Eiffel_Tower",
        "http://en.wikipedia.org/wiki/Eiffel_Tower",
        "https://fr.m.wikipedia.org/wiki/Tour_Eiffel",
        "https://zh-yue.wikipedia.org/wiki/Example",
    ],
)
def test_rule3_accepts_wikipedia_article_urls(url):
    assert is_wikipedia_article_url(url)


@pytest.mark.unit
@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/wiki/latest",
        "http://localhost/wiki/Eiffel_Tower",
        "https://example.com/wiki/Eiffel_Tower",
        "https://en.wikipedia.org.example.com/wiki/Eiffel_Tower",
        "https://wikipedia.org/wiki/Eiffel_Tower",
        "https://user@en.wikipedia.org/wiki/Eiffel_Tower",
        "https://en.wikipedia.org:8080/wiki/Eiffel_Tower",
        "ftp://en.wikipedia.org/wiki/Eiffel_Tower",
        "https://en.wikipedia.org/w/index.php?title=Eiffel_Tower",
        "https://en.wikipedia.org/wiki/",
        "not a url",
    ],
)
def test_rule3_rejects_other_urls(url):
    assert not is_wikipedia_article_url(url)
    _rejected(
        _llm_vs_wikipedia(sources=[_llm(), _wiki(url=url)]),
        "Wikipedia article URL",
    )


# ---------------------------------------------------------------------------
# Rule 4: generate_with only on llm_output, and requires prompt
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rule4_generate_with_only_on_llm_output():
    source = {"id": "a", "kind": "text", "generate_with": "model-a"}
    _rejected(
        {"mode": "text_vs_text", "prompt": "Q?", "sources": [source, _text("b")]},
        "generate_with only allowed",
    )


@pytest.mark.unit
def test_rule4_generate_with_requires_prompt():
    payload = example("10.1")
    del payload["prompt"]
    _rejected(payload, "prompt is required")


# ---------------------------------------------------------------------------
# Rule 5: sources must match the mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rule5_text_vs_text_accepts_documents():
    document = {"id": "b", "kind": "document", "text": "# Title\n\nBody."}
    request = ComparisonRequest.model_validate(
        {"mode": "text_vs_text", "sources": [_text("a"), document]}
    )
    assert request.sources[1].kind == "document"


@pytest.mark.unit
def test_rule5_llm_vs_llm_rejects_text_sources():
    _rejected(
        {"mode": "llm_vs_llm", "sources": [_llm("a"), _text("b")]},
        "does not accept source kinds",
    )


@pytest.mark.unit
def test_rule5_text_vs_text_rejects_wikipedia():
    _rejected(
        {"mode": "text_vs_text", "sources": [_text("a"), _wiki()]},
        "does not accept source kinds",
    )


@pytest.mark.unit
def test_rule5_llm_vs_wikipedia_needs_one_of_each():
    _rejected(
        _llm_vs_wikipedia(sources=[_llm("a"), _llm("b")]),
        "exactly one 'llm_output' and one 'wikipedia'",
    )


@pytest.mark.unit
def test_rule5_llm_vs_wikipedia_takes_two_sources_only():
    _rejected(
        _llm_vs_wikipedia(sources=[_llm("a"), _wiki("b"), _wiki("c")]),
        "exactly one 'llm_output' and one 'wikipedia'",
    )


# ---------------------------------------------------------------------------
# Rule 6 and other options
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("partial", [0.75, 0.9])
def test_rule6_partial_threshold_below_similarity_threshold(partial):
    options = {"similarity_threshold": 0.75, "partial_threshold": partial}
    _rejected(_llm_vs_wikipedia(options=options), "partial_threshold")


@pytest.mark.unit
def test_rule6_partial_threshold_alone_is_allowed():
    request = ComparisonRequest.model_validate(
        _llm_vs_wikipedia(options={"partial_threshold": 0.5})
    )
    assert request.options.partial_threshold == 0.5


@pytest.mark.unit
def test_threshold_out_of_range_rejected():
    _rejected(_llm_vs_wikipedia(options={"similarity_threshold": 1.2}), "similarity")


@pytest.mark.unit
def test_timeout_must_be_positive():
    _rejected(_llm_vs_wikipedia(options={"timeout_seconds": 0}), "timeout_seconds")
