"""Tests that each supported API v2 source kind reaches the generic pipeline."""

import asyncio

import pytest

from app.pipeline import ComparisonPipeline, TextInput


def run(coro):
    return asyncio.run(coro)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("kind", "label"),
    [
        ("text", "raw-text"),
        ("document", "document-input"),
        ("wikipedia", "Wikipedia:Cat"),
        ("llm_output", "llm:gpt"),
    ],
)
def test_pipeline_accepts_each_supported_input_kind(kind, label):
    source = TextInput(
        text="Cats are mammals.",
        id="source-a",
        kind=kind,
        label=label,
        language="en",
    )
    target = TextInput(
        text="Cats are animals.",
        id="source-b",
        kind="text",
        label="comparison-text",
        language="en",
    )

    result = run(ComparisonPipeline().run(source, target, ["fake"]))

    assert result.ok
    assert result.source.kind == kind
    assert result.source.label == label
    assert result.source.text == "Cats are mammals."
    assert result.source.language == "en"
    assert result.target.kind == "text"
    assert result.strategy_names == ["fake"]


@pytest.mark.unit
def test_pipeline_preserves_wikipedia_source_details():
    source = TextInput(
        text="The Eiffel Tower is in Paris.",
        id="wiki-source",
        kind="wikipedia",
        label="Wikipedia:Eiffel Tower",
        language="en",
        url="https://en.wikipedia.org/wiki/Eiffel_Tower",
        revision_id=12345,
    )
    target = TextInput(
        text="The Eiffel Tower is located in Paris.",
        id="text-source",
        kind="text",
    )

    result = run(ComparisonPipeline().run(source, target, ["fake"]))

    assert result.ok
    assert result.source.kind == "wikipedia"
    assert result.source.url == "https://en.wikipedia.org/wiki/Eiffel_Tower"
    assert result.source.revision_id == 12345


@pytest.mark.unit
def test_pipeline_preserves_llm_output_metadata():
    source = TextInput(
        text="Paris is the capital of France.",
        id="llm-source",
        kind="llm_output",
        label="llm-output",
        language="en",
        metadata={"provider": "fake", "model": "test-model"},
    )
    target = TextInput(
        text="Paris is France's capital city.",
        id="reference",
        kind="text",
    )

    result = run(ComparisonPipeline().run(source, target, ["fake"]))

    assert result.ok
    assert result.source.kind == "llm_output"
    assert result.source.metadata["provider"] == "fake"
    assert result.source.metadata["model"] == "test-model"