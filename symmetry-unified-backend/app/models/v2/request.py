"""Request models for API v2 (schema section 4).

Validation here covers the request rules of the schema. Checks that need the
server's registries (unknown engine ids, engines that cannot serve a
strategy) happen when the request is handled, not here.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from app.models.v2.common import (
    ComparisonMode,
    Direction,
    Score,
    SourceKind,
    StrategyId,
    V2Model,
)

# Content fields: each source sets exactly one of them (rule 2).
_CONTENT_FIELDS = ("text", "url", "title", "generate_with")

# Fields only allowed on Wikipedia sources (rule 3).
_WIKIPEDIA_ONLY_FIELDS = ("url", "title", "revision_id")

# Language subdomains, optionally mobile: en.wikipedia.org, fr.m.wikipedia.org.
_WIKIPEDIA_HOST = re.compile(r"^[a-z0-9-]+(\.m)?\.wikipedia\.org$")

# Source kinds each mode accepts (rule 5).
_MODE_KINDS: dict[str, set[str]] = {
    "text_vs_text": {"text", "document"},
    "llm_vs_llm": {"llm_output"},
    "llm_vs_wikipedia": {"llm_output", "wikipedia"},
}


def is_wikipedia_article_url(url: str) -> bool:
    """Return True if ``url`` points to a Wikipedia article.

    The server never fetches other URLs, so this check is what prevents the
    API from being used to reach internal or third-party addresses.
    """
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    return (
        parts.scheme in ("http", "https")
        and parts.hostname is not None
        and _WIKIPEDIA_HOST.match(parts.hostname) is not None
        and parts.username is None
        and parts.password is None
        and port is None
        and parts.path.startswith("/wiki/")
        and len(parts.path) > len("/wiki/")
    )


class SourceInput(V2Model):
    """One source to compare, as sent by the client."""

    id: str = Field(min_length=1, description="Unique in the request")
    kind: SourceKind
    language: str | None = Field(
        default=None,
        description="ISO 639-1 code. null means detect, or take it from the Wikipedia URL",
    )
    text: str | None = Field(default=None, description="Literal content")
    url: str | None = Field(default=None, description="Wikipedia article URL")
    title: str | None = Field(
        default=None, description="Wikipedia article title (with language)"
    )
    revision_id: int | None = Field(
        default=None, description="A specific Wikipedia revision. null means the latest"
    )
    generate_with: str | None = Field(
        default=None, description="Engine id that generates this source from prompt"
    )

    @model_validator(mode="after")
    def _check_fields_for_kind(self) -> SourceInput:
        content = [name for name in _CONTENT_FIELDS if getattr(self, name) is not None]
        if len(content) != 1:
            raise ValueError(
                f"source '{self.id}' must set exactly one of "
                f"{', '.join(_CONTENT_FIELDS)}; got {content or 'none'}"
            )

        if self.kind != "wikipedia":
            misplaced = [
                name
                for name in _WIKIPEDIA_ONLY_FIELDS
                if getattr(self, name) is not None
            ]
            if misplaced:
                raise ValueError(
                    f"source '{self.id}': {', '.join(misplaced)} only allowed for "
                    "kind 'wikipedia'"
                )

        if self.url is not None and not is_wikipedia_article_url(self.url):
            raise ValueError(
                f"source '{self.id}': url must be a Wikipedia article URL; "
                "send other content as text"
            )

        if self.generate_with is not None and self.kind != "llm_output":
            raise ValueError(
                f"source '{self.id}': generate_with only allowed for kind 'llm_output'"
            )
        return self


class ComparisonOptions(V2Model):
    """Optional settings for a comparison. null means the server default."""

    similarity_threshold: Score | None = None
    partial_threshold: Score | None = Field(
        default=None, description="Lower band for 'partial'; below similarity_threshold"
    )
    direction: Direction | None = None
    pivot_language: str | None = Field(
        default=None, description="Translate both texts to this language first"
    )
    include_source_text: bool = True
    include_blocks: bool = True
    include_evidence: bool = True
    include_word_diff: bool = False
    timeout_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_thresholds(self) -> ComparisonOptions:
        if (
            self.similarity_threshold is not None
            and self.partial_threshold is not None
            and self.partial_threshold >= self.similarity_threshold
        ):
            raise ValueError(
                "partial_threshold must be lower than similarity_threshold"
            )
        return self


class ComparisonRequest(V2Model):
    """The request body accepted by every v2 comparison endpoint."""

    mode: ComparisonMode
    sources: list[SourceInput] = Field(min_length=2)
    prompt: str | None = Field(
        default=None, description="Prompt sent to every source that uses generate_with"
    )
    engines: list[str] = Field(
        default_factory=list,
        description="Ids of the comparing engines. Empty means the server default",
    )
    strategy: StrategyId | None = Field(
        default=None,
        description=(
            "Strategy id from the server's registry, e.g. 'semantic_similarity' "
            "or 'factual_consistency'. null means the server default for the mode"
        ),
    )
    options: ComparisonOptions = Field(default_factory=ComparisonOptions)

    @model_validator(mode="after")
    def _check_sources(self) -> ComparisonRequest:
        ids = [source.id for source in self.sources]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"source ids must be unique; repeated: {duplicates}")

        if self.prompt is None and any(
            s.generate_with is not None for s in self.sources
        ):
            raise ValueError("prompt is required when a source uses generate_with")

        kinds = [source.kind for source in self.sources]
        allowed = _MODE_KINDS[self.mode]
        wrong = sorted({kind for kind in kinds if kind not in allowed})
        if wrong:
            raise ValueError(
                f"mode '{self.mode}' does not accept source kinds {wrong}; "
                f"allowed: {sorted(allowed)}"
            )
        if self.mode == "llm_vs_wikipedia" and sorted(kinds) != [
            "llm_output",
            "wikipedia",
        ]:
            raise ValueError(
                "mode 'llm_vs_wikipedia' takes exactly one 'llm_output' and one "
                "'wikipedia' source"
            )
        return self
