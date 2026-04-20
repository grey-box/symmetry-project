from transformers import MarianMTModel, MarianTokenizer
import torch

from app.ai.translation_model_registry import (
    get_translation_model_name,
)


def translate_text(input_text: str, source_lang: str, target_lang: str):
    """
    Translate text from source_lang to target_lang using the configured model registry.
    """

    source_lang = source_lang.strip().lower()
    target_lang = target_lang.strip().lower()

    if source_lang == target_lang:
        return input_text

    model_name = get_translation_model_name(source_lang, target_lang)

    if model_name is None:
        raise ValueError(
            f"Translation model not supported for '{source_lang}' -> '{target_lang}'."
        )

    # Load tokenizer and model
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    # Tokenize and translate
    inputs = tokenizer(input_text, return_tensors="pt", padding=True)
    with torch.no_grad():
        translated = model.generate(**inputs)

    translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
    return translated_text
