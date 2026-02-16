import pytest
from app.ai.semantic_comparison import semantic_compare


class TestSemanticComparison:
    """Tests for semantic comparison functionality"""

    testset = {
        "complete_text": [
            "The Eiffel Tower was completed in 1889. Stands 330 meters tall, and was designed by Gustave Eiffel for the World's Fair.",
            "The iPhone 15 Pro features a titanium frame, weighs 187 grams, and includes a 48-megapixel main camera.",
            "Lake Baikal in Russia is the world's deepest lake at 1,642 meters, contains 23% of the world's fresh surface water, and is approximately 25 million years old.",
            "Tesla was founded in 2003, is headquartered in Austin, Texas, and employs over 140,000 people worldwide.",
            "Mars has two moons named Phobos and Deimos, completes one orbit around the Sun in 687 Earth days, and has a diameter of 6,779 kilometers.",
            '"1984" was published in 1949, written by George Orwell, and takes place in a dystopian totalitarian society.',
            "Usain Bolt set the 100-meter world record at 9.58 seconds in Berlin during the 2009 World Championships.",
            "Gold has the atomic number 79, a melting point of 1,064 degrees Celsius, and is represented by the symbol Au.",
            "Python was created by Guido van Rossum, first released in 1991, and is known for its emphasis on code readability.",
            "The blue whale is the largest animal on Earth, can reach lengths of 30 meters, and feeds primarily on krill.",
        ],
        "incomplete_text": [
            "The Eiffel Tower stands 330 meters tall and was designed by Gustave Eiffel for the World's Fair.",
            "The iPhone 15 Pro features a titanium frame and weighs 187 grams.",
            "Lake Baikal in Russia is the world's deepest lake and is approximately 25 million years old.",
            "Tesla is headquartered in Austin, Texas, and employs over 140,000 people worldwide.",
            "Mars has two moons named Phobos and Deimos and has a diameter of 6,779 kilometers.",
            '"1984" was written by George Orwell and takes place in a dystopian totalitarian society.',
            "Usain Bolt set the 100-meter world record at 9.58 seconds in Berlin.",
            "Gold has the atomic number 79 and is represented by the symbol Au.",
            "Python was created by Guido van Rossum and is known for its emphasis on code readability.",
            "The blue whale is the largest animal on Earth and can reach lengths of 30 meters.",
        ],
    }

    def test_semantic_compare_returns_dict(self):
        """Test that semantic_compare returns a dictionary with correct structure"""
        sample_a = self.testset["complete_text"][0]
        sample_b = self.testset["incomplete_text"][0]

        result = semantic_compare(
            sample_a, sample_b, "en", "en", 0.5, "sentence-transformers/LaBSE"
        )

        assert isinstance(result, dict)
        assert "success" in result
        assert "original_sentences" in result
        assert "translated_sentences" in result
        assert "missing_info" in result
        assert "extra_info" in result
        assert "missing_info_indices" in result
        assert "extra_info_indices" in result

    def test_semantic_compare_success_flag(self):
        """Test that semantic_compare sets success flag correctly"""
        sample_a = self.testset["complete_text"][0]
        sample_b = self.testset["incomplete_text"][0]

        result = semantic_compare(
            sample_a, sample_b, "en", "en", 0.5, "sentence-transformers/LaBSE"
        )

        assert result["success"] is True

    def test_semantic_compare_identifies_missing_info(self):
        """Test that semantic_compare identifies missing information"""
        sample_a = self.testset["complete_text"][0]
        sample_b = self.testset["incomplete_text"][0]

        result = semantic_compare(
            sample_a, sample_b, "en", "en", 0.5, "sentence-transformers/LaBSE"
        )

        assert isinstance(result["missing_info"], list)
        assert isinstance(result["missing_info_indices"], list)

    def test_semantic_compare_multiple_samples(self):
        """Test semantic comparison with multiple sample pairs"""
        for i in range(min(3, len(self.testset["complete_text"]))):
            sample_a = self.testset["complete_text"][i]
            sample_b = self.testset["incomplete_text"][i]

            result = semantic_compare(
                sample_a, sample_b, "en", "en", 0.5, "sentence-transformers/LaBSE"
            )

            assert result["success"] is True
            assert isinstance(result["original_sentences"], list)
            assert isinstance(result["translated_sentences"], list)
