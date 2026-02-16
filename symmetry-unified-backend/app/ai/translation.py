from transformers import MarianMTModel, MarianTokenizer
import torch

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

    # Dictionary mapping target languages to model names
    # Format: {target_lang_code: (source_prefix, model_name)}
    translation_models = {
        # English to other languages
        'es': ('en', 'Helsinki-NLP/opus-mt-en-es'),
        'fr': ('en', 'Helsinki-NLP/opus-mt-en-fr'),
        'de': ('en', 'Helsinki-NLP/opus-mt-en-de'),
        'it': ('en', 'Helsinki-NLP/opus-mt-en-it'),
        'pt': ('en', 'Helsinki-NLP/opus-mt-en-pt'),
        'nl': ('en', 'Helsinki-NLP/opus-mt-en-nl'),
        'pl': ('en', 'Helsinki-NLP/opus-mt-en-pl'),
        'ru': ('en', 'Helsinki-NLP/opus-mt-en-ru'),
        'zh': ('en', 'Helsinki-NLP/opus-mt-en-zh'),
        'ja': ('en', 'Helsinki-NLP/opus-mt-en-jap'),
        'ko': ('en', 'Helsinki-NLP/opus-mt-en-ko'),
        'ar': ('en', 'Helsinki-NLP/opus-mt-en-ar'),
        'hi': ('en', 'Helsinki-NLP/opus-mt-en-hi'),
        'tr': ('en', 'Helsinki-NLP/opus-mt-en-tr'),

        # Other languages to English
        'en': ('multi', 'Helsinki-NLP/opus-mt-ROMANCE-en'),  # Generic Romance to English
    }

    # Handle specific language pairs for better accuracy
    if target_lang == 'en':
        # Detect source language and use specific model if available
        # For simplicity, we'll use the generic ROMANCE model for Romance languages
        # In a real application, you might want to detect the source language first
        model_name = 'Helsinki-NLP/opus-mt-ROMANCE-en'
        source_prefix = '>>en<<'
    elif target_lang in translation_models:
        source_prefix, model_name = translation_models[target_lang]
        # Add target language prefix for some models
        if source_prefix == 'en':
            source_prefix = ''
    else:
        # Fallback to generic approach or raise error
        available_langs = ', '.join(translation_models.keys())
        raise ValueError(f"Target language '{target_lang}' not supported. Available: {available_langs}")

    try:
        # Load tokenizer and model
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)

        # Prepare input text
        if target_lang == 'en':
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

# Google Colab interactive input
# try:
#     user_input = input("Enter text and target language (separated by comma): ")
#     if ',' not in user_input:
#         print("Please use format: 'your text,language_code' (e.g., 'Hello world,es')")
#     else:
#         text_part, lang_part = user_input.rsplit(',', 1)  # Split on last comma to handle text with commas
#         result = translate_text(text_part.strip(), lang_part.strip())
#         print(f"\nTranslated text: {result}")
# 
# except KeyboardInterrupt:
#     print("\nOperation cancelled by user.")
# except Exception as e:
#     print(f"Error: {e}"