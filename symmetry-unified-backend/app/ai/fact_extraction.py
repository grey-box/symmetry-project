import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForCausalLM,
    AutoConfig,
)

# ---------------------------------------------------------------------
# Load model config
# ---------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "fact_extraction_models.json"

with open(CONFIG_PATH, "r") as f:
    MODEL_CONFIG = {
        entry["id"]: entry
        for entry in json.load(f)
    }

# Cache: model_name -> (model, tokenizer)
_model_cache: Dict[str, Tuple[Any, Any]] = {}


def get_model_config(model_id: str) -> Dict[str, Any]:
    config = MODEL_CONFIG.get(model_id)
    if not config:
        raise ValueError(f"Model ID '{model_id}' not found")
    return config


def get_available_models() -> List[Dict[str, Any]]:
    return list(MODEL_CONFIG.values())


# ---------------------------------------------------------------------
# Main extraction function (simplified)
# ---------------------------------------------------------------------

def extract_facts(text: str, model_id: str) -> str:
    """
    Sends text + prompt to model and returns RAW output.
    No parsing, no cleaning.
    """

    if not text.strip():
        return ""

    config = get_model_config(model_id)
    model_name = config["model_name"]

    # Load model if not cached
    if model_name not in _model_cache:
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        model_config = AutoConfig.from_pretrained(model_name)

        if model_config.is_encoder_decoder:
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        else:
            model = AutoModelForCausalLM.from_pretrained(model_name)

        model.eval()
        _model_cache[model_name] = (model, tokenizer)

    model, tokenizer = _model_cache[model_name]

    # Simple prompt
    prompt = (
        "Extract all explicit facts from the text below.\n\n"
        "Return them as bullet points.\n\n"
        f"Text:\n{text}\n\n"
        "Facts:"
    )

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
        model.config.pad_token_id = tokenizer.pad_token_id

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    return [tokenizer.decode(outputs[0], skip_special_tokens=True)]