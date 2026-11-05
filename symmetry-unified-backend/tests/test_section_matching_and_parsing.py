from unittest.mock import Mock, patch

import numpy as np

from app.models import Section
from app.services.article_parser import _parse_article_html
from app.services.section_comparison import _match_sections, _split_into_paragraphs


def _section(title: str) -> Section:
    return Section(title=title, raw_content="", clean_content="", citations=[])


class TestMatchSections:
    def test_optimal_assignment_avoids_greedy_stealing(self):
        """A's best cell (X, 0.77) must not steal X from B when A also fits Y."""
        source = [_section("A"), _section("B")]
        target = [_section("X"), _section("Y")]
        sim = np.array([[0.77, 0.60], [0.75, 0.10]])

        with patch(
            "app.services.section_comparison.cosine_similarity", return_value=sim
        ):
            matched, unmatched_src, unmatched_tgt = _match_sections(
                source, target, Mock(), threshold=0.5
            )

        assert {(s, t) for s, t, _ in matched} == {(0, 1), (1, 0)}
        assert unmatched_src == []
        assert unmatched_tgt == []

    def test_pairs_below_threshold_are_unmatched(self):
        source = [_section("A")]
        target = [_section("X")]

        with patch(
            "app.services.section_comparison.cosine_similarity",
            return_value=np.array([[0.2]]),
        ):
            matched, unmatched_src, unmatched_tgt = _match_sections(
                source, target, Mock(), threshold=0.5
            )

        assert matched == []
        assert unmatched_src == [0]
        assert unmatched_tgt == [0]


class TestParseArticleHtml:
    def test_separate_paragraphs_keep_boundaries(self):
        html = "<h2>History</h2><p>First paragraph.</p><p>Second paragraph.</p>"
        article = _parse_article_html(html, "Test", "en", "test")

        section = next(s for s in article.sections if s.title == "History")
        assert _split_into_paragraphs(section) == [
            "First paragraph.",
            "Second paragraph.",
        ]
