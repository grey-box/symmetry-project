from unittest.mock import patch, Mock
from fastapi import HTTPException
import pytest


class TestStructuralAnalysisRouter:
    """Tests for the structural_analysis router"""

    @patch("app.routers.structural_analysis.table_analysis.analyze_tables")
    @patch("app.routers.structural_analysis.header_analysis.count_html_headers")
    @patch("app.routers.structural_analysis.infobox_analysis.analyze_infobox")
    @patch(
        "app.routers.structural_analysis.citation_analysis.extract_citation_from_wikitext"
    )
    @patch("app.routers.structural_analysis.image_analysis.get_image_count")
    def test_get_results_success(
        self,
        mock_image_count,
        mock_citation_analysis,
        mock_infobox_analysis,
        mock_header_analysis,
        mock_table_analysis,
        client,
        mock_structural_analysis_data,
    ):
        """Test successful structural analysis"""
        mock_table_analysis.return_value = mock_structural_analysis_data[
            "table_analysis"
        ]
        mock_header_analysis.return_value = mock_structural_analysis_data[
            "header_analysis"
        ]
        mock_infobox_analysis.return_value = mock_structural_analysis_data["info_box"]
        mock_citation_analysis.return_value = mock_structural_analysis_data["citations"]
        mock_image_count.return_value = 5

        with patch(
            "app.routers.structural_analysis.wiki_utils.get_translation",
            return_value="Test_Article",
        ):
            response = client.get("/operations/en/Test_Article")

            assert response.status_code == 200
            data = response.json()
            assert data["article"] == "Test Article"
            assert data["source_language_code"] == "en"
            assert "scores_by_language" in data
            assert len(data["scores_by_language"]) == 6

    @patch("app.routers.structural_analysis.table_analysis.analyze_tables")
    @patch("app.routers.structural_analysis.header_analysis.count_html_headers")
    @patch("app.routers.structural_analysis.infobox_analysis.analyze_infobox")
    @patch(
        "app.routers.structural_analysis.citation_analysis.extract_citation_from_wikitext"
    )
    @patch("app.routers.structural_analysis.image_analysis.get_image_count")
    def test_get_results_with_translations(
        self,
        mock_image_count,
        mock_citation_analysis,
        mock_infobox_analysis,
        mock_header_analysis,
        mock_table_analysis,
        client,
        mock_structural_analysis_data,
    ):
        """Test structural analysis with translated articles"""
        mock_table_analysis.return_value = mock_structural_analysis_data[
            "table_analysis"
        ]
        mock_header_analysis.return_value = mock_structural_analysis_data[
            "header_analysis"
        ]
        mock_infobox_analysis.return_value = mock_structural_analysis_data["info_box"]
        mock_citation_analysis.return_value = mock_structural_analysis_data["citations"]
        mock_image_count.return_value = 5

        # Mock translations for different languages
        translations = {
            "fr": "Article_de_test",
            "es": "Articulo_de_prueba",
            "de": "Testartikel",
            "pt": "Artigo_de_teste",
            "ar": "مقال_اختبار",
        }

        def get_translation_side_effect(title, source_lang, target_lang):
            return translations.get(target_lang)

        with patch(
            "app.routers.structural_analysis.wiki_utils.get_translation",
            side_effect=get_translation_side_effect,
        ):
            response = client.get("/operations/en/Test_Article")

            assert response.status_code == 200
            data = response.json()
            assert len(data["scores_by_language"]) == 6

    @patch("app.routers.structural_analysis.table_analysis.analyze_tables")
    @patch("app.routers.structural_analysis.header_analysis.count_html_headers")
    @patch("app.routers.structural_analysis.infobox_analysis.analyze_infobox")
    @patch(
        "app.routers.structural_analysis.citation_analysis.extract_citation_from_wikitext"
    )
    @patch("app.routers.structural_analysis.image_analysis.get_image_count")
    def test_get_results_missing_translation(
        self,
        mock_image_count,
        mock_citation_analysis,
        mock_infobox_analysis,
        mock_header_analysis,
        mock_table_analysis,
        client,
        mock_structural_analysis_data,
    ):
        """Test structural analysis when translation fails"""
        mock_table_analysis.return_value = mock_structural_analysis_data[
            "table_analysis"
        ]
        mock_header_analysis.return_value = mock_structural_analysis_data[
            "header_analysis"
        ]
        mock_infobox_analysis.return_value = mock_structural_analysis_data["info_box"]
        mock_citation_analysis.return_value = mock_structural_analysis_data["citations"]
        mock_image_count.return_value = 5

        # Return None for some translations to simulate failure
        def get_translation_side_effect(title, source_lang, target_lang):
            if target_lang == "fr":
                return None
            return f"{target_lang}_Test_Article"

        with patch(
            "app.routers.structural_analysis.wiki_utils.get_translation",
            side_effect=get_translation_side_effect,
        ):
            response = client.get("/operations/en/Test_Article")

            assert response.status_code == 200
            data = response.json()
            # Check that French has an error
            french_score = next(
                (s for s in data["scores_by_language"] if s["lang_code"] == "fr"), None
            )
            assert french_score is not None
            assert french_score["error"] is not None
            assert french_score["score"] == -1

    @patch("app.routers.structural_analysis.table_analysis.analyze_tables")
    def test_get_results_table_analysis_failure(self, mock_table_analysis, client):
        """Test structural analysis when table analysis fails"""
        mock_table_analysis.side_effect = HTTPException(
            status_code=500, detail="Table analysis failed"
        )

        with patch(
            "app.routers.structural_analysis.wiki_utils.get_translation",
            return_value="Test",
        ):
            response = client.get("/operations/en/Test_Article")

            assert response.status_code == 200
            data = response.json()
            # Check that English has an error
            english_score = next(
                (s for s in data["scores_by_language"] if s["lang_code"] == "en"), None
            )
            assert english_score is not None
            assert "error" in english_score

    def test_get_results_missing_title(self, client):
        """Test structural analysis with missing title"""
        response = client.get("/operations/en/")

        assert response.status_code == 404 or response.status_code == 422

    def test_get_results_missing_language(self, client):
        """Test structural analysis with missing language code"""
        response = client.get("/operations//Test_Article")

        assert response.status_code == 404

    @patch("app.routers.structural_analysis.table_analysis.analyze_tables")
    @patch("app.routers.structural_analysis.header_analysis.count_html_headers")
    @patch("app.routers.structural_analysis.infobox_analysis.analyze_infobox")
    @patch(
        "app.routers.structural_analysis.citation_analysis.extract_citation_from_wikitext"
    )
    @patch("app.routers.structural_analysis.image_analysis.get_image_count")
    def test_get_results_authority_article_detection(
        self,
        mock_image_count,
        mock_citation_analysis,
        mock_infobox_analysis,
        mock_header_analysis,
        mock_table_analysis,
        client,
        mock_structural_analysis_data,
    ):
        """Test that authority article is properly identified"""
        from app.models import (
            TableResponse,
            HeaderCount,
            InfoBoxResponse,
            CitationAnalysisResponse,
        )

        # Create different data for each language to test authority detection
        def create_analysis_data(score_multiplier):
            return {
                "table_analysis": TableResponse(
                    number_of_tables=2 * score_multiplier,
                    individual_table_information=[],
                    language="en",
                ),
                "header_analysis": HeaderCount(
                    h1_count=1 * score_multiplier,
                    h2_count=5 * score_multiplier,
                    h3_count=10 * score_multiplier,
                    h4_count=0,
                    h5_count=0,
                    h6_count=0,
                ),
                "info_box": InfoBoxResponse(
                    total_attributes=10 * score_multiplier, individual_infobox_data=[]
                ),
                "citations": CitationAnalysisResponse(
                    citations_with_doi=5 * score_multiplier,
                    citations_with_isbn=2 * score_multiplier,
                    see_also_links=3 * score_multiplier,
                    external_links=10 * score_multiplier,
                    page_title="Test",
                    language="en",
                    total_citations=20 * score_multiplier,
                ),
            }

        def side_effect(title, lang):
            multiplier = {"en": 2, "fr": 1, "es": 1, "de": 1, "pt": 1, "ar": 1}.get(
                lang, 1
            )
            data = create_analysis_data(multiplier)
            return (
                data["table_analysis"],
                data["header_analysis"],
                data["info_box"],
                data["citations"],
            )

        mock_table_analysis.side_effect = lambda t, l: side_effect(t, l)[0]
        mock_header_analysis.side_effect = lambda t, l: side_effect(t, l)[1]
        mock_infobox_analysis.side_effect = lambda t, l: side_effect(t, l)[2]
        mock_citation_analysis.side_effect = lambda t, l: side_effect(t, l)[3]
        mock_image_count.return_value = 5

        with patch(
            "app.routers.structural_analysis.wiki_utils.get_translation",
            return_value="Test",
        ):
            response = client.get("/operations/en/Test_Article")

            assert response.status_code == 200
            data = response.json()
            # English should be the authority article (highest score)
            english_score = next(
                (s for s in data["scores_by_language"] if s["lang_code"] == "en"), None
            )
            assert english_score is not None
            assert english_score["is_authority_article"] is True

    @patch("app.routers.structural_analysis.table_analysis.analyze_tables")
    @patch("app.routers.structural_analysis.header_analysis.count_html_headers")
    @patch("app.routers.structural_analysis.infobox_analysis.analyze_infobox")
    @patch(
        "app.routers.structural_analysis.citation_analysis.extract_citation_from_wikitext"
    )
    @patch("app.routers.structural_analysis.image_analysis.get_image_count")
    def test_get_results_score_calculation(
        self,
        mock_image_count,
        mock_citation_analysis,
        mock_infobox_analysis,
        mock_header_analysis,
        mock_table_analysis,
        client,
        mock_structural_analysis_data,
    ):
        """Test that scores are properly calculated"""
        mock_table_analysis.return_value = mock_structural_analysis_data[
            "table_analysis"
        ]
        mock_header_analysis.return_value = mock_structural_analysis_data[
            "header_analysis"
        ]
        mock_infobox_analysis.return_value = mock_structural_analysis_data["info_box"]
        mock_citation_analysis.return_value = mock_structural_analysis_data["citations"]
        mock_image_count.return_value = 5

        with patch(
            "app.routers.structural_analysis.wiki_utils.get_translation",
            return_value="Test",
        ):
            response = client.get("/operations/en/Test_Article")

            assert response.status_code == 200
            data = response.json()
            english_score = next(
                (s for s in data["scores_by_language"] if s["lang_code"] == "en"), None
            )
            assert english_score is not None
            # Score should be positive
            assert english_score["score"] >= 0
            assert english_score["is_user_language"] is True

    def test_calculate_single_score(self):
        """Test the score calculation formula"""
        from app.routers.structural_analysis import calculate_single_score
        from app.models import (
            TableResponse,
            HeaderCount,
            InfoBoxResponse,
            CitationAnalysisResponse,
            FinalAnalysisResponse,
        )

        response = FinalAnalysisResponse(
            title="Test",
            table_analysis=TableResponse(
                number_of_tables=2, individual_table_information=[], language="en"
            ),
            header_analysis=HeaderCount(
                h1_count=1, h2_count=5, h3_count=10, h4_count=0, h5_count=0, h6_count=0
            ),
            info_box=InfoBoxResponse(total_attributes=10, individual_infobox_data=[]),
            citations=CitationAnalysisResponse(
                citations_with_doi=5,
                citations_with_isbn=2,
                see_also_links=3,
                external_links=10,
                page_title="Test",
                language="en",
                total_citations=20,
            ),
            total_images=5,
        )

        score = calculate_single_score(response)

        # Expected: (0.5 * 20) + (0.3 * 2) + (0.10 * 10) + (0.05 * 16) + (0.05 * 5)
        # = 10 + 0.6 + 1 + 0.8 + 0.25 = 12.65
        assert score > 0
        assert score == pytest.approx(12.65, rel=1e-2)

    def test_calculate_single_score_zero_values(self):
        """Test score calculation with zero values"""
        from app.routers.structural_analysis import calculate_single_score
        from app.models import (
            TableResponse,
            HeaderCount,
            InfoBoxResponse,
            CitationAnalysisResponse,
            FinalAnalysisResponse,
        )

        response = FinalAnalysisResponse(
            title="Test",
            table_analysis=TableResponse(
                number_of_tables=0, individual_table_information=[], language="en"
            ),
            header_analysis=HeaderCount(
                h1_count=0, h2_count=0, h3_count=0, h4_count=0, h5_count=0, h6_count=0
            ),
            info_box=InfoBoxResponse(total_attributes=0, individual_infobox_data=[]),
            citations=CitationAnalysisResponse(
                citations_with_doi=0,
                citations_with_isbn=0,
                see_also_links=0,
                external_links=0,
                page_title="Test",
                language="en",
                total_citations=0,
            ),
            total_images=0,
        )

        score = calculate_single_score(response)

        assert score == 0

    def test_analyze_single_article_success(self):
        """Test analyzing a single article successfully"""
        from app.routers.structural_analysis import analyze_single_article
        from app.models import (
            TableResponse,
            HeaderCount,
            InfoBoxResponse,
            CitationAnalysisResponse,
        )

        with (
            patch(
                "app.routers.structural_analysis.table_analysis.analyze_tables"
            ) as mock_tables,
            patch(
                "app.routers.structural_analysis.header_analysis.count_html_headers"
            ) as mock_headers,
            patch(
                "app.routers.structural_analysis.infobox_analysis.analyze_infobox"
            ) as mock_infobox,
            patch(
                "app.routers.structural_analysis.citation_analysis.extract_citation_from_wikitext"
            ) as mock_citations,
            patch(
                "app.routers.structural_analysis.image_analysis.get_image_count"
            ) as mock_images,
        ):
            mock_tables.return_value = TableResponse(
                number_of_tables=2, individual_table_information=[], language="en"
            )
            mock_headers.return_value = HeaderCount(
                h1_count=1, h2_count=5, h3_count=10, h4_count=0, h5_count=0, h6_count=0
            )
            mock_infobox.return_value = InfoBoxResponse(
                total_attributes=10, individual_infobox_data=[]
            )
            mock_citations.return_value = CitationAnalysisResponse(
                citations_with_doi=5,
                citations_with_isbn=2,
                see_also_links=3,
                external_links=10,
                page_title="Test",
                language="en",
                total_citations=20,
            )
            mock_images.return_value = 5

            result = analyze_single_article("Test_Article", "en")

            assert result.title == "Test_Article"
            assert result.total_images == 5

    def test_analyze_single_article_failure(self):
        """Test analyzing a single article when it fails"""
        from app.routers.structural_analysis import analyze_single_article

        with patch(
            "app.routers.structural_analysis.table_analysis.analyze_tables"
        ) as mock_tables:
            mock_tables.side_effect = HTTPException(status_code=404, detail="Not found")

            with pytest.raises(HTTPException) as exc_info:
                analyze_single_article("NonExistent", "en")

            assert exc_info.value.status_code == 404
