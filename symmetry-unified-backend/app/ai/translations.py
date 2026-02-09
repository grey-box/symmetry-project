from transformers import MarianMTModel, MarianTokenizer

ROMANCE_LANGS = ["es", "fr", "it", "pt", "ro", "ca", "co", "fur", "lld", "rm", "an", "rup", "wa", "vec", "nap", "scn"]


MODEL_DICT = {
    # English -> Other
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

    # Other -> English
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
    key = (source_lang, target_lang)

    if key in MODEL_DICT:
        model_name = MODEL_DICT[key]
    elif source_lang in ROMANCE_LANGS and target_lang == "en":
        model_name = "Helsinki-NLP/opus-mt-ROMANCE-en"
    elif source_lang == "en" and target_lang in ROMANCE_LANGS:
        model_name = "Helsinki-NLP/opus-mt-en-ROMANCE"
    else: 
        raise ValueError(f"No translation model available for {source_lang} -> {target_lang}")

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    if not text.strip():
        return text

    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    outputs = model.generate(**inputs)

    return tokenizer.decode(outputs[0], skip_special_tokens=True)
