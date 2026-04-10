import logging
import re
from collections import OrderedDict
from typing import List, Dict, Any, Tuple
import os

import spacy
from spacy.language import Language
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForCausalLM,
    AutoConfig,
)
from huggingface_hub import model_info

from app.core.config import load_config

# ---------------------------------------------------------------------
# Load model config from backend config.toml
# ---------------------------------------------------------------------


def _load_fact_extraction_config() -> Dict[str, Any]:
    config = load_config()
    models = config.get("fact_extraction_models")
    if not isinstance(models, list):
        return {}
    return {
        entry["id"]: entry
        for entry in models
        if isinstance(entry, dict) and "id" in entry
    }


MODEL_CONFIG = _load_fact_extraction_config()

# Cache: model_name -> (model, tokenizer)
MODEL_CACHE_MAX_SIZE = int(os.getenv("FACT_EXTRACTION_MODEL_CACHE_SIZE", "3"))
_model_cache: "OrderedDict[str, Tuple[Any, Any]]" = OrderedDict()

_spacy_sentence_segmenter: Language | None = None


def _get_spacy_sentence_segmenter() -> Language:
    global _spacy_sentence_segmenter
    if _spacy_sentence_segmenter is None:
        nlp = spacy.blank("en")
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        _spacy_sentence_segmenter = nlp
    return _spacy_sentence_segmenter


def _evict_lru_model() -> None:
    """Evict the least recently used model from the cache."""
    if not _model_cache:
        return

    evicted_name, (evicted_model, _) = _model_cache.popitem(last=False)

    try:
        evicted_model.to("cpu")
    except Exception as e:
        logging.warning(f"Could not move evicted model {evicted_name} to CPU: {e}")

    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass

    logging.info(f"Evicted least recently used model from cache: {evicted_name}")


def model_exists_on_hf(model_name: str) -> bool:
    """
    Check if a model exists on HuggingFace Hub.
    Uses huggingface_hub.model_info() which automatically uses HF_TOKEN from environment.

    Args:
        model_name: The HuggingFace model ID to check

    Returns:
        True if model exists and is accessible, False otherwise
    """
    try:
        model_info(model_name)
        return True
    except Exception as e:
        logging.error(f"Error checking model {model_name}: {e}")
        return False


