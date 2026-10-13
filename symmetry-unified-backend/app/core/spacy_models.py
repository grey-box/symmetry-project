"""
spaCy language models used by the backend.

This is the one place that says which spaCy model belongs to which language
and which models are installed by default. The services that load models
(keyword proximity, legacy AI comparison) and the install script
(scripts/install_spacy_models.py) all read from here.

This module must stay free of heavy imports. The Dockerfile copies it into the
image on its own, before the rest of the app, so the install script can run in
a cached layer.
"""

import re

# Language code -> spaCy model package. Every name here has to be a real
# package published by spaCy, otherwise installing "all" fails.
SPACY_MODEL_MAP: dict[str, str] = {
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",
    "es": "es_core_news_sm",
    "it": "it_core_news_sm",
    "pt": "pt_core_news_sm",
    "nl": "nl_core_news_sm",
    "pl": "pl_core_news_sm",
    "ru": "ru_core_news_sm",
    "zh": "zh_core_web_sm",
    "ja": "ja_core_news_sm",
    "ca": "ca_core_news_sm",
    "da": "da_core_news_sm",
    "el": "el_core_news_sm",
    "nb": "nb_core_news_sm",
    "lt": "lt_core_news_sm",
    "mk": "mk_core_news_sm",
    "ro": "ro_core_news_sm",
    "sl": "sl_core_news_sm",
    "uk": "uk_core_news_sm",
    "ko": "ko_core_news_sm",
    "fi": "fi_core_news_sm",
    "sv": "sv_core_news_sm",
    "hr": "hr_core_news_sm",
}

# Languages installed when SPACY_MODELS is unset or set to "default".
# The other languages are opt-in because together they add several hundred MB,
# and ja/zh/ko/ru/uk also pull in extra tokenizer packages.
DEFAULT_SPACY_LANGUAGES: tuple[str, ...] = ("en", "es", "fr", "de", "pt", "it")

SPACY_MODELS_ENV_VAR = "SPACY_MODELS"


def resolve_spacy_models(spec: str | None) -> list[str]:
    """
    Turn a SPACY_MODELS value into a list of model package names.

    The value is a comma or space separated list. Each entry can be a language
    code ("es"), a model name ("es_core_news_sm"), "default" for the default
    set, or "all" for every supported language. An empty or missing value means
    the default set.

    Raises ValueError if an entry is not a supported language or model.
    """
    entries = [e for e in re.split(r"[,\s]+", (spec or "").strip().lower()) if e]
    if not entries:
        entries = ["default"]

    known_models = set(SPACY_MODEL_MAP.values())
    models: list[str] = []
    unknown: list[str] = []

    for entry in entries:
        if entry == "all":
            models.extend(SPACY_MODEL_MAP.values())
        elif entry == "default":
            models.extend(SPACY_MODEL_MAP[lang] for lang in DEFAULT_SPACY_LANGUAGES)
        elif entry in SPACY_MODEL_MAP:
            models.append(SPACY_MODEL_MAP[entry])
        elif entry in known_models:
            models.append(entry)
        else:
            unknown.append(entry)

    if unknown:
        raise ValueError(
            f"Unknown spaCy language or model: {', '.join(unknown)}. "
            f"Supported languages: {', '.join(sorted(SPACY_MODEL_MAP))}"
        )

    # Drop duplicates but keep the order the user asked for.
    return list(dict.fromkeys(models))
