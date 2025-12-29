from transformers import MarianMTModel, MarianTokenizer

# model_name = 'Helsinki-NLP/opus-mt-en-es'


def sentence_romance_to_english(romance_lang_sentence: str):
    model_name = 'Helsinki-NLP/opus-mt-ROMANCE-en'
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    # Translate
    translated = model.generate(**tokenizer(romance_lang_sentence, return_tensors="pt", padding=True))
    translated_text = [tokenizer.decode(t, skip_special_tokens=True) for t in translated][0]
    return translated_text