def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using spaCy sentence segmentation for improved
    accuracy. Falls back to regex-based splitting if spaCy segmentation fails.
    """
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []

    try:
        nlp = _get_spacy_sentence_segmenter()
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        if sentences:
            return sentences
    except Exception as e:
        logging.warning(
            f"spaCy sentence segmentation failed, falling back to regex: {e}"
        )

    # Fallback for any unexpected spaCy failure.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _chunk_by_word_count(sentences: List[str], num_chunks: int) -> List[List[str]]:
    """
    Divide sentences into approximately equal chunks by word count.

    Args:
        sentences: List of sentences to chunk
        num_chunks: Number of chunks to create (will be capped by len(sentences))

    Returns:
        List of chunks, where each chunk is a list of sentences
    """
    if not sentences:
        return []

    # Cap num_chunks to number of sentences
    num_chunks = min(num_chunks, len(sentences))

    # Calculate word count for each sentence
    sentence_word_counts = [len(s.split()) for s in sentences]
    total_words = sum(sentence_word_counts)

    if total_words == 0:
        return [[s] for s in sentences[:num_chunks]]

    # Target words per chunk
    target_words_per_chunk = total_words / num_chunks

    chunks: List[List[str]] = []
    current_chunk: List[str] = []
    current_word_count = 0

    for sentence, word_count in zip(sentences, sentence_word_counts):
        # If adding this sentence would exceed the target and we still have chunks to allocate
        if (
            current_word_count + word_count > target_words_per_chunk
            and len(chunks) < num_chunks - 1
        ):
            if current_chunk:  # Don't add empty chunks
                chunks.append(current_chunk)
            current_chunk = [sentence]
            current_word_count = word_count
        else:
            current_chunk.append(sentence)
            current_word_count += word_count

    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    # If we have fewer chunks than requested, redistribute some sentences
    # This can happen if sentences are very large
    while len(chunks) < num_chunks and chunks:
        # Find the largest chunk
        largest_idx = max(range(len(chunks)), key=lambda i: len(chunks[i]))
        largest_chunk = chunks[largest_idx]

        if len(largest_chunk) <= 1:
            break  # Can't split further

        # Split the largest chunk in half
        mid = len(largest_chunk) // 2
        new_chunk1 = largest_chunk[:mid]
        new_chunk2 = largest_chunk[mid:]

        chunks[largest_idx] = new_chunk1
        chunks.append(new_chunk2)

    return chunks


def get_model_config(model_id: str) -> Dict[str, Any]:
    """
    Get model configuration. First checks predefined configs, then treats
    the model_id as a HuggingFace model name if it's not in the config.

    Args:
        model_id: Either a predefined model ID from the backend config or a HuggingFace model name (e.g., "google/flan-t5-large")

    Returns:
        Model configuration dictionary
    """
    config = MODEL_CONFIG.get(model_id)
    if config:
        return config

    # If not in predefined configs, treat as custom HuggingFace model
    # Validate that the model exists on HF Hub
    if model_exists_on_hf(model_id):
        # Return a minimal config for custom models
        return {
            "id": model_id,
            "name": model_id,
            "provider": "huggingface",
            "model_name": model_id,
            "description": f"Custom HuggingFace model: {model_id}",
            "task": "text2text-generation",  # Default, will be auto-detected
            "prompt_style": "instruction",
            "use_chat_template": False,
        }

    raise ValueError(
        f"Model ID '{model_id}' not found in config and does not exist on HuggingFace Hub"
    )


def get_available_models() -> List[Dict[str, Any]]:
    """
    Get list of all available fact extraction models.
    Returns predefined models from config file.
    Custom HuggingFace models are validated on-demand, not listed here.

    Returns:
        List of model configuration dictionaries
    """
    return list(MODEL_CONFIG.values())


def validate_model(model_id: str) -> Dict[str, Any]:
    """
    Validate that a model exists on HuggingFace Hub and return its config.
    This supports both predefined models and custom HuggingFace models.

    Args:
        model_id: Model ID (predefined or HuggingFace model name)

    Returns:
        Model configuration dictionary if valid

    Raises:
        ValueError: If model does not exist or is invalid
    """
    try:
        config = get_model_config(model_id)
        return config
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"Failed to validate model '{model_id}': {str(e)}")


# ---------------------------------------------------------------------
# Main extraction function (simplified)
# ---------------------------------------------------------------------


def extract_facts(
    text: str, model_id: str, num_facts: int = 1
) -> Tuple[List[str], List[str]]:
    """
    Extract facts from text using the specified model.

    Args:
        text: The text content to extract facts from
        model_id: The ID of the model to use
        num_facts: Number of facts to extract (also determines number of model calls).
                  The text will be chunked and each chunk sent to the model.
                  Default is 1 (no chunking).

    Returns:
        Tuple of (facts, chunks) where:
        - facts: List of extracted facts (strings)
        - chunks: List of text chunks that were processed
        Empty lists if no text.
    """
    if not text.strip():
        return [], []

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

        if len(_model_cache) >= MODEL_CACHE_MAX_SIZE:
            _evict_lru_model()

        _model_cache[model_name] = (model, tokenizer)
    else:
        _model_cache.move_to_end(model_name)

    model, tokenizer = _model_cache[model_name]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
        model.config.pad_token_id = tokenizer.pad_token_id

    # If num_facts is 1, process the whole text at once (backward compatible)
    if num_facts == 1:
        chunks = [text]
    else:
        # Split text into sentences and chunk
        sentences = _split_into_sentences(text)
        if not sentences:
            return [], []
        chunks_sentences = _chunk_by_word_count(sentences, num_facts)
        chunks = [" ".join(chunk_sentences) for chunk_sentences in chunks_sentences]

    all_facts: List[str] = []
    processed_chunks: List[str] = []

    for chunk in chunks:
        if not chunk.strip():
            continue

        # Build prompt based on prompt_style in model config
        prompt_style = config.get("prompt_style", "plain")

        if prompt_style == "prefix":
            # T5-style models expect a task prefix rather than an instruction wrapper
            prefix = config.get("prompt_prefix", "")
            prompt = f"{prefix}{chunk}"

        elif prompt_style == "plain":
            # Summarization models (e.g. distilbart) were trained on raw text
            prompt = chunk

        else:
            prompt = (
                "Extract all explicit facts from the text below.\n\n"
                "Return them as bullet points.\n\n"
                f"Text:\n{chunk}\n\n"
                "Facts:"
            )

        inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        rep_penalty = config.get("repetition_penalty", 1.0)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
                repetition_penalty=rep_penalty,
            )

        raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Parse the output into individual facts (handle bullet points and newlines)
        facts_from_chunk = _parse_facts(raw_output)
        all_facts.extend(facts_from_chunk)
        processed_chunks.append(chunk)

    return all_facts, processed_chunks


def _parse_facts(raw_output: str) -> List[str]:
    """
    Parse raw model output into a list of individual facts.
    Handles bullet points, numbered lists, and newline-separated facts.
    """
    # Split by newlines
    lines = raw_output.strip().split("\n")

    facts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove bullet point markers and numbering
        # Handles: -, *, •, 1., 1), etc.
        cleaned = re.sub(r"^[\s]*([-*•]|\d+[.)])\s+", "", line)
        cleaned = cleaned.strip()

        if cleaned:
            facts.append(cleaned)

    # If no bullet points found, treat the whole output as one fact
    if not facts and raw_output.strip():
        return [raw_output.strip()]

    return facts
