from transformers import MarianMTModel, MarianTokenizer


#list of romance languages
ROMANCE_LANGS = ["es", "fr", "it", "pt", "ro", "ca", "co", "fur", "lld", "rm", "an", "rup", "wa", "vec", "nap", "scn"]

# This dictionary maps (source_lang, target_lang) pairs to specific MarianMT models.
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


# Translates text from source_lang to target_lang using the appropriate MarianMT model.
def translate(text: str, source_lang: str, target_lang: str) -> str:

    # Determine the appropriate model based on the source and target languages.
    key = (source_lang, target_lang)

# First check if there's a specific model for the language pair in MODEL_DICT.
    if key in MODEL_DICT:
        model_name = MODEL_DICT[key]
        # If we have a specific model for this language pair, use it.
    elif source_lang in ROMANCE_LANGS and target_lang == "en":
        model_name = "Helsinki-NLP/opus-mt-ROMANCE-en"
        # If the source language is a Romance language and the target is English, use the ROMANCE-en model.
    elif source_lang == "en" and target_lang in ROMANCE_LANGS:
        model_name = "Helsinki-NLP/opus-mt-en-ROMANCE"
    else: 
        raise ValueError(f"No translation model available for {source_lang} -> {target_lang}")

    # Load the tokenizer and model for the determined model name.
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    # Load the model for the determined model name.
    model = MarianMTModel.from_pretrained(model_name)

    if not text.strip():
        return text

    # Tokenize the input text and generate the translation using the model.
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    # Generate the translation using the model.
    outputs = model.generate(**inputs)

    # Decode the generated tokens back into a string and return it.
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
