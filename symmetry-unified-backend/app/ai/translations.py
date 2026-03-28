"""
Translation bridge module.

Provides a `translate(text, source_lang, target_lang)` interface used by
structured_wiki.py, delegating to the MarianMT-based translate_text() in
app.ai.translation.
"""

import logging

from app.ai.translation import translate_text

logger = logging.getLogger(__name__)


def translate(text: str, source_lang: str, target_lang: str) -> str:
    """
    Translate text from source_lang to target_lang.

    Uses Helsinki-NLP MarianMT models via translate_text().
    If source and target are the same, returns text unchanged.

    Args:
        text: The text to translate.
        source_lang: ISO 639-1 code of the source language (e.g. 'en').
        target_lang: ISO 639-1 code of the target language (e.g. 'fr').

    Returns:
        Translated text, or the original text if translation fails.
    """
    if not text or not text.strip():
        return text

    if source_lang == target_lang:
        return text

    try:
        result = translate_text(text, target_lang)
        # translate_text returns an error string on failure
        if isinstance(result, str) and result.startswith("Translation error:"):
            logger.warning("Translation failed for '%s…': %s", text[:50], result)
            return text
        return result
    except Exception as e:
        logger.error("Translation exception: %s", e)
        return text
