from transformers import MarianMTModel, MarianTokenizer
import torch

from app.ai.translation_model_registry import (
    get_supported_target_langs,
    get_translation_model_name,
)


def translate_text(input_text: str, target_lang: str):
    """
    Translate text to the specified target language.
    Supported language pairs (source -> target):
    - English -> Spanish, French, German, Italian, Portuguese, Dutch, Polish, Russian, Chinese, Japanese, Korean, Arabic, Hindi, Turkish
    - Spanish -> English, French, German, Italian, Portuguese
    - French -> English, Spanish, German, Italian, Portuguese
    - German -> English, Spanish, French, Italian, Portuguese
    - Italian -> English, Spanish, French, German, Portuguese
    - Portuguese -> English, Spanish, French, German, Italian
    - Dutch -> English
    - Polish -> English
    - Russian -> English
    - Chinese -> English
    - Japanese -> English
    - Korean -> English
    - Arabic -> English
    - Hindi -> English
    - Turkish -> English
    For Romance languages (Spanish, French, Italian, Portuguese, Romanian, Catalan, etc.) to English,
    you can also use the generic 'ROMANCE-en' model.
    Usage: Enter text and target language separated by comma (e.g., "Hello world,es" or "Bonjour,en")
    """

    # Clean and parse inputs
    target_lang = target_lang.strip().lower()

    # Use translation model configuration from JSON if available.
    if target_lang == "en":
        model_name = "Helsinki-NLP/opus-mt-ROMANCE-en"
    else:
        model_name = get_translation_model_name("en", target_lang)

    if model_name is None:
        available_langs = ", ".join(["en"] + get_supported_target_langs("en"))
        raise ValueError(
            f"Target language '{target_lang}' not supported. Available: {available_langs}"
        )

    try:
        # Load tokenizer and model
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)

        # Prepare input text
        if target_lang == "en":
            # For Romance to English, the model expects the text as-is
            input_text_formatted = input_text
        else:
            # For English to other languages, format appropriately
            input_text_formatted = input_text

        # Tokenize and translate
        inputs = tokenizer(input_text_formatted, return_tensors="pt", padding=True)
        with torch.no_grad():
            translated = model.generate(**inputs)

        # Decode the result
        translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
        return translated_text

    except Exception as e:
        return f"Translation error: {str(e)}"
