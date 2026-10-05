"""Split English LLM text into ordered, sentence-level statements."""

import re
from functools import lru_cache

import spacy
from spacy.language import Language

MAX_TEXT_LENGTH = 100_000
LIST_PREFIX = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+")


@lru_cache(maxsize=1)
def _segmenter() -> Language:
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def _blocks(text: str) -> list[str]:
    """Separate paragraphs/list items while joining wrapped lines."""
    blocks: list[str] = []
    lines: list[str] = []

    for line in text.splitlines():
        marker = LIST_PREFIX.match(line)

        if (not line.strip() or marker) and lines:
            blocks.append(" ".join(lines))
            lines = []

        if line.strip():
            content = line[marker.end() :] if marker else line
            if content.strip():
                lines.append(content.strip())

    if lines:
        blocks.append(" ".join(lines))

    return blocks


def split_statements(text: str) -> list[str]:
    """Return sentences in source order, preserving repeated statements."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"text must be at most {MAX_TEXT_LENGTH} characters")

    if not text.strip():
        return []

    statements: list[str] = []

    for block in _blocks(text):
        normalized = re.sub(r"\s+", " ", block)
        doc = _segmenter()(normalized)

        for sentence in doc.sents:
            content = sentence.text.strip()
            if any(character.isalnum() for character in content):
                statements.append(content)

    return statements
