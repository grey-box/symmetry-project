import pytest

from app.ai import translation as translation_module
from app.ai.translation import TRANSLATION_CHUNK_CHAR_THRESHOLD, translate


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _stub_translation_backend(request, monkeypatch):
    """Run translation tests offline by default; external tests can opt out."""
    if request.node.get_closest_marker("external"):
        return

    original_loader = translation_module.load_translation_components
    if hasattr(original_loader, "cache_clear"):
        original_loader.cache_clear()

    def _fake_loader(_model_name: str):
        return object(), object()

    def _fake_translate_batch(batch: list[str], _tokenizer, _model) -> list[str]:
        return [f"translated::{item}" for item in batch]

    monkeypatch.setattr(translation_module, "load_translation_components", _fake_loader)
    monkeypatch.setattr(
        translation_module, "_translate_batch_with_model", _fake_translate_batch
    )


class TestTranslationLimits:
    """Focused translation tests with reduced redundancy and no network by default."""

    @pytest.mark.parametrize(
        "text,source,target",
        [
            ("", "en", "fr"),
            ("   \n\t", "en", "es"),
            ("Hello world", "en", "en"),
            ("Hello world", "english", "en"),
        ],
    )
    def test_returns_input_for_noop_cases(self, text, source, target):
        assert translate(text, source, target) == text

    @pytest.mark.parametrize("target", ["es", "fr", "de", "pt", "zh", "ar"])
    def test_supported_language_pairs(self, target):
        result = translate("Good morning, how are you today?", "en", target)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize(
        "text,target",
        [
            ("A", "fr"),
            ("The speed of light is 3.0 x 10^8 m/s.", "de"),
            ("Hello! How are you? @#$%", "it"),
            ("Line one.\n\nLine two.", "nl"),
            ("Check https://example.com and ping @user", "es"),
        ],
    )
    def test_varied_content_inputs(self, text, target):
        result = translate(text, "en", target)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chunked_translation_path_for_long_input(self):
        long_text = "word " * 1300
        assert len(long_text) > TRANSLATION_CHUNK_CHAR_THRESHOLD
        result = translate(long_text, "en", "fr")
        # Chunked path joins translated chunks with double newlines.
        assert "\n\n" in result

    def test_consecutive_calls_are_deterministic(self):
        text = "The quick brown fox jumps over the lazy dog."
        first = translate(text, "en", "es")
        second = translate(text, "en", "es")
        assert first == second

    def test_alias_normalization_works(self):
        result = translate("Hello world", "english", "french")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unsupported_language_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported translation pair"):
            translate("Hello world", "en", "xx")

    def test_fallback_to_source_text_when_model_is_unavailable(self, monkeypatch):
        def _raise_repo_error(_model_name: str):
            raise OSError(
                "Repository Not Found for url: https://huggingface.co/fake/model"
            )

        monkeypatch.setattr(
            translation_module, "load_translation_components", _raise_repo_error
        )

        text = "Fallback expected"
        assert translate(text, "en", "pt") == text

    def test_fallback_to_source_text_on_timeout(self, monkeypatch):
        def _raise_timeout(_model_name: str):
            raise RuntimeError("Connection timed out while loading tokenizer")

        monkeypatch.setattr(
            translation_module, "load_translation_components", _raise_timeout
        )

        text = "Fallback expected on timeout"
        assert translate(text, "en", "ja") == text


@pytest.mark.external
def test_live_huggingface_translation_smoke():
    """Optional live smoke test; requires network allowlist for huggingface.co."""
    result = translate("Hello world", "en", "fr")
    assert isinstance(result, str)
    assert len(result) > 0
