"""
Central registry of supported sentence-transformer models.

Loads COMPARISON_MODELS and DEFAULT_MODEL from config.json at the
repository root when available. Falls back to the original hardcoded
defaults when the config file or keys are missing.
"""

from pathlib import Path
import json
from typing import List

_DEFAULT_MODELS: List[str] = [
    "sentence-transformers/LaBSE",
    "xlm-roberta-base",
    "multi-qa-distilbert-cos-v1",
    "multi-qa-MiniLM-L6-cos-v1",
    "multi-qa-mpnet-base-cos-v1",
]
_DEFAULT_MODEL = "sentence-transformers/LaBSE"


def _load_from_config() -> dict:
    """Search upward for config.json and load it if present."""
    for p in Path(__file__).resolve().parents:
        cfg = p / "config.json"
        if cfg.is_file():
            try:
                return json.loads(cfg.read_text(encoding="utf-8"))
            except Exception:
                return {}
    return {}


_config = _load_from_config()

COMPARISON_MODELS: List[str] = _config.get("COMPARISON_MODELS", _DEFAULT_MODELS)
DEFAULT_MODEL = _config.get("DEFAULT_MODEL", _DEFAULT_MODEL)
