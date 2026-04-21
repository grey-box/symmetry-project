"""MarianMT translation engine with chunking and LRU model cache."""

import logging
from functools import lru_cache

from transformers import MarianMTModel, MarianTokenizer

from app.models.translation.registry import get_translation_model_name, ROMANCE_LANGS
from app.services.chunking import chunk_text

logger = logging.getLogger(__name__)

TRANSLATION_CHUNK_CHAR_THRESHOLD = 1500
TRANSLATION_CHUNK_WORD_SIZE = 300
TRANSLATION_BATCH_SIZE = 4

_LANG_ALIASES = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "hindi": "hi",
    "arabic": "ar",
}


def _normalize_lang_code(lang: str) -> str:
    normalized = (lang or "").strip().lower()
    normalized = _LANG_ALIASES.get(normalized, normalized)
    normalized = normalized.replace("_", "-")
    if "-" in normalized:
        normalized = normalized.split("-")[0]
    return normalized


@lru_cache(maxsize=4)
def load_translation_components(model_name: str):
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    return tokenizer, model


def _translate_batch_with_model(batch: list, tokenizer, model) -> list:
    inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True)
    translated = model.generate(**inputs)
    return [tokenizer.decode(t, skip_special_tokens=True) for t in translated]


def _translate_with_model(text: str, tokenizer, model) -> str:
    return _translate_batch_with_model([text], tokenizer, model)[0]


def translate(text: str, source_lang: str, target_lang: str) -> str:
    source_lang = _normalize_lang_code(source_lang)
    target_lang = _normalize_lang_code(target_lang)

    if not text.strip() or source_lang == target_lang:
        return text

    model_name = get_translation_model_name(source_lang, target_lang)
    if model_name is None:
        if source_lang in ROMANCE_LANGS and target_lang == "en":
            model_name = "Helsinki-NLP/opus-mt-ROMANCE-en"
        elif source_lang == "en" and target_lang in ROMANCE_LANGS:
            model_name = "Helsinki-NLP/opus-mt-en-ROMANCE"
        else:
            logger.warning(
                "Unsupported translation pair %s -> %s. Returning original text.",
                source_lang, target_lang,
            )
            return text

    try:
        tokenizer, model = load_translation_components(model_name)

        if len(text) > TRANSLATION_CHUNK_CHAR_THRESHOLD:
            chunks = [c for c in chunk_text(text, chunk_size=TRANSLATION_CHUNK_WORD_SIZE, overlap=0) if c.strip()]
            translated_chunks = []
            for i in range(0, len(chunks), TRANSLATION_BATCH_SIZE):
                translated_chunks.extend(
                    _translate_batch_with_model(chunks[i : i + TRANSLATION_BATCH_SIZE], tokenizer, model)
                )
            return "\n\n".join(translated_chunks).strip()

        return _translate_with_model(text, tokenizer, model)
    except Exception as exc:
        logger.warning("Translation failed %s -> %s: %s. Returning original.", source_lang, target_lang, exc)
        return text

