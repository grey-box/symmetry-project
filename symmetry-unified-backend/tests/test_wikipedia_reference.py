"""Tests for reading a Wikipedia article as v2 reference text."""

import asyncio

import httpx
import pytest

from app.models.wiki.structure import Article, Section
from app.services import wikipedia_reference
from app.services.wikipedia_reference import (
    ArticleNotFoundError,
    ArticleRef,
    ParsedArticleReader,
    WikipediaArticle,
    WikipediaUnavailableError,
    article_ref,
)


def _section(title: str, content: str) -> Section:
    return Section(title=title, raw_content=content, clean_content=content)


def _article(*sections: Section, title: str = "Eiffel Tower") -> Article:
    return Article(
        title=title, lang="en", source="test", sections=list(sections), references=[]
    )


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://en.wikipedia.org/w/api.php")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


@pytest.mark.unit
class TestArticleRef:
    def test_reads_language_and_title_from_url(self):
        ref = article_ref("https://fr.wikipedia.org/wiki/Tour_Eiffel", None, None)
        assert ref == ArticleRef(language="fr", title="Tour Eiffel")

    def test_decodes_percent_encoded_titles(self):
        ref = article_ref("https://de.wikipedia.org/wiki/K%C3%B6ln", None, None)
        assert ref.title == "Köln"

    def test_mobile_url_uses_the_language_subdomain(self):
        ref = article_ref("https://en.m.wikipedia.org/wiki/Eiffel_Tower", None, None)
        assert ref.language == "en"

    def test_keeps_the_revision(self):
        ref = article_ref("https://en.wikipedia.org/wiki/Eiffel_Tower", None, None, 42)
        assert ref.revision_id == 42

    def test_rejects_a_language_that_contradicts_the_url(self):
        with pytest.raises(ValueError, match="does not match"):
            article_ref("https://en.wikipedia.org/wiki/Eiffel_Tower", None, "fr")

    def test_title_needs_a_language(self):
        with pytest.raises(ValueError, match="language is required"):
            article_ref(None, "Eiffel Tower", None)

    def test_title_with_language(self):
        assert article_ref(None, " Eiffel Tower ", "EN") == ArticleRef(
            language="en", title="Eiffel Tower"
        )


@pytest.mark.unit
class TestWikipediaArticle:
    def test_url_points_to_the_article(self):
        article = WikipediaArticle(title="Eiffel Tower", language="en", text="x")
        assert article.url == "https://en.wikipedia.org/wiki/Eiffel_Tower"

    def test_url_points_to_the_revision_when_one_is_set(self):
        article = WikipediaArticle(
            title="Eiffel Tower", language="en", text="x", revision_id=7
        )
        assert article.url.endswith("/wiki/Eiffel_Tower?oldid=7")
        assert "(revision 7)" in article.attribution

    def test_attribution_names_the_licence(self):
        article = WikipediaArticle(title="Eiffel Tower", language="en", text="x")
        assert "Eiffel Tower" in article.attribution
        assert "CC BY-SA 4.0" in article.attribution


@pytest.mark.unit
class TestParsedArticleReader:
    def _read(self, ref: ArticleRef) -> WikipediaArticle:
        return asyncio.run(ParsedArticleReader().read(ref))

    def test_joins_section_text_with_blank_lines(self, monkeypatch):
        async def fetch(title, lang):
            assert (title, lang) == ("Eiffel Tower", "en")
            return _article(
                _section("Lead section", "The tower is in Paris."),
                _section("Empty", "   "),
                _section("History", "It opened in 1889."),
            )

        monkeypatch.setattr(wikipedia_reference, "article_fetcher", fetch)
        article = self._read(ArticleRef(language="en", title="Eiffel Tower"))
        assert article.text == "The tower is in Paris.\n\nIt opened in 1889."
        assert article.title == "Eiffel Tower"
        assert article.revision_id is None

    def test_reads_a_specific_revision(self, monkeypatch):
        async def fetch_revision(revid, lang):
            assert (revid, lang) == (42, "en")
            return _article(_section("Lead section", "Old text."))

        monkeypatch.setattr(wikipedia_reference, "revision_fetcher", fetch_revision)
        article = self._read(
            ArticleRef(language="en", title="Eiffel Tower", revision_id=42)
        )
        assert article.text == "Old text."
        assert article.revision_id == 42

    def test_article_without_text_is_not_found(self, monkeypatch):
        async def fetch(title, lang):
            return _article()

        monkeypatch.setattr(wikipedia_reference, "article_fetcher", fetch)
        with pytest.raises(ArticleNotFoundError):
            self._read(ArticleRef(language="en", title="No Such Page"))

    def test_http_404_is_not_found(self, monkeypatch):
        async def fetch(title, lang):
            raise _http_error(404)

        monkeypatch.setattr(wikipedia_reference, "article_fetcher", fetch)
        with pytest.raises(ArticleNotFoundError):
            self._read(ArticleRef(language="en", title="Eiffel Tower"))

    @pytest.mark.parametrize(
        "error", [_http_error(403), httpx.ConnectError("offline"), RuntimeError("boom")]
    )
    def test_other_failures_mean_wikipedia_is_unavailable(self, monkeypatch, error):
        async def fetch(title, lang):
            raise error

        monkeypatch.setattr(wikipedia_reference, "article_fetcher", fetch)
        with pytest.raises(WikipediaUnavailableError) as caught:
            self._read(ArticleRef(language="en", title="Eiffel Tower"))
        assert caught.value.retryable
