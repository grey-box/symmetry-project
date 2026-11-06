"""Check English statements against passages from one Wikipedia article."""

import math
import re
from urllib.parse import quote

from app.engines.base import ModelAdapter
from app.services.statement_splitting import split_statements
from app.strategies.base import StrategyInput
from app.strategies.factual_consistency import FactualConsistencyStrategy

PASSAGE_CHARS = 2000
MAX_STATEMENTS = 100
MAX_ARTICLE_CHARS = 500_000

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "with",
}


class WikipediaEvidenceError(ValueError):
    """The article could not provide usable reference text."""


def _terms(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold())) - STOP_WORDS


def _passages(article) -> list[dict]:
    passages = []
    total = sum(len(section.clean_content) for section in article.sections)
    if total > MAX_ARTICLE_CHARS:
        raise WikipediaEvidenceError("Article exceeds the supported size limit")

    for section in article.sections:
        text = section.clean_content.strip()
        start = 0
        while start < len(text):
            end = min(start + PASSAGE_CHARS, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start, end)
                if boundary > start:
                    end = boundary
            passage = text[start:end].strip()
            if passage:
                passages.append({"section": section.title, "text": passage})
            start = end

    return passages


def _select_passages(statement: str, passages: list[dict]) -> list[dict]:
    terms = _terms(statement)
    ranked = sorted(
        passages,
        key=lambda passage: len(terms & _terms(passage["text"])),
        reverse=True,
    )
    return ranked[:3]


async def resolve_and_fetch_article(query: str, default_lang: str = "en"):
    """Load the Wikipedia dependencies only when fetching an article."""
    from app.services.router_utils import (
        resolve_and_fetch_article as fetch_article,
    )

    return await fetch_article(query, default_lang)


async def compare_with_wikipedia(
    text: str,
    query: str,
    adapter: ModelAdapter,
) -> dict:
    """Return service-level results; API v2 serialization belongs to the router."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Wikipedia title or URL must not be empty")

    statements = split_statements(text)
    if not statements:
        raise ValueError("Text must contain at least one statement")
    if len(statements) > MAX_STATEMENTS:
        raise ValueError(f"At most {MAX_STATEMENTS} statements are supported")

    article = await resolve_and_fetch_article(query.strip(), "en")
    if article.lang != "en":
        raise ValueError("This version supports English Wikipedia articles only")

    passages = _passages(article)
    if not passages:
        raise WikipediaEvidenceError("Wikipedia returned no usable article text")

    source_url = "https://en.wikipedia.org/wiki/" + quote(
        article.title.replace(" ", "_"), safe=""
    )
    strategy = FactualConsistencyStrategy(
        model_adapter=adapter,
        splitter=lambda value: [value],
        max_reference_chars=3 * PASSAGE_CHARS + 4,
    )

    rows = []
    for index, statement in enumerate(statements):
        selected = _select_passages(statement, passages)
        reference = "\n\n".join(passage["text"] for passage in selected)
        result = await strategy.compare(
            StrategyInput(source_text=reference, target_text=statement)
        )
        verdict = result.details["statements"][0]
        label = verdict["label"]
        confidence = verdict["confidence"]
        evidence = []
        reason = None

        evidence_quote = verdict["evidence"]
        if evidence_quote:
            for passage in selected:
                if evidence_quote in passage["text"]:
                    evidence.append(
                        {
                            "kind": "wikipedia_passage",
                            "text": evidence_quote,
                            "passage": passage["text"],
                            "section": passage["section"],
                            "url": source_url,
                        }
                    )
                    break

        if label in {"supported", "contradicted"} and not evidence:
            label = "unverifiable"
            confidence = None
            reason = "The model did not supply an exact verifiable evidence quote"
        elif confidence is None or not math.isfinite(confidence):
            label = "unverifiable"
            confidence = None
            reason = "The model did not supply a usable confidence score"

        rows.append(
            {
                "index": index,
                "text": statement,
                "label": label,
                "confidence": confidence,
                "evidence": evidence,
                "reason": reason,
                "retrieved_passages": selected,
                "reference_is_subset": len(selected) < len(passages),
            }
        )

    return {
        "source": {"title": article.title, "language": article.lang, "url": source_url},
        "model": adapter.get_model_name(),
        "score_basis": "model_reported",
        "retrieval_method": "word_overlap",
        "statements": rows,
    }
