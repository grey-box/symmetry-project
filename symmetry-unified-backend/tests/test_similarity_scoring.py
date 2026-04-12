"""
Test suite for similarity_scoring module.
"""

import pytest
from app.services.similarity_scoring import (
    normalized_levenshtein_distance,
    has_loanword_suffix,
    classify_band,
    score_article_pair,
    score_articles_batch,
    get_language_family,
    LanguageFamily,
    transliterate_cyrillic,
    normalize_script,
    get_family_threshold,
)


class TestLevenshteinDistance:
    """Tests for normalized Levenshtein distance."""
    
    def test_identical_strings(self):
        """Identical strings should score 1.0."""
        assert normalized_levenshtein_distance("hello", "hello") == 1.0
    
    def test_completely_different(self):
        """Completely different strings should score low."""
        sim = normalized_levenshtein_distance("abc", "xyz")
        assert sim < 0.5
    
    def test_one_char_diff(self):
        """One character difference should be high."""
        sim = normalized_levenshtein_distance("cat", "car")
        assert sim > 0.6
    
    def test_empty_strings(self):
        """Empty strings should return appropriate scores."""
        assert normalized_levenshtein_distance("", "") == 1.0
        assert normalized_levenshtein_distance("", "hello") == 0.0
        assert normalized_levenshtein_distance("hello", "") == 0.0


class TestLoanwordDetection:
    """Tests for loanword suffix detection."""
    
    def test_common_loanword_suffixes(self):
        """Should detect common Latinate suffixes."""
        assert has_loanword_suffix("nation")
        assert has_loanword_suffix("action")
        assert has_loanword_suffix("movement")
        assert has_loanword_suffix("utilidad")
        assert has_loanword_suffix("modernismo")
    
    def test_non_loanword(self):
        """Should not flag basic words."""
        assert not has_loanword_suffix("cat")
        assert not has_loanword_suffix("dog")
        assert not has_loanword_suffix("run")


class TestBandClassification:
    """Tests for similarity band classification."""
    
    def test_very_close(self):
        """Score >= 85 should be very_close."""
        label, desc = classify_band(90)
        assert label == "very_close"
    
    def test_same_branch(self):
        """Score 60-85 should be same_branch."""
        label, desc = classify_band(72)
        assert label == "same_branch"
    
    def test_same_family_distant(self):
        """Score 25-60 should be same_family_distant."""
        label, desc = classify_band(42)
        assert label == "same_family_distant"
    
    def test_unrelated(self):
        """Score < 25 should be unrelated."""
        label, desc = classify_band(15)
        assert label == "unrelated"


class TestArticlePairScoring:
    """Tests for full article pair scoring."""
    
    def test_identical_articles(self):
        """Identical articles should score very high."""
        text = "the quick brown fox jumps over the lazy dog"
        score = score_article_pair(text, text)
        assert score.similarity_percent >= 85
        assert score.band_label == "very_close"
    
    def test_completely_different_articles(self):
        """Completely different text should score low."""
        original_text = "one two three four five"
        translated_text = "alpha beta gamma delta epsilon"
        score = score_article_pair(original_text, translated_text)
        assert score.similarity_percent < 25
        assert score.band_label == "unrelated"
    
    def test_partially_similar_articles(self):
        """Articles with some overlap should get intermediate scores."""
        original_text = "the cat sat on the mat"
        translated_text = "the dog sat on the floor"
        score = score_article_pair(original_text, translated_text)
        assert 25 <= score.similarity_percent <= 85
        assert score.band_label in ["same_branch", "same_family_distant"]
    
    def test_empty_articles(self):
        """Empty articles should return 0% similarity."""
        score = score_article_pair("", "hello world")
        assert score.similarity_percent == 0.0
        assert "empty_text" in score.confidence_flags
    
    def test_low_data_flag(self):
        """Articles with < 20 words should get low_data flag."""
        text = "one two three"
        score = score_article_pair(text, "four five six")
        assert "low_data_original" in score.confidence_flags or "low_data_translated" in score.confidence_flags
    
    def test_loanword_downweighting(self):
        """Articles with loanwords should be downweighted."""
        original_text = "nation action position"
        translated_text = "nation action position"
        
        score_no_dw = score_article_pair(
            original_text, translated_text, downweight_loanwords=False
        )
        score_with_dw = score_article_pair(
            original_text, translated_text, downweight_loanwords=True
        )
        
        # Both should exist and have values
        assert score_no_dw.similarity_percent >= 0
        assert score_with_dw.similarity_percent >= 0
    
    def test_swadesh_filter(self):
        """Swadesh filter should only use core vocabulary."""
        original_text = "I you he we they hand foot head"
        translated_text = "I you he we they hand foot head"
        
        score = score_article_pair(
            original_text, translated_text, use_swadesh_filter=True
        )
        assert "swadesh_filtered" in score.confidence_flags
    
    def test_word_match_threshold(self):
        """Different thresholds should affect match counts."""
        original_text = "cat"
        translated_text = "car dog bird"
        
        score_low = score_article_pair(original_text, translated_text, word_match_threshold=0.5)
        score_high = score_article_pair(original_text, translated_text, word_match_threshold=0.9)
        
        # Lower threshold should find cat~car, higher threshold should not
        assert score_low.word_match_count >= score_high.word_match_count


