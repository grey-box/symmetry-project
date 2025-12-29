from unittest.mock import patch, Mock
from fastapi import HTTPException
import pytest


class TestWikiArticlesRouter:
    """Tests for the wiki_articles router"""

    def test_get_article_with_title(self, client, mock_wikipediaapi):
        """Test fetching an article by title"""
        with patch(
            "app.routers.wiki_articles.wikipediaapi.Wikipedia",
            return_value=mock_wikipediaapi,
        ):
            with patch("app.routers.wiki_articles.validate_language_code"):
                with patch(
                    "app.routers.wiki_articles.validate_url",
                    return_value=("en", "Test_Article"),
                ):
                    response = client.get(
                        "/symmetry/v1/wiki/articles?query=Test_Article&lang=en"
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "sourceArticle" in data
                    assert "articleLanguages" in data
                    assert isinstance(data["articleLanguages"], list)

    def test_get_article_with_url(self, client, mock_wikipediaapi):
        """Test fetching an article by URL"""
        from unittest.mock import AsyncMock

        with patch(
            "app.routers.wiki_articles.wikipediaapi.Wikipedia",
            return_value=mock_wikipediaapi,
        ):
            with patch(
                "app.routers.wiki_articles.validate_url",
                new=AsyncMock(return_value=("en", "Test_Article")),
            ):
                with patch("app.routers.wiki_articles.validate_language_code"):
                    response = client.get(
                        "/symmetry/v1/wiki/articles?query=https://en.wikipedia.org/wiki/Test_Article"
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "sourceArticle" in data

    def test_get_article_no_query(self, client):
        """Test fetching article without query parameter returns 400"""
        response = client.get("/symmetry/v1/wiki/articles")

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_get_article_not_found(self, client, mock_wikipediaapi):
        """Test fetching non-existent article returns 404"""
        mock_wikipediaapi.page.return_value.exists.return_value = False

        with patch(
            "app.routers.wiki_articles.wikipediaapi.Wikipedia",
            return_value=mock_wikipediaapi,
        ):
            with patch(
                "app.routers.wiki_articles.validate_url",
                return_value=("en", "NonExistent"),
            ):
                with patch("app.routers.wiki_articles.validate_language_code"):
                    response = client.get(
                        "/symmetry/v1/wiki/articles?query=NonExistent&lang=en"
                    )

                    assert response.status_code == 404
                    assert "not found" in response.json()["detail"].lower()

    def test_get_article_with_cache(self, client, mock_cache):
        """Test that cached articles are returned"""
        with patch(
            "app.routers.wiki_articles.get_cached_article",
            side_effect=mock_cache.get_cached_article,
        ):
            with patch(
                "app.routers.wiki_articles.set_cached_article",
                side_effect=mock_cache.set_cached_article,
            ):
                with patch("app.routers.wiki_articles.validate_language_code"):
                    mock_cache.cache["en.Test_Article"] = (
                        "Cached content",
                        ["fr", "es"],
                    )

                    response = client.get(
                        "/symmetry/v1/wiki/articles?query=Test_Article&lang=en"
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["sourceArticle"] == "Cached content"

    def test_validate_url_invalid_domain(self):
        """Test URL validation rejects non-Wikipedia domains"""
        from app.routers.wiki_articles import validate_url
        import asyncio

        async def test_invalid_domain():
            with pytest.raises(HTTPException) as exc_info:
                await validate_url("https://google.com/wiki/test")
            assert "wikipedia" in exc_info.value.detail.lower()

        asyncio.run(test_invalid_domain())

    def test_validate_url_invalid_language_code(self):
        """Test URL validation rejects invalid language codes"""
        from app.routers.wiki_articles import validate_url
        import asyncio

        async def test_invalid_lang():
            with pytest.raises(HTTPException) as exc_info:
                await validate_url("https://invalidlang.wikipedia.org/wiki/Test")
            assert "language code" in exc_info.value.detail.lower()

        asyncio.run(test_invalid_lang())

    def test_validate_url_success(self):
        """Test successful URL validation"""
        from app.routers.wiki_articles import validate_url
        import asyncio

        async def test_valid():
            with patch("app.routers.wiki_articles.validate_language_code"):
                lang, title = await validate_url(
                    "https://en.wikipedia.org/wiki/Test_Article"
                )
                assert lang == "en"
                assert title == "Test Article"

        asyncio.run(test_valid())

    def test_extract_wiki_title(self):
        """Test extraction of wiki title from URL path"""
        from app.routers.wiki_articles import _extract_wiki_title

        # Test simple title
        assert _extract_wiki_title("/wiki/Test_Article") == "Test Article"

        # Test title with underscores
        assert _extract_wiki_title("/wiki/Test_Article_Name") == "Test Article Name"

        # Test title with section fragment
        assert _extract_wiki_title("/wiki/Test_Article#Section") == "Test Article"

        # Test title with query parameters
        assert _extract_wiki_title("/wiki/Test_Article?action=edit") == "Test Article"

    def test_get_article_default_language(self, client, mock_wikipediaapi_fresh):
        """Test that English is default language when not specified"""
        with patch(
            "app.routers.wiki_articles.wikipediaapi.Wikipedia",
            return_value=mock_wikipediaapi_fresh,
        ):
            with patch("app.routers.wiki_articles.validate_language_code"):
                response = client.get("/symmetry/v1/wiki/articles?query=Test_Article")

                assert response.status_code == 200
                mock_wikipediaapi_fresh.page.assert_called_once()
