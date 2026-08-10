import json
import logging
import os

logger = logging.getLogger(__name__)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_PATH = os.path.join(_BASE, "config.default.json")
_OVERRIDE_PATH = os.path.join(_BASE, "config.json")

_config: dict | None = None


def load_config() -> dict:
    global _config
    if _config is not None:
        return _config

    try:
        with open(_DEFAULT_PATH) as f:
            defaults = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load config.default.json: %s", exc)
        defaults = {}

    try:
        with open(_OVERRIDE_PATH) as f:
            overrides = json.load(f)
    except Exception:  # noqa: BLE001
        overrides = {}

    _config = _deep_merge(defaults, overrides)
    logger.debug("Config loaded: %s", _config)
    return _config


def _deep_merge(base: dict, overlay: dict) -> dict:
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_translation_config() -> dict:
    return load_config().get("translation", {})
