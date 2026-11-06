"""Reads a Wikipedia article as plain reference text for API v2 comparisons.

This module only obtains the article. Choosing which passages support each
statement (evidence retrieval) is a separate step and is not done here.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit

from app.services.article_parser import article_fetcher, revision_fetcher

logger = logging.getLogger(__name__)

WIKIPEDIA_LICENSE = "CC BY-SA 4.0"


# Base class for failures to obtain a Wikipedia article.
class WikipediaSourceError(Exception):
    retryable = False

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# Raised when the article or revision does not exist or has no text.
class ArticleNotFoundError(WikipediaSourceError):
    pass


# Raised when Wikipedia could not be reached or answered with an error.
class WikipediaUnavailableError(WikipediaSourceError):
    retryable = True


# Which article to read: a language edition plus a title, or a specific revision.
@dataclass(frozen=True)
class ArticleRef:
    language: str
    title: str | None = None
    revision_id: int | None = None


# One article, with the plain text that statement spans and evidence refer to.
@dataclass(frozen=True)
class WikipediaArticle:
    title: str
    language: str
    text: str
    revision_id: int | None = None

    # Link to the article, or to the exact revision when one was requested.
    @property
    def url(self) -> str:
        page = quote(self.title.replace(" ", "_"), safe="()_,:'!-.")
        url = f"https://{self.language}.wikipedia.org/wiki/{page}"
        if self.revision_id is not None:
            url += f"?oldid={self.revision_id}"
        return url

    # Attribution that must accompany any reuse of the text (CC BY-SA).
    @property
    def attribution(self) -> str:
        revision = f" (revision {self.revision_id})" if self.revision_id else ""
        return (
            f'From the Wikipedia article "{self.title}"{revision}, '
            f"licensed under {WIKIPEDIA_LICENSE}."
        )


# Builds an ArticleRef from the fields of a v2 wikipedia source. The URL must already
# have passed the request model's Wikipedia URL check. Raises ValueError when the
# fields do not identify one article.
def article_ref(
    url: str | None,
    title: str | None,
    language: str | None,
    revision_id: int | None = None,
) -> ArticleRef:
    if url is not None:
        parts = urlsplit(url)
        url_language = (parts.hostname or "").split(".")[0]
        if language and language.lower() != url_language:
            raise ValueError(
                f"language '{language}' does not match the URL's language "
                f"'{url_language}'"
            )
        page = unquote(parts.path[len("/wiki/") :]).replace("_", " ").strip()
        return ArticleRef(language=url_language, title=page, revision_id=revision_id)
    if title is not None:
        if not language:
            raise ValueError("language is required when the article is given by title")
        return ArticleRef(
            language=language.lower(), title=title.strip(), revision_id=revision_id
        )
    raise ValueError("a wikipedia source needs a url or a title")


# The interface the v2 endpoints use to obtain an article, so tests and future
# readers (for example one that also returns section structure) can be swapped in.
class WikipediaReader(ABC):
    @abstractmethod
    async def read(self, ref: ArticleRef) -> WikipediaArticle: ...


# Reads articles through the existing v1 article parser (MediaWiki parse API).
# The text is the cleaned paragraph text of every section, joined by blank lines.
class ParsedArticleReader(WikipediaReader):
    async def read(self, ref: ArticleRef) -> WikipediaArticle:
        name = ref.title or f"revision {ref.revision_id}"
        try:
            if ref.revision_id is not None:
                article = await revision_fetcher(ref.revision_id, ref.language)
            else:
                article = await article_fetcher(ref.title, ref.language)
        # The parser uses httpx today; a pending fix switches it to requests, so any
        # error from the call is treated as Wikipedia being unavailable.
        except Exception as exc:
            response = getattr(exc, "response", None)
            if getattr(response, "status_code", None) == 404:
                raise ArticleNotFoundError(
                    f"Wikipedia article not found: {name} ({ref.language})"
                ) from exc
            logger.warning("could not read %s from Wikipedia: %r", name, exc)
            raise WikipediaUnavailableError(
                f"Wikipedia could not be reached for {name} ({ref.language})"
            ) from exc

        text = "\n\n".join(
            section.clean_content.strip()
            for section in article.sections
            if section.clean_content and section.clean_content.strip()
        )
        if not text:
            raise ArticleNotFoundError(
                f"Wikipedia article not found or has no text: {name} ({ref.language})"
            )
        title = ref.title or article.title or name
        return WikipediaArticle(
            title=title, language=ref.language, text=text, revision_id=ref.revision_id
        )
