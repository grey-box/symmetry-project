from unittest.mock import patch, Mock
from fastapi import HTTPException
import pytest


class TestComparisonRouter:
    """Tests for the comparison router"""

    def test_compare_articles_post_success(self, client, valid_compare_request):
        """Test successful POST request to compare articles"""
        mock_response = {
            "comparisons": [
                {
                    "left_article_array": ["Sentence 1", "Sentence 2"],
                    "right_article_array": ["Sentence 1", "Sentence 3"],
                    "left_article_missing_info_index": [1],
                    "right_article_extra_info_index": [1],
                }
            ]
        }

        with patch(
            "app.routers.comparison.perform_semantic_comparison",
            return_value=mock_response,
        ):
            response = client.post(
                "/symmetry/v1/articles/compare", json=valid_compare_request
            )

            assert response.status_code == 200
            data = response.json()
            assert "comparisons" in data
            assert len(data["comparisons"]) == 1

    def test_compare_articles_with_obama_data(
        self, client, sample_obama_text_a, sample_obama_text_b
    ):
        """Test comparison with real Obama article data"""
        request_data = {
            "article_text_blob_1": sample_obama_text_a,
            "article_text_blob_2": sample_obama_text_b,
            "article_text_blob_1_language": "en",
            "article_text_blob_2_language": "en",
            "comparison_threshold": 0.65,
            "model_name": "sentence-transformers/LaBSE",
        }

        mock_response = {
            "comparisons": [
                {
                    "left_article_array": sample_obama_text_a.split("\n"),
                    "right_article_array": sample_obama_text_b.split("\n"),
                    "left_article_missing_info_index": [2, 6],
                    "right_article_extra_info_index": [1, 5],
                }
            ]
        }

        with patch(
            "app.routers.comparison.perform_semantic_comparison",
            return_value=mock_response,
        ):
            response = client.post("/symmetry/v1/articles/compare", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert "comparisons" in data

    def test_compare_articles_missing_required_field(self, client):
        """Test comparison request missing required fields"""
        incomplete_request = {
            "article_text_blob_1": "First article",
        }

        response = client.post("/symmetry/v1/articles/compare", json=incomplete_request)

        assert response.status_code == 422

    def test_compare_articles_invalid_threshold(self, client, valid_compare_request):
        """Test comparison with invalid threshold value"""
        invalid_request = valid_compare_request.copy()
        invalid_request["comparison_threshold"] = 1.5

        response = client.post("/symmetry/v1/articles/compare", json=invalid_request)

        assert response.status_code == 422

    def test_compare_articles_invalid_language_length(
        self, client, valid_compare_request
    ):
        """Test comparison with invalid language code length"""
        invalid_request = valid_compare_request.copy()
        invalid_request["article_text_blob_1_language"] = "verylonglanguagecode"

        response = client.post("/symmetry/v1/articles/compare", json=invalid_request)

        assert response.status_code == 422

    def test_compare_semantic_get_success(self, client, valid_semantic_compare_request):
        """Test successful GET request for semantic comparison"""
        mock_response = {
            "comparisons": [
                {
                    "left_article_array": ["Sentence 1"],
                    "right_article_array": ["Sentence 2"],
                    "left_article_missing_info_index": [0],
                    "right_article_extra_info_index": [0],
                }
            ]
        }

        with patch(
            "app.routers.comparison.perform_semantic_comparison",
            return_value=mock_response,
        ):
            response = client.get(
                "/symmetry/v1/comparison/semantic",
                params=valid_semantic_compare_request,
            )

            assert response.status_code == 200
            data = response.json()
            assert "missing_info" in data or "comparisons" in data

    def test_compare_semantic_get_invalid_threshold(self, client):
        """Test semantic comparison GET with invalid threshold"""
        response = client.get(
            "/symmetry/v1/comparison/semantic",
            params={"text_a": "Test", "text_b": "Test", "similarity_threshold": 2.0},
        )

        assert response.status_code == 400

    def test_compare_semantic_get_invalid_model(self, client):
        """Test semantic comparison GET with invalid model name"""
        response = client.get(
            "/symmetry/v1/comparison/semantic",
            params={
                "text_a": "Test",
                "text_b": "Test",
                "model_name": "invalid-model-name",
            },
        )

        assert response.status_code == 404

    def test_compare_semantic_post_success(
        self, client, valid_semantic_compare_request
    ):
        """Test successful POST request for semantic comparison"""
        mock_response = {
            "comparisons": [
                {
                    "left_article_array": ["Sentence 1"],
                    "right_article_array": ["Sentence 2"],
                    "left_article_missing_info_index": [0],
                    "right_article_extra_info_index": [0],
                }
            ]
        }

        with patch(
            "app.routers.comparison.perform_semantic_comparison",
            return_value=mock_response,
        ):
            response = client.post(
                "/symmetry/v1/comparison/semantic", json=valid_semantic_compare_request
            )

            assert response.status_code == 200
            data = response.json()
            assert "missing_info" in data or "comparisons" in data

    def test_compare_semantic_post_invalid_threshold(
        self, client, valid_semantic_compare_request
    ):
        """Test semantic comparison POST with invalid threshold"""
        invalid_request = valid_semantic_compare_request.copy()
        invalid_request["similarity_threshold"] = 1.5

        response = client.post("/symmetry/v1/comparison/semantic", json=invalid_request)

        assert response.status_code == 422

    def test_compare_semantic_post_invalid_model(
        self, client, valid_semantic_compare_request
    ):
        """Test semantic comparison POST with invalid model name"""
        invalid_request = valid_semantic_compare_request.copy()
        invalid_request["model_name"] = "invalid-model-name"

        response = client.post("/symmetry/v1/comparison/semantic", json=invalid_request)

        assert response.status_code == 404

    def test_wiki_translate_with_url(self, client):
        """Test wiki translation with URL"""
        mock_wiki = Mock()
        mock_page = Mock()
        mock_page.exists.return_value = True
        mock_page.text = "Translated content"
        mock_page.langlinks = {"fr": "Article_Test"}
        mock_page.title.return_value = "Test Article"
        mock_wiki.page.return_value = mock_page

        with patch("wikipediaapi.Wikipedia", return_value=mock_wiki):
            with patch(
                "app.services.wiki_utils.get_translation", return_value="Article_Test"
            ):
                response = client.get(
                    "/symmetry/v1/wiki_translate/source_article",
                    params={
                        "url": "https://en.wikipedia.org/wiki/Test_Article",
                        "language": "fr",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "translatedArticle" in data

    def test_wiki_translate_with_title(self, client):
        """Test wiki translation with title"""
        mock_wiki = Mock()
        mock_page = Mock()
        mock_page.exists.return_value = True
        mock_page.text = "Translated content"
        mock_page.langlinks = {"fr": "Article_Test"}
        mock_page.title.return_value = "Test Article"
        mock_wiki.page.return_value = mock_page

        with patch("wikipediaapi.Wikipedia", return_value=mock_wiki):
            with patch(
                "app.services.wiki_utils.get_translation", return_value="Article_Test"
            ):
                response = client.get(
                    "/symmetry/v1/wiki_translate/source_article",
                    params={"title": "Test_Article", "language": "fr"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "translatedArticle" in data

    def test_wiki_translate_missing_params(self, client):
        """Test wiki translation without required parameters"""
        response = client.get("/symmetry/v1/wiki_translate/source_article")

        assert response.status_code == 400

    def test_wiki_translate_article_not_found(self, client):
        """Test wiki translation for non-existent article"""
        mock_wiki = Mock()
        mock_page = Mock()
        mock_page.exists.return_value = False
        mock_wiki.page.return_value = mock_page

        with patch("wikipediaapi.Wikipedia", return_value=mock_wiki):
            response = client.get(
                "/symmetry/v1/wiki_translate/source_article",
                params={"title": "NonExistent", "language": "en"},
            )

            assert response.status_code == 404