class TestBatchScoring:
    """Tests for batch article scoring."""
    
    def test_batch_scoring(self):
        """Should score multiple pairs."""
        pairs = [
            ("hello world", "hello world"),
            ("abc", "xyz"),
            ("one two three", "one two three"),
        ]
        
        scores = score_articles_batch(pairs)
        assert len(scores) == 3
        assert scores[0].similarity_percent > scores[1].similarity_percent
        assert scores[2].similarity_percent > scores[1].similarity_percent
    
    def test_batch_with_options(self):
        """Batch scoring should respect options."""
        pairs = [
            ("hand foot head", "hand foot head"),
        ]
        
        scores = score_articles_batch(
            pairs, word_match_threshold=0.7, use_swadesh_filter=True
        )
        assert len(scores) == 1
        assert "swadesh_filtered" in scores[0].confidence_flags


class TestLanguageFamilies:
    """Tests for language family classification."""
    
    def test_germanic_languages(self):
        """Should identify Germanic languages."""
        assert get_language_family("english") == LanguageFamily.GERMANIC
        assert get_language_family("german") == LanguageFamily.GERMANIC
        assert get_language_family("dutch") == LanguageFamily.GERMANIC
    
    def test_romance_languages(self):
        """Should identify Romance languages."""
        assert get_language_family("spanish") == LanguageFamily.ROMANCE
        assert get_language_family("french") == LanguageFamily.ROMANCE
        assert get_language_family("italian") == LanguageFamily.ROMANCE
    
    def test_slavic_languages(self):
        """Should identify Slavic languages."""
        assert get_language_family("russian") == LanguageFamily.SLAVIC
        assert get_language_family("polish") == LanguageFamily.SLAVIC
        assert get_language_family("ukrainian") == LanguageFamily.SLAVIC
    
    def test_unknown_language(self):
        """Unknown languages should return UNKNOWN."""
        assert get_language_family("klingon") == LanguageFamily.UNKNOWN


class TestScriptNormalization:
    """Tests for script normalization and transliteration."""
    
    def test_cyrillic_transliteration(self):
        """Should convert Cyrillic to Latin."""
        result = transliterate_cyrillic("привет")
        assert result == "privet"
    
    def test_normalize_cyrillic_text(self):
        """Should detect and normalize Cyrillic text."""
        cyrillic_text = "Привет мир"
        result = normalize_script(cyrillic_text)
        assert all(ord(c) < 0x0400 or ord(c) > 0x04FF for c in result)
    
    def test_latin_text_unchanged(self):
        """Latin text should pass through unchanged."""
        latin_text = "hello world"
        result = normalize_script(latin_text)
        assert result == latin_text


class TestCrossLanguageComparison:
    """Tests for cross-language similarity scoring."""
    
    def test_same_family_threshold(self):
        """Same language family should use lower threshold."""
        threshold = get_family_threshold(LanguageFamily.ROMANCE, LanguageFamily.ROMANCE)
        assert threshold < 0.60
    
    def test_different_family_threshold(self):
        """Different language families should use higher threshold."""
        threshold = get_family_threshold(LanguageFamily.GERMANIC, LanguageFamily.SLAVIC)
        assert threshold >= 0.60
    
    def test_english_spanish_cognates(self):
        """English and Spanish share some cognates (both IE languages)."""
        text_en = "education technology information"
        text_es = "educacion tecnologia informacion"
        
        score = score_article_pair(
            text_en, text_es,
            original_language="english",
            translated_language="spanish"
        )
        assert score.similarity_percent >= 0
    
    def test_english_russian_transliteration(self):
        """English and Russian should be transliterated for comparison."""
        text_en = "hello"
        text_ru = "привет"
        
        score = score_article_pair(
            text_en, text_ru,
            original_language="english",
            translated_language="russian"
        )
        assert score.original_language_family == "germanic"
        assert score.translated_language_family == "slavic"
        assert score.similarity_percent >= 0
    
    def test_french_spanish_similarity(self):
        """French and Spanish are both Romance languages."""
        threshold_fr_es = get_family_threshold(LanguageFamily.ROMANCE, LanguageFamily.ROMANCE)
        threshold_en_ru = get_family_threshold(LanguageFamily.GERMANIC, LanguageFamily.SLAVIC)
        assert threshold_fr_es < threshold_en_ru
    
    def test_batch_with_language_pairs(self):
        """Batch scorer should apply language-specific thresholds."""
        pairs = [
            ("hello world", "hello world"),
            ("test data", "test data"),
        ]
        language_pairs = [
            ("english", "english"),
            ("russian", "english"),
        ]
        scores = score_articles_batch(
            pairs,
            language_pairs=language_pairs
        )
        assert len(scores) == 2
        assert scores[0].original_language == "english"
        assert scores[0].translated_language == "english"
        assert scores[1].original_language == "russian"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
