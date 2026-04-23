import logging
import re
import json
from collections import OrderedDict
from typing import List, Dict, Any, Tuple
import asyncio
import os

import httpx

from starlette.config import Config

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

# Load environment variables from .env file (same as main.py)
_env_config = Config(".env")

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
    Divide sentences into chunks based on sentence count.

    Each chunk will contain approximately len(sentences) / num_chunks sentences.
    This ensures that n facts are extracted from n equal groups of sentences.

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

    if num_chunks == 0:
        return []

    # Calculate sentences per chunk
    sentences_per_chunk = len(sentences) // num_chunks

    # Handle edge case: if sentences_per_chunk is 0 (more chunks than sentences)
    if sentences_per_chunk == 0:
        return [[s] for s in sentences[:num_chunks]]

    # Target words per chunk
    target_words_per_chunk = total_words / num_chunks

    chunks: List[List[str]] = []

    for i in range(num_chunks):
        start_idx = i * sentences_per_chunk
        # Last chunk gets any remaining sentences
        if i == num_chunks - 1:
            end_idx = len(sentences)
        else:
            end_idx = (i + 1) * sentences_per_chunk

        chunk = sentences[start_idx:end_idx]
        if chunk:
            chunks.append(chunk)

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
# OpenRouter API support
# ---------------------------------------------------------------------


def _build_chat_messages(prompt: str) -> List[Dict[str, str]]:
    """
    Convert a prompt string into OpenRouter chat format.

    Args:
        prompt: The prompt text (either instruction-style or plain text)

    Returns:
        List of message dictionaries in chat format
    """
    return [{"role": "user", "content": prompt}]


async def _call_openrouter_api(
    prompt: str, model_name: str, max_tokens: int = 256
) -> str:
    """
    Call OpenRouter API to generate text using a chat model.

    Uses httpx.AsyncClient so the FastAPI event loop is never blocked.

    Args:
        prompt: The prompt to send to the model
        model_name: The OpenRouter model identifier (e.g., "openrouter/free")
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text from the model

    Raises:
        ValueError: If API key is missing or API call fails
    """
    api_key = _env_config.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable is required for OpenRouter models. "
            "Please set it in your .env file."
        )

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": _build_chat_messages(prompt),
        "max_tokens": max_tokens,
        "temperature": 0.0,  # Deterministic output for fact extraction
        "top_p": 1.0,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

        result = response.json()

        if "choices" not in result or not result["choices"]:
            raise ValueError(f"OpenRouter API returned no choices: {result}")

        message = result["choices"][0].get("message", {})
        content = message.get("content", "")

        if not content:
            raise ValueError(f"OpenRouter API returned empty content: {result}")

        return content.strip()

    except httpx.HTTPStatusError as e:
        logging.error(f"OpenRouter API request failed: {e}")
        try:
            error_detail = e.response.json()
            logging.error(f"OpenRouter error detail: {error_detail}")
            raise ValueError(
                f"OpenRouter API error: {error_detail.get('error', str(e))}"
            )
        except (json.JSONDecodeError, KeyError):
            raise ValueError(f"OpenRouter API request failed: {str(e)}")
    except httpx.RequestError as e:
        logging.error(f"OpenRouter API request failed: {e}")
        raise ValueError(f"OpenRouter API request failed: {str(e)}")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logging.error(f"Failed to parse OpenRouter response: {e}")
        raise ValueError(f"Invalid response from OpenRouter: {str(e)}")


# ---------------------------------------------------------------------
# HuggingFace inference helper (runs in a thread pool via asyncio.to_thread)
# ---------------------------------------------------------------------


def _hf_inference(
    model: Any,
    tokenizer: Any,
    device: str,
    rep_penalty: float,
    prompt: str,
) -> str:
    """Run a single HuggingFace forward pass synchronously.

    Designed to be called via ``asyncio.to_thread`` so that CPU/GPU-bound
    PyTorch work never blocks the FastAPI event loop.
    """
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
    inputs_on_device = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model.generate(
            **inputs_on_device,
            max_new_tokens=256,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
            repetition_penalty=rep_penalty,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


# ---------------------------------------------------------------------
# Main extraction function (simplified)
# ---------------------------------------------------------------------


async def extract_facts(
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

    # Build chunk list once
    if num_facts == 1:
        chunks = [text]
    else:
        sentences = _split_into_sentences(text)
        if not sentences:
            return [], []
        chunks_sentences = _chunk_by_word_count(sentences, num_facts)
        chunks = [" ".join(chunk_sentences) for chunk_sentences in chunks_sentences]

    # Load / retrieve the HuggingFace model once before the chunk loop so that
    # model.to(device) and tokenizer configuration happen exactly once per call,
    # regardless of how many chunks are processed.
    hf_model = None
    hf_tokenizer = None
    device: str = "cpu"
    rep_penalty: float = 1.0

    if provider != "openrouter":
        device = "cuda" if torch.cuda.is_available() else "cpu"
        rep_penalty = config.get("repetition_penalty", 1.0)

        if model_name not in _model_cache:
            hf_tokenizer = AutoTokenizer.from_pretrained(model_name)

            hf_config = AutoConfig.from_pretrained(model_name)
            if hf_config.is_encoder_decoder:
                hf_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            else:
                hf_model = AutoModelForCausalLM.from_pretrained(model_name)

            hf_model.eval()
            hf_model.to(device)

            if hf_tokenizer.pad_token_id is None:
                hf_tokenizer.pad_token = hf_tokenizer.eos_token
                hf_model.config.pad_token_id = hf_tokenizer.pad_token_id

            if len(_model_cache) >= MODEL_CACHE_MAX_SIZE:
                _evict_lru_model()

            _model_cache[model_name] = (hf_model, hf_tokenizer)
        else:
            _model_cache.move_to_end(model_name)
            hf_model, hf_tokenizer = _model_cache[model_name]

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

        if provider == "openrouter":
            raw_output = await _call_openrouter_api(prompt, model_name, max_tokens=256)
        else:
            # Run CPU/GPU-bound PyTorch inference in a thread pool so the
            # FastAPI event loop is never blocked.
            raw_output = await asyncio.to_thread(
                _hf_inference, hf_model, hf_tokenizer, device, rep_penalty, prompt
            )

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
