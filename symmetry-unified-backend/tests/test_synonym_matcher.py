import pytest

from nltk.corpus import wordnet
from app.services.similarity_prototype.Phase_2.synonym_matcher import SynonymMatcher


def test_build_sentence_pos_cache_uses_sentence_context():
    pytest.importorskip("nltk")

    matcher = SynonymMatcher()
    matcher.build_sentence_pos_cache("The cat sat on the mat.")

    assert matcher._pos_cache.get("cat") == wordnet.NOUN
    assert matcher._pos_cache.get("sat") == wordnet.VERB


def test_compare_does_not_repeatedly_tag_each_token():
    pytest.importorskip("nltk")

    matcher = SynonymMatcher()
    matcher.compare("The cat sat on the mat.", "A feline rested on a rug.")

    assert "cat" in matcher._pos_cache
    assert "rested" in matcher._pos_cache
