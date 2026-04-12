from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import load_config

_LANGUAGE_ALIASES = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "hindi": "hi",
    "arabic": "ar",
}

ROMANCE_LANGS = [
    "es",
    "fr",
    "it",
    "pt",
    "ro",
    "ca",
    "co",
    "fur",
    "lld",
    "rm",
    "an",
    "rup",
    "wa",
    "vec",
    "nap",
    "scn",
]


def _normalize_lang_code(language: str) -> str:
    normalized = (language or "").strip().lower()
    if not normalized:
        return normalized

    if normalized in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[normalized]

    normalized = normalized.replace("_", "-")
    if "-" in normalized:
        normalized = normalized.split("-")[0]

    return normalized


def _load_config() -> List[Dict[str, Any]]:
    config = load_config()
    models = config.get("translation_models")
    if isinstance(models, list):
        return [item for item in models if isinstance(item, dict)]
    return []


_TRANSLATION_MODELS = _load_config()
_TRANSLATION_MODEL_MAP: Dict[tuple[str, str], Dict[str, Any]] = {
    (
        _normalize_lang_code(item.get("source_lang", "")),
        _normalize_lang_code(item.get("target_lang", "")),
    ): item
    for item in _TRANSLATION_MODELS
}


def get_translation_model(
    source_lang: str, target_lang: str
) -> Optional[Dict[str, Any]]:
    return _TRANSLATION_MODEL_MAP.get(
        (_normalize_lang_code(source_lang), _normalize_lang_code(target_lang))
    )


def get_translation_model_name(source_lang: str, target_lang: str) -> Optional[str]:
    model = get_translation_model(source_lang, target_lang)
    return model.get("model_name") if model else None


def get_translation_similarity_threshold(
    source_lang: str, target_lang: str
) -> Optional[float]:
    model = get_translation_model(source_lang, target_lang)
    if model is None:
        return None
    return float(model.get("similarity_threshold", 0.0))


def get_supported_target_langs(source_lang: str = "en") -> List[str]:
    return [
        item["target_lang"]
        for item in _TRANSLATION_MODELS
        if _normalize_lang_code(item.get("source_lang", ""))
        == _normalize_lang_code(source_lang)
    ]
