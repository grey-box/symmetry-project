from functools import lru_cache
import logging

from transformers import MarianMTModel, MarianTokenizer

from app.services.chunking import chunk_text

ROMANCE_LANGS = [
    "es",
    "fr",
    "it",
    "pt",
    "ro",
    "ca",
    "co",
    "fur",
    "lld",
    "rm",
    "an",
    "rup",
    "wa",
    "vec",
    "nap",
    "scn",
]

TRANSLATION_CHUNK_CHAR_THRESHOLD = 3500
TRANSLATION_CHUNK_WORD_SIZE = 450
TRANSLATION_BATCH_SIZE = 4

LANG_ALIASES = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "hindi": "hi",
    "arabic": "ar",
}

MODEL_DICT = {
    ("en", "es"): "Helsinki-NLP/opus-mt-en-es",
    ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr",
    ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
    ("en", "it"): "Helsinki-NLP/opus-mt-en-it",
    ("en", "pt"): "Helsinki-NLP/opus-mt-en-pt",
    ("en", "nl"): "Helsinki-NLP/opus-mt-en-nl",
    ("en", "pl"): "Helsinki-NLP/opus-mt-en-pl",
    ("en", "ru"): "Helsinki-NLP/opus-mt-en-ru",
    ("en", "zh"): "Helsinki-NLP/opus-mt-en-zh",
    ("en", "ja"): "Helsinki-NLP/opus-mt-en-ja",
    ("en", "ko"): "Helsinki-NLP/opus-mt-en-ko",
    ("en", "ar"): "Helsinki-NLP/opus-mt-en-ar",
    ("en", "hi"): "Helsinki-NLP/opus-mt-en-hi",
    ("en", "tr"): "Helsinki-NLP/opus-mt-en-tr",
    ("es", "en"): "Helsinki-NLP/opus-mt-es-en",
    ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
    ("de", "en"): "Helsinki-NLP/opus-mt-de-en",
    ("it", "en"): "Helsinki-NLP/opus-mt-it-en",
    ("pt", "en"): "Helsinki-NLP/opus-mt-pt-en",
    ("nl", "en"): "Helsinki-NLP/opus-mt-nl-en",
    ("pl", "en"): "Helsinki-NLP/opus-mt-pl-en",
    ("ru", "en"): "Helsinki-NLP/opus-mt-ru-en",
    ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
    ("ja", "en"): "Helsinki-NLP/opus-mt-ja-en",
    ("ko", "en"): "Helsinki-NLP/opus-mt-ko-en",
    ("ar", "en"): "Helsinki-NLP/opus-mt-ar-en",
    ("hi", "en"): "Helsinki-NLP/opus-mt-hi-en",
    ("tr", "en"): "Helsinki-NLP/opus-mt-tr-en",
}


def translate(text: str, source_lang: str, target_lang: str) -> str:
    source_lang = _normalize_lang_code(source_lang)
    target_lang = _normalize_lang_code(target_lang)

    key = (source_lang, target_lang)
    if key in MODEL_DICT:
        model_name = MODEL_DICT[key]
    elif source_lang in ROMANCE_LANGS and target_lang == "en":
        model_name = "Helsinki-NLP/opus-mt-ROMANCE-en"
    elif source_lang == "en" and target_lang in ROMANCE_LANGS:
        model_name = "Helsinki-NLP/opus-mt-en-ROMANCE"
    else:
        raise ValueError(f"No translation model available for {source_lang} -> {target_lang}")

    if not text.strip():
        return text

    tokenizer, model = load_translation_components(model_name)

    if len(text) > TRANSLATION_CHUNK_CHAR_THRESHOLD:
        chunks = chunk_text(text, chunk_size=TRANSLATION_CHUNK_WORD_SIZE, overlap=0)
        chunks = [chunk for chunk in chunks if chunk.strip()]
        logging.info(
            "Translation chunking active (chars=%d, chunks=%d, chunk_words=%d)",
            len(text),
            len(chunks),
            TRANSLATION_CHUNK_WORD_SIZE,
        )
        translated_chunks = []
        for i in range(0, len(chunks), TRANSLATION_BATCH_SIZE):
            batch = chunks[i : i + TRANSLATION_BATCH_SIZE]
            translated_chunks.extend(_translate_batch_with_model(batch, tokenizer, model))
        return "\n\n".join(translated_chunks).strip()

    return _translate_with_model(text, tokenizer, model)


@lru_cache(maxsize=32)
def load_translation_components(model_name: str):
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    return tokenizer, model


def _translate_with_model(text: str, tokenizer, model) -> str:
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    outputs = model.generate(**inputs)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def _translate_batch_with_model(texts, tokenizer, model):
    if not texts:
        return []
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
    outputs = model.generate(**inputs)
    return [tokenizer.decode(output, skip_special_tokens=True) for output in outputs]


def _normalize_lang_code(language: str) -> str:
    normalized = (language or "").strip().lower()
    if not normalized:
        return normalized

    if normalized in LANG_ALIASES:
        return LANG_ALIASES[normalized]

    normalized = normalized.replace("_", "-")
    if "-" in normalized:
        normalized = normalized.split("-")[0]

    return normalized
