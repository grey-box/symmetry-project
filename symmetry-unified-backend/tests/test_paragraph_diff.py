"""Unit tests for the paragraph_diff service.

All tests are offline — no external Wikipedia or HuggingFace calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from app.services.paragraph_diff import (
    align_paragraphs,
    diff_sections,
    word_diff,
)
from app.models.wiki.paragraph_diff import WordToken


# ---------------------------------------------------------------------------
# word_diff tests
# ---------------------------------------------------------------------------


class TestWordDiff:
    def test_identical_texts(self):
        tokens = word_diff("Hello world", "Hello world")
        # All tokens should be equal (non-whitespace ones)
        types = {t.type for t in tokens}
        assert types <= {"equal"}
        # The word content must be there
        texts = " ".join(t.text or "" for t in tokens if t.type == "equal")
        assert "Hello" in texts
        assert "world" in texts

    def test_single_word_substitution(self):
        tokens = word_diff("Hello world", "Hello earth")
        types = [t.type for t in tokens]
        assert "replace" in types
        replace_token = next(t for t in tokens if t.type == "replace")
        assert replace_token.old == "world"
        assert replace_token.new == "earth"

    def test_insertion(self):
        tokens = word_diff("Hello world", "Hello big world")
        types = [t.type for t in tokens]
        assert "insert" in types
        insert_token = next(t for t in tokens if t.type == "insert")
        assert insert_token.text == "big"

    def test_deletion(self):
        tokens = word_diff("Hello big world", "Hello world")
        types = [t.type for t in tokens]
        assert "delete" in types
        del_token = next(t for t in tokens if t.type == "delete")
        assert del_token.text == "big"

    def test_empty_source(self):
        tokens = word_diff("", "Hello world")
        types = [t.type for t in tokens]
        # All tokens should be inserts
        assert all(t in {"insert", "equal"} for t in types)

    def test_empty_target(self):
        tokens = word_diff("Hello world", "")
        types = [t.type for t in tokens]
        assert all(t in {"delete", "equal"} for t in types)

    def test_both_empty(self):
        assert word_diff("", "") == []

    def test_word_token_schema(self):
        tokens = word_diff("cat sat on mat", "cat sat on rug")
        for tok in tokens:
            assert isinstance(tok, WordToken)
            if tok.type == "equal":
                assert tok.text is not None
            elif tok.type == "replace":
                assert tok.old is not None and tok.new is not None
            elif tok.type in {"insert", "delete"}:
                assert tok.text is not None


# ---------------------------------------------------------------------------
# align_paragraphs tests
# ---------------------------------------------------------------------------


def _make_mock_model(sim_value: float = 0.9):
    """Return a mock SentenceTransformer that returns predictable embeddings."""
    mock = MagicMock()

    def encode_side_effect(sentences, **kwargs):
        n = len(sentences)
        # Each sentence gets a unit vector; neighbouring sentences are similar
        vecs = np.eye(max(n, 1))[:n]
        return vecs

    mock.encode.side_effect = encode_side_effect
    return mock


class TestAlignParagraphs:
    def test_basic_alignment(self):
        model = _make_mock_model()
        src = ["The sky is blue.", "Water is wet."]
        tgt = ["The sky is blue.", "Water is wet."]

        # Override encode to return identical unit vectors for same-index sentences
        call_count = [0]

        def encode_side_effect(sentences, **kwargs):
            call_count[0] += 1
            n = len(sentences)
            vecs = np.eye(max(n, 2))[:n]
            return vecs

        model.encode.side_effect = encode_side_effect

        pairs = align_paragraphs(src, tgt, model, threshold=0.5)
        assert len(pairs) > 0
        for pair in pairs:
            assert 0.0 <= pair.similarity <= 1.0
            assert isinstance(pair.word_diff, list)

    def test_empty_source(self):
        model = _make_mock_model()
        pairs = align_paragraphs([], ["Some target"], model)
        assert pairs == []

    def test_empty_target(self):
        model = _make_mock_model()
        pairs = align_paragraphs(["Some source"], [], model)
        assert pairs == []

    def test_threshold_filters_low_similarity(self):
        model = MagicMock()
        # Return orthogonal unit vectors: src=[1,0], tgt=[0,1] → cosine = 0.0
        call_count = [0]

        def encode_side_effect(sentences, **kwargs):
            n = len(sentences)
            idx = call_count[0]
            call_count[0] += 1
            vecs = np.zeros((n, 2))
            for i in range(n):
                # First call (src): axis 0; second call (tgt): axis 1
                vecs[i, idx % 2] = 1.0
            return vecs

        model.encode.side_effect = encode_side_effect
        pairs = align_paragraphs(
            ["Completely different source text."],
            ["Totally unrelated target sentence."],
            model,
            threshold=0.5,  # similarity will be 0.0 → filtered out
        )
        assert pairs == []

    def test_embedding_error_returns_empty(self):
        model = MagicMock()
        model.encode.side_effect = RuntimeError("embedding failed")
        pairs = align_paragraphs(["a"], ["b"], model)
        assert pairs == []


# ---------------------------------------------------------------------------
# diff_sections tests
# ---------------------------------------------------------------------------


class TestDiffSections:
    def test_basic_section_match(self):
        model = MagicMock()

        call_count = [0]

        def encode_side_effect(sentences, **kwargs):
            call_count[0] += 1
            n = len(sentences)
            vecs = np.eye(max(n, 2))[:n]
            return vecs

        model.encode.side_effect = encode_side_effect

        src = [("Introduction", "The Earth is the third planet from the Sun.")]
        tgt = [("Introduction", "The Earth is the third planet from the Sun.")]

        sections = diff_sections(src, tgt, model, threshold=0.0)
        assert isinstance(sections, list)

    def test_empty_inputs(self):
        model = MagicMock()
        assert diff_sections([], [], model) == []
        assert diff_sections([("A", "text")], [], model) == []

    def test_embedding_error_returns_empty(self):
        model = MagicMock()
        model.encode.side_effect = RuntimeError("fail")
        result = diff_sections([("A", "text")], [("A", "text")], model)
        assert result == []


# ---------------------------------------------------------------------------
# paragraph-diff endpoint (integration, no external calls)
# ---------------------------------------------------------------------------


class TestParagraphDiffEndpoint:
    def test_endpoint_reachable(self, client):
        """The endpoint exists and returns 422 when body is empty."""
        response = client.post(
            "/symmetry/v1/wiki/paragraph-diff",
            json={},
        )
        # 422 = validation error (missing required fields) — endpoint IS registered
        assert response.status_code == 422

    def test_endpoint_with_mocked_articles(self, client):
        """End-to-end test with mocked article_fetcher and model."""
        from app.models.wiki.structure import Article, Section

        fake_article_en = Article(
            title="Climate change",
            lang="en",
            source="https://en.wikipedia.org/wiki/Climate_change",
            sections=[
                Section(
                    title="Overview",
                    raw_content="Climate change is a long-term shift in temperatures.",
                    clean_content="Climate change is a long-term shift in temperatures.",
                )
            ],
            references=[],
        )
        fake_article_fr = Article(
            title="Changement climatique",
            lang="fr",
            source="https://fr.wikipedia.org/wiki/Changement_climatique",
            sections=[
                Section(
                    title="Présentation",
                    raw_content="Le changement climatique désigne une variation durable.",
                    clean_content="Le changement climatique désigne une variation durable.",
                )
            ],
            references=[],
        )

        mock_model = MagicMock()
        # Return simple unit vectors so cosine similarity is deterministic
        mock_model.encode.side_effect = lambda sentences, **kw: np.eye(
            max(len(sentences), 2)
        )[: len(sentences)]

        with (
            patch(
                "app.routers.structured_wiki.article_fetcher",
                side_effect=[fake_article_en, fake_article_fr],
            ),
            patch(
                "app.routers.structured_wiki._get_st_model",
                return_value=mock_model,
            ),
        ):
            response = client.post(
                "/symmetry/v1/wiki/paragraph-diff",
                json={
                    "source_query": "Climate change",
                    "target_query": "Changement climatique",
                    "source_lang": "en",
                    "target_lang": "fr",
                    "similarity_threshold": 0.1,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["source_title"] == "Climate change"
        assert data["target_title"] == "Changement climatique"
        assert "sections" in data
        assert isinstance(data["sections"], list)

    def test_invalid_source_url(self, client):
        """Invalid Wikipedia URL in source_query should return 400."""
        with (
            patch(
                "app.routers.structured_wiki.article_fetcher",
                side_effect=Exception("should not be called"),
            ),
        ):
            response = client.post(
                "/symmetry/v1/wiki/paragraph-diff",
                json={
                    "source_query": "https://not-wikipedia.com/invalid",
                    "target_query": "Climate change",
                    "source_lang": "en",
                    "target_lang": "en",
                },
            )
        assert response.status_code == 400
