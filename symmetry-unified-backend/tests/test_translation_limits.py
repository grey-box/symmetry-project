import pytest
from app.ai.translations import translate


class TestTranslationLimits:
    """Test suite for translation model limits in terms of length and content variety"""

    # Length Tests

    def test_very_short_text(self):
        """Test translation of very short text (single word)"""
        result = translate("Hello", "en", "es")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "error" not in result.lower()

    def test_single_character(self):
        """Test translation of single character"""
        result = translate("A", "en", "fr")
        assert isinstance(result, str)
        # Single characters might not translate, but should not fail

    def test_empty_string(self):
        """Test translation of empty string"""
        result = translate("", "en", "de")
        assert isinstance(result, str)
        # Should handle gracefully

    def test_medium_length_text(self):
        """Test translation of medium-length text (normal paragraph)"""
        medium_text = "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed."
        result = translate(medium_text, "en", "es")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "error" not in result.lower()

    def test_very_long_text(self):
        """Test translation of very long text (multiple paragraphs)"""
        long_text = """
        Artificial intelligence (AI) has become increasingly important in modern society. 
        Machine learning, a subset of AI, allows computers to learn from data and make predictions 
        or decisions without being explicitly programmed. Natural language processing (NLP) is another 
        important field that deals with the interaction between computers and human language.
        
        Deep learning, inspired by biological neural networks, has revolutionized many domains 
        including computer vision, speech recognition, and machine translation. Transformers, a 
        type of neural network architecture, have become the backbone of modern language models.
        
        The development of large language models has opened new possibilities for human-computer 
        interaction, from chatbots to code generation. However, these models also raise important 
        questions about bias, fairness, and the ethical use of AI in society.
        """
        result = translate(long_text, "en", "fr")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "error" not in result.lower()

    def test_extremely_long_text(self):
        """Test translation of extremely long text (over 1000 words)"""
        # Create a very long text by repeating content
        base_text = "The quick brown fox jumps over the lazy dog. "
        extremely_long_text = base_text * 100  # ~500 words
        result = translate(extremely_long_text, "en", "de")
        assert isinstance(result, str)
        # Model might have limits on token length, but should handle or error gracefully

    # content variety tests

    def test_technical_content(self):
        """Test translation of technical/specialized content"""
        technical_text = "Implement a recursive backtracking algorithm to solve the N-Queens problem using dynamic programming and memoization techniques."
        result = translate(technical_text, "en", "it")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_poetic_content(self):
        """Test translation of poetic/literary content"""
        poetic_text = (
            "Two roads diverged in a yellow wood, and sorry I could not travel both."
        )
        result = translate(poetic_text, "en", "pt")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_numerical_content(self):
        """Test translation with numbers and digits"""
        numerical_text = "The population in 2024 is approximately 8.1 billion people. GDP growth rate is 2.5% year-over-year."
        result = translate(numerical_text, "en", "ru")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mixed_case_content(self):
        """Test translation with varied capitalization"""
        mixed_case = "ThE QuIcK bRoWn Fox JUMPS over the LAZY dog. Hello WORLD!"
        result = translate(mixed_case, "en", "nl")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_special_characters(self):
        """Test translation with special characters and punctuation"""
        special_text = "Hello! How are you? I'm fine, thanks & regards. @#$%"
        result = translate(special_text, "en", "pl")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unicode_content(self):
        """Test translation with unicode characters"""
        unicode_text = "Hello 你好 مرحبا привет こんにちは"
        result = translate(unicode_text, "en", "es")
        assert isinstance(result, str)
        # Should handle unicode gracefully

    def test_urls_and_mentions(self):
        """Test translation with URLs and mentions"""
        url_text = "Check out https://www.example.com for more info. Follow @username on social media!"
        result = translate(url_text, "en", "fr")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_code_snippets(self):
        """Test translation with code-like content"""
        code_text = (
            "function calculate(x, y) { return x + y; } const result = calculate(5, 3);"
        )
        result = translate(code_text, "en", "de")
        assert isinstance(result, str)
        # Should handle code without breaking

    def test_scientific_notation(self):
        """Test translation with scientific notation and mathematical symbols"""
        scientific_text = "The speed of light is approximately 3.0 × 10^8 m/s. E = mc²"
        result = translate(scientific_text, "en", "zh")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_quoted_text(self):
        """Test translation with quoted content"""
        quoted_text = (
            '"To be or not to be, that is the question." - William Shakespeare'
        )
        result = translate(quoted_text, "en", "ja")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_sentences_with_contractions(self):
        """Test translation with contractions and abbreviated forms"""
        contraction_text = (
            "I've got what's needed. Don't worry, there's no problem. We'll handle it."
        )
        result = translate(contraction_text, "en", "ko")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_list_format(self):
        """Test translation of list-formatted content"""
        list_text = """
        1. First item in the list
        2. Second item with more details
        3. Third item for completion
        - Bullet point one
        - Bullet point two
        """
        result = translate(list_text, "en", "ar")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_multiline_content(self):
        """Test translation with multiple line breaks"""
        multiline_text = (
            "Line one.\n\nLine two with spacing.\n\n\nLine three with extra spacing."
        )
        result = translate(multiline_text, "en", "hi")
        assert isinstance(result, str)
        assert len(result) > 0

    # language pair tests

    def test_english_to_spanish(self):
        """Test English to Spanish translation"""
        result = translate("Good morning, how are you?", "en", "es")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_english_to_french(self):
        """Test English to French translation"""
        result = translate("Good morning, how are you?", "en", "fr")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_english_to_german(self):
        """Test English to German translation"""
        result = translate("Good morning, how are you?", "en", "de")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_english_to_italian(self):
        """Test English to Italian translation"""
        result = translate("Good morning, how are you?", "en", "it")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_english_to_portuguese(self):
        """Test English to Portuguese translation"""
        result = translate("Good morning, how are you?", "en", "pt")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_english_to_chinese(self):
        """Test English to Chinese translation"""
        result = translate("Good morning, how are you?", "en", "zh")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_english_to_japanese(self):
        """Test English to Japanese translation"""
        result = translate("Good morning, how are you?", "en", "ja")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_english_to_russian(self):
        """Test English to Russian translation"""
        result = translate("Good morning, how are you?", "en", "ru")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_english_to_arabic(self):
        """Test English to Arabic translation"""
        result = translate("Good morning, how are you?", "en", "ar")
        assert isinstance(result, str)
        assert "error" not in result.lower()

    def test_to_english_romance_language(self):
        """Test Romance language to English translation (generic model)"""
        result = translate("Bonjour, comment allez-vous?", "fr", "en")
        assert isinstance(result, str)
        # Should use generic ROMANCE-en model

    # edge case tests

    def test_unsupported_language(self):
        """Test with unsupported language code - falls back to original text"""
        result = translate("Hello world", "en", "xx")
        assert result == "Hello world"

    def test_very_many_special_characters(self):
        """Test with predominantly special characters"""
        special_heavy = "!!!??? ... @@@### $$$%%% &&&*** ((()))"
        result = translate(special_heavy, "en", "es")
        assert isinstance(result, str)

    def test_repeated_word(self):
        """Test translation of repeated single word"""
        repeated = "hello " * 100
        result = translate(repeated, "en", "fr")
        assert isinstance(result, str)

    def test_mixed_language_content(self):
        """Test translation with content in multiple languages"""
        mixed = "Hello world. Bonjour le monde. Hola mundo."
        result = translate(mixed, "en", "de")
        assert isinstance(result, str)

    def test_whitespace_only(self):
        """Test translation with only whitespace"""
        whitespace = "   \n\t   \n  "
        result = translate(whitespace, "en", "it")
        assert isinstance(result, str)

    def test_very_long_single_word(self):
        """Test translation with very long single word"""
        long_word = "hippopotomonstrosesquippedaliophobia" * 10
        result = translate(long_word, "en", "pt")
        assert isinstance(result, str)

    def test_numbers_only(self):
        """Test translation with only numbers"""
        numbers_only = "1234567890" * 20
        result = translate(numbers_only, "en", "nl")
        assert isinstance(result, str)

    def test_sentence_with_newlines_between_words(self):
        """Test translation where words are separated by newlines"""
        newline_separated = "Hello\nworld\nthis\nis\na\ntest"
        result = translate(newline_separated, "en", "pl")
        assert isinstance(result, str)

    def test_single_space(self):
        """Test translation with single space"""
        result = translate(" ", "en", "ru")
        assert isinstance(result, str)

    # stres tests

    def test_consecutive_translations_same_text(self):
        """Test multiple consecutive translations of same text"""
        text = "The quick brown fox jumps over the lazy dog."
        results = []
        for i in range(3):
            result = translate(text, "en", "es")
            results.append(result)
            assert isinstance(result, str)

        # Results should be consistent
        assert results[0] == results[1] == results[2]

    def test_consecutive_translations_different_languages(self):
        """Test multiple consecutive translations to different languages"""
        text = "Hello world"
        languages = ["es", "fr", "de", "it", "pt"]

        for lang in languages:
            result = translate(text, "en", lang)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.parametrize(
        "text",
        [
            "Hello",
            "Hello world",
            "The quick brown fox jumps over the lazy dog.",
            "Machine learning is a powerful technology for solving complex problems.",
        ],
    )
    def test_parametrized_texts_to_spanish(self, text):
        """Parametrized test for various text lengths to Spanish"""
        result = translate(text, "en", "es")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize(
        "lang", ["es", "fr", "de", "it", "pt", "nl", "pl", "ru", "zh", "ja"]
    )
    def test_parametrized_languages(self, lang):
        """Parametrized test for translation to all supported languages"""
        text = "Good morning, how are you today?"
        result = translate(text, "en", lang)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_response_length_reasonable(self):
        """Test that response length is reasonable compared to input"""
        text = "Hello world"
        result = translate(text, "en", "es")

        # Translation length should be somewhat reasonable
        # Allow for 5x expansion to account for language differences
        assert len(result) < len(text) * 5

    def test_no_exponential_output_growth(self):
        """Test that output doesn't grow exponentially with input"""
        short_text = "Hello world"
        long_text = short_text * 50

        short_result = translate(short_text, "en", "fr")
        long_result = translate(long_text, "en", "fr")

        # Long text should not cause exponential growth in output
        # Should be roughly proportional to input length
        assert len(long_result) < len(short_result) * 100
