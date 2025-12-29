from unittest.mock import patch, Mock
from app.models import (
    Citation,
    Reference,
    Section,
)
import pytest


class TestStructuredWikiRouter:
    """Tests for the structured_wiki router"""

    def test_get_structured_article_with_title(self, client, mock_article_parser):
        """Test fetching structured article by title"""
        with patch(
            "app.routers.structured_wiki.article_fetcher",
            side_effect=mock_article_parser,
        ):
            response = client.get(
                "/symmetry/v1/wiki/structured-article?query=Test_Article"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Test Article"
            assert data["lang"] == "en"
            assert "sections" in data
            assert "references" in data
            assert data["total_sections"] >= 0
            assert data["total_citations"] >= 0
            assert data["total_references"] >= 0

    def test_get_structured_article_with_url(self, client, mock_article_parser):
        """Test fetching structured article by URL"""
        with patch(
            "app.routers.structured_wiki.parse_wikipedia_url",
            return_value=("en", "Test"),
        ):
            with patch(
                "app.routers.structured_wiki.article_fetcher",
                side_effect=mock_article_parser,
            ):
                response = client.get(
                    "/symmetry/v1/wiki/structured-article?query=https://en.wikipedia.org/wiki/Test"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["title"] == "Test Article"

    def test_get_structured_article_missing_query(self, client):
        """Test structured article without query parameter"""
        response = client.get("/symmetry/v1/wiki/structured-article")

        assert response.status_code == 400

    def test_get_structured_article_with_language(self, client, mock_article_parser):
        """Test structured article with specified language"""
        with patch(
            "app.routers.structured_wiki.article_fetcher",
            side_effect=mock_article_parser,
        ):
            response = client.get(
                "/symmetry/v1/wiki/structured-article?query=Test&lang=fr"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["lang"] == "fr"

    def test_get_structured_article_with_citations(
        self, client, mock_article_parser, mock_article_parser_factory
    ):
        """Test structured article returns citation data"""
        from app.models import Citation

        def mock_citations_fetcher(title="Test", lang="en"):
            article = Mock()
            article.title = "Test Article"
            article.lang = lang
            article.source = "wikipedia"
            article.sections = [
                Section(
                    title="Introduction",
                    raw_content="Test content [1].",
                    clean_content="Test content.",
                    citations=[Citation(label="1", url="http://example.com")],
                    citation_position=["1"],
                )
            ]
            article.references = [
                Reference(label="Reference 1", url="http://example.com")
            ]
            return article

        with patch(
            "app.routers.structured_wiki.article_fetcher",
            side_effect=mock_citations_fetcher,
        ):
            response = client.get("/symmetry/v1/wiki/structured-article?query=Test")

            assert response.status_code == 200
            data = response.json()
            assert data["total_citations"] == 1
            assert data["total_references"] == 1

    def test_get_structured_article_default_language(self, client, mock_article_parser):
        """Test that English is default language for structured articles"""
        with patch(
            "app.routers.structured_wiki.article_fetcher",
            side_effect=mock_article_parser,
        ):
            response = client.get("/symmetry/v1/wiki/structured-article?query=Test")

            assert response.status_code == 200
            data = response.json()
            assert data["lang"] == "en"

    def test_get_structured_section(self, client, mock_article_parser):
        """Test fetching specific section from article"""
        with patch(
            "app.routers.structured_wiki.article_fetcher",
            return_value=mock_article_parser(),
        ):
            response = client.get(
                "/symmetry/v1/wiki/structured-section?query=Test&section_title=Introduction"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Introduction"
            assert "word_count" in data
            assert "citation_count" in data

    def test_get_structured_section_not_found(self, client, mock_article_parser):
        """Test requesting non-existent section returns 404"""
        with patch(
            "app.routers.structured_wiki.article_fetcher",
            return_value=mock_article_parser(),
        ):
            response = client.get(
                "/symmetry/v1/wiki/structured-section?query=Test&section_title=NonExistent"
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_structured_section_with_url(self, client, mock_article_parser):
        """Test structured section with URL parameter"""
        with patch(
            "app.routers.structured_wiki.parse_wikipedia_url",
            return_value=("en", "Test"),
        ):
            with patch(
                "app.routers.structured_wiki.article_fetcher",
                return_value=mock_article_parser(),
            ):
                response = client.get(
                    "/symmetry/v1/wiki/structured-section?query=https://en.wikipedia.org/wiki/Test&section_title=Introduction"
                )

                assert response.status_code == 200

    def test_get_structured_section_missing_section_title(self, client):
        """Test structured section without section_title parameter"""
        response = client.get("/symmetry/v1/wiki/structured-section?query=Test")

        assert response.status_code == 422

    def test_get_citation_analysis(self, client):
        """Test citation analysis endpoint"""
        article = Mock()
        article.title = "Test Article"
        article.sections = [
            Mock(
                citations=[
                    Citation(label="1", url="http://example.com/ref1"),
                    Citation(label="2", url="http://example.com/ref1"),
                    Citation(label="3", url="http://example.com/ref2"),
                ]
            ),
            Mock(citations=[Citation(label="4", url="http://example.com/ref3")]),
        ]

        with patch("app.routers.structured_wiki.article_fetcher", return_value=article):
            response = client.get("/symmetry/v1/wiki/citation-analysis?query=Test")

            assert response.status_code == 200
            data = response.json()
            assert data["total_citations"] == 4
            assert data["unique_targets"] == 3
            assert "most_cited_articles" in data
            assert len(data["most_cited_articles"]) <= 10

    def test_get_citation_analysis_no_citations(self, client):
        """Test citation analysis for article with no citations"""
        article = Mock()
        article.title = "Test Article"
        article.sections = [Mock(citations=None)]

        with patch("app.routers.structured_wiki.article_fetcher", return_value=article):
            response = client.get("/symmetry/v1/wiki/citation-analysis?query=Test")

            assert response.status_code == 200
            data = response.json()
            assert data["total_citations"] == 0
            assert data["unique_targets"] == 0

    def test_get_citation_analysis_most_cited(self, client):
        """Test that most_cited_articles is properly sorted"""
        article = Mock()
        article.title = "Test Article"
        article.sections = [
            Mock(
                citations=[
                    Citation(label="Ref1", url="http://example.com/1"),
                    Citation(label="Ref1", url="http://example.com/1"),
                    Citation(label="Ref1", url="http://example.com/1"),
                    Citation(label="Ref2", url="http://example.com/2"),
                ]
            )
        ]

        with patch("app.routers.structured_wiki.article_fetcher", return_value=article):
            response = client.get("/symmetry/v1/wiki/citation-analysis?query=Test")

            assert response.status_code == 200
            data = response.json()
            most_cited = data["most_cited_articles"]
            assert len(most_cited) > 0
            assert most_cited[0]["title"] == "Ref1"
            assert most_cited[0]["count"] == 3

    def test_get_reference_analysis(self, client):
        """Test reference analysis endpoint"""
        article = Mock()
        article.title = "Test Article"
        article.sections = [
            Mock(clean_content="This is a test article with some content."),
        ]
        article.references = [
            Reference(label="Ref1", url="http://example.com/1"),
            Reference(label="Ref2", url="http://example.com/2"),
            Reference(label="Ref3", id="ref3", url=None),
        ]

        with patch("app.routers.structured_wiki.article_fetcher", return_value=article):
            response = client.get("/symmetry/v1/wiki/reference-analysis?query=Test")

            assert response.status_code == 200
            data = response.json()
            assert data["total_references"] == 3
            assert data["references_with_urls"] == 2
            assert "reference_density" in data

    def test_get_reference_analysis_no_references(self, client):
        """Test reference analysis for article with no references"""
        article = Mock()
        article.title = "Test Article"
        article.sections = [Mock(clean_content="Test content.")]
        article.references = []

        with patch("app.routers.structured_wiki.article_fetcher", return_value=article):
            response = client.get("/symmetry/v1/wiki/reference-analysis?query=Test")

            assert response.status_code == 200
            data = response.json()
            assert data["total_references"] == 0
            assert data["references_with_urls"] == 0

    def test_get_reference_analysis_density(self, client):
        """Test reference density calculation"""
        article = Mock()
        article.title = "Test Article"
        # 10 words total, 5 references = 500 references per 1000 words
        article.sections = [Mock(clean_content="Test content words.")]
        article.references = [
            Reference(label=str(i), url="http://example.com") for i in range(5)
        ]

        with patch("app.routers.structured_wiki.article_fetcher", return_value=article):
            response = client.get("/symmetry/v1/wiki/reference-analysis?query=Test")

            assert response.status_code == 200
            data = response.json()
            assert data["reference_density"] > 0

    def test_parse_wikipedia_url_success(self):
        """Test successful Wikipedia URL parsing"""
        from app.routers.structured_wiki import parse_wikipedia_url
        import asyncio

        async def test_parse():
            lang, title = await parse_wikipedia_url(
                "https://en.wikipedia.org/wiki/Test_Article"
            )
            assert lang == "en"
            assert title == "Test Article"

        asyncio.run(test_parse())

    def test_parse_wikipedia_url_invalid_domain(self):
        """Test Wikipedia URL parsing with invalid domain"""
        from app.routers.structured_wiki import parse_wikipedia_url
        import asyncio

        async def test_parse():
            with pytest.raises(ValueError) as exc_info:
                await parse_wikipedia_url("https://example.com/wiki/Test")
            assert "wikipedia" in str(exc_info.value).lower()

        asyncio.run(test_parse())

    def test_parse_wikipedia_url_invalid_language(self):
        """Test Wikipedia URL parsing with invalid language code"""
        from app.routers.structured_wiki import parse_wikipedia_url
        import asyncio

        async def test_parse():
            with pytest.raises(ValueError) as exc_info:
                await parse_wikipedia_url(
                    "https://invalidlangcode.wikipedia.org/wiki/Test"
                )
            assert "language" in str(exc_info.value).lower()

        asyncio.run(test_parse())
