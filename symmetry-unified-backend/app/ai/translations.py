import json
from pathlib import Path
from transformers import MarianMTModel, MarianTokenizer

ROMANCE_LANGS = ["es", "fr", "it", "pt", "ro", "ca", "co", "fur", "lld", "rm", "an", "rup", "wa", "vec", "nap", "scn"]


CONFIG_PATH = Path(__file__).parent / "translation_models.json"

with open(CONFIG_PATH, "r") as f:
    MODEL_CONFIG = json.load(f)


def get_model_config(source_lang: str, target_lang: str):
    for entry in MODEL_CONFIG:
        if (
            entry["source_lang"] == source_lang
            and entry["target_lang"] == target_lang
        ):
            return entry
    return None


def translate(text: str, source_lang: str, target_lang: str) -> str:
    config = get_model_config(source_lang, target_lang)

    if config != None:
        model_name = config["model_name"]
    elif source_lang in ROMANCE_LANGS and target_lang == "en":
        model_name = "Helsinki-NLP/opus-mt-ROMANCE-en"
    elif source_lang == "en" and target_lang in ROMANCE_LANGS:
        model_name = "Helsinki-NLP/opus-mt-en-ROMANCE"
    else:
        raise ValueError(
            f"No translation model available for {source_lang} -> {target_lang}"
        )

    if not text.strip():
        return text

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    outputs = model.generate(**inputs)

    return tokenizer.decode(outputs[0], skip_special_tokens=True)
