import json
from pathlib import Path
from typing import List, Dict, Any

CONFIG_PATH = Path(__file__).parent / "fact_extraction_models.json"

with open(CONFIG_PATH, "r") as f:
    MODEL_CONFIG = {
        entry["id"]: entry
        for entry in json.load(f)
    }

# Cache for loaded models (similar to translation.py)
_model_cache = {}

# Lazy import flags to avoid heavy imports until needed
_transformers_imported = False
_torch_imported = False

def _lazy_import_transformers():
    """Lazily import transformers and torch only when first needed"""
    global _transformers_imported, _torch_imported
    if not _transformers_imported:
        global pipeline, AutoTokenizer, AutoModelForSeq2SeqLM, torch
        from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
        import torch
        _transformers_imported = True
        _torch_imported = True

def get_model_config(model_id: str) -> Dict[str, Any]:
    """Get configuration for a specific model ID"""
    config = MODEL_CONFIG.get(model_id)
    if not config:
        raise ValueError(f"Model ID '{model_id}' not found in configuration")
    return config


def extract_facts(text: str, model_id: str) -> List[str]:
    """
    Extract facts from text using the specified HuggingFace model.
    Uses summarization models to extract key factual statements.

    Args:
        text: The text to extract facts from
        model_id: ID of the model to use (must be in fact_extraction_models.json)

    Returns:
        List of extracted facts as strings
    """
    # Lazy import transformers only when first needed
    _lazy_import_transformers()
    
    config = get_model_config(model_id)
    provider = config.get("provider", "huggingface")
    model_name = config["model_name"]
    task = config.get("task", "summarization")

    if not text.strip():
        return []

    if provider != "huggingface":
        raise ValueError(f"Only huggingface provider is supported. Got: {provider}")

    # Use cached model if available
    if model_name in _model_cache:
        summarizer = _model_cache[model_name]
    else:
        try:
            # Load tokenizer and model (this may download on first use)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            # Create pipeline with the appropriate task from config
            # Supported tasks: "summarization", "text-generation"
            pipeline_task = task if task in ["text-generation", "summarization"] else "summarization"
            summarizer = pipeline(
                pipeline_task,
                model=model,
                tokenizer=tokenizer,
                device=0 if torch.cuda.is_available() else -1
            )
            _model_cache[model_name] = summarizer
        except Exception as e:
            raise RuntimeError(f"Failed to load model '{model_name}': {str(e)}. "
                             f"Check internet connection or model cache.")

    # Generate summary/facts
    try:
        # For text-generation models (like FLAN-T5), we need to provide a prompt
        if task == "text-generation":
            prompt = f"Extract the key factual statements from the following text. Return each fact as a separate sentence.\n\nText: {text}\n\nFacts:"
            result = summarizer(
                prompt,
                max_length=150,
                min_length=30,
                do_sample=False,
                truncation=True
            )
            summary = result[0]['generated_text'].strip()
        else:
            # For summarization models (BART, Pegasus)
            result = summarizer(
                text,
                max_length=150,
                min_length=30,
                do_sample=False,
                truncation=True
            )
            summary = result[0]['summary_text'].strip()
        
        # Split into sentences and clean up
        facts = _split_into_facts(summary)
        
        return facts if facts else [summary] if summary else []
        
    except Exception as e:
        raise RuntimeError(f"Failed to extract facts with model {model_name}: {str(e)}")


def _split_into_facts(text: str) -> List[str]:
    """Split extracted summary into individual facts"""
    # Split by sentence boundaries
    sentences = []
    
    # Simple sentence splitting (can be improved)
    for separator in ['. ', '! ', '? ']:
        text = text.replace(separator, '\n')
    
    raw_sentences = text.split('\n')
    
    for sentence in raw_sentences:
        sentence = sentence.strip()
        if len(sentence) > 10:  # Filter out very short fragments
            sentences.append(sentence)
    
    return sentences[:10]  # Limit to 10 facts


def get_available_models() -> List[Dict[str, Any]]:
    """Return list of available fact extraction models"""
    return list(MODEL_CONFIG.values())
