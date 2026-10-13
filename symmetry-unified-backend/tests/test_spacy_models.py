"""
Tests for the shared spaCy model map and the model install script.

Nothing here downloads anything. The install script's download and
"is it installed" checks are replaced with fakes.
"""

import logging
import re

import pytest

from app.core.spacy_models import (
    DEFAULT_SPACY_LANGUAGES,
    SPACY_MODEL_MAP,
    resolve_spacy_models,
)
from app.services import keyword_proximity
from scripts import install_spacy_models

# The small pipelines spaCy publishes for spaCy 3.8, taken from the
# spacy-models compatibility table. If spaCy adds a language, add it here and
# to SPACY_MODEL_MAP together.
PUBLISHED_SMALL_MODELS = {
    "ca_core_news_sm",
    "da_core_news_sm",
    "de_core_news_sm",
    "el_core_news_sm",
    "en_core_web_sm",
    "es_core_news_sm",
    "fi_core_news_sm",
    "fr_core_news_sm",
    "hr_core_news_sm",
    "it_core_news_sm",
    "ja_core_news_sm",
    "ko_core_news_sm",
    "lt_core_news_sm",
    "mk_core_news_sm",
    "nb_core_news_sm",
    "nl_core_news_sm",
    "pl_core_news_sm",
    "pt_core_news_sm",
    "ro_core_news_sm",
    "ru_core_news_sm",
    "sl_core_news_sm",
    "sv_core_news_sm",
    "uk_core_news_sm",
    "zh_core_web_sm",
}


# ---------------------------------------------------------------------------
# Model map
# ---------------------------------------------------------------------------


def test_every_mapped_model_is_published_by_spacy():
    unpublished = set(SPACY_MODEL_MAP.values()) - PUBLISHED_SMALL_MODELS
    assert not unpublished, f"Not real spaCy packages: {sorted(unpublished)}"


def test_model_names_start_with_their_language_code():
    for language, model_name in SPACY_MODEL_MAP.items():
        assert re.fullmatch(rf"{language}_core_(web|news)_sm", model_name)


def test_default_languages_are_all_in_the_map():
    assert set(DEFAULT_SPACY_LANGUAGES) <= set(SPACY_MODEL_MAP)
    assert "en" in DEFAULT_SPACY_LANGUAGES


def test_services_share_the_same_map():
    from app.ai import comparison

    assert keyword_proximity._SPACY_MODEL_MAP is SPACY_MODEL_MAP
    assert comparison._SPACY_MODEL_MAP is SPACY_MODEL_MAP


# ---------------------------------------------------------------------------
# SPACY_MODELS parsing
# ---------------------------------------------------------------------------

DEFAULT_MODELS = [SPACY_MODEL_MAP[lang] for lang in DEFAULT_SPACY_LANGUAGES]


@pytest.mark.parametrize("spec", [None, "", "   ", "default", "DEFAULT"])
def test_missing_or_default_value_gives_the_default_set(spec):
    assert resolve_spacy_models(spec) == DEFAULT_MODELS


def test_all_gives_every_model():
    assert resolve_spacy_models("all") == list(SPACY_MODEL_MAP.values())


@pytest.mark.parametrize(
    "spec",
    ["es,ja", "es ja", " es ,  ja ", "ES,JA", "es_core_news_sm,ja_core_news_sm"],
)
def test_language_codes_and_model_names_are_both_accepted(spec):
    assert resolve_spacy_models(spec) == ["es_core_news_sm", "ja_core_news_sm"]


def test_duplicates_are_removed_and_order_is_kept():
    assert resolve_spacy_models("ja,es,es_core_news_sm,ja") == [
        "ja_core_news_sm",
        "es_core_news_sm",
    ]


def test_default_can_be_extended_with_more_languages():
    assert resolve_spacy_models("default,ja") == [*DEFAULT_MODELS, "ja_core_news_sm"]


def test_unknown_entries_are_reported_by_name():
    with pytest.raises(ValueError, match="sk, en_core_web_lg"):
        resolve_spacy_models("es,sk,en_core_web_lg")


# ---------------------------------------------------------------------------
# Install script
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_installer(monkeypatch):
    """
    Replace the script's package lookup and downloader.

    Returns a dict the test can edit: "installed" is the set of models already
    present, "broken" is the set whose download fails, and "downloaded" records
    what the script tried to download.
    """
    state = {"installed": set(), "broken": set(), "downloaded": []}

    def fake_is_installed(model_name):
        return model_name in state["installed"]

    def fake_download(model_name):
        state["downloaded"].append(model_name)
        return model_name not in state["broken"]

    monkeypatch.setattr(install_spacy_models, "is_installed", fake_is_installed)
    monkeypatch.setattr(install_spacy_models, "download", fake_download)
    monkeypatch.delenv("SPACY_MODELS", raising=False)
    return state


def test_script_installs_the_default_set_when_nothing_is_configured(fake_installer):
    assert install_spacy_models.main([]) == 0
    assert fake_installer["downloaded"] == DEFAULT_MODELS


def test_script_reads_the_environment_variable(fake_installer, monkeypatch):
    monkeypatch.setenv("SPACY_MODELS", "en,ja")
    assert install_spacy_models.main([]) == 0
    assert fake_installer["downloaded"] == ["en_core_web_sm", "ja_core_news_sm"]


def test_command_line_models_win_over_the_environment(fake_installer, monkeypatch):
    monkeypatch.setenv("SPACY_MODELS", "all")
    assert install_spacy_models.main(["fr"]) == 0
    assert fake_installer["downloaded"] == ["fr_core_news_sm"]


def test_script_skips_models_that_are_already_installed(fake_installer):
    fake_installer["installed"] = {"en_core_web_sm"}
    assert install_spacy_models.main(["en", "es"]) == 0
    assert fake_installer["downloaded"] == ["es_core_news_sm"]


def test_failed_download_gives_exit_code_1_but_keeps_going(fake_installer, capsys):
    fake_installer["broken"] = {"es_core_news_sm"}
    assert install_spacy_models.main(["es", "fr"]) == 1
    assert fake_installer["downloaded"] == ["es_core_news_sm", "fr_core_news_sm"]
    assert "Could not install: es_core_news_sm" in capsys.readouterr().err


def test_unknown_language_gives_exit_code_2_and_downloads_nothing(
    fake_installer, capsys
):
    assert install_spacy_models.main(["es", "klingon"]) == 2
    assert fake_installer["downloaded"] == []
    assert "klingon" in capsys.readouterr().err


def test_list_shows_status_without_downloading(fake_installer, capsys):
    fake_installer["installed"] = {"en_core_web_sm"}
    assert install_spacy_models.main(["--list"]) == 0
    assert fake_installer["downloaded"] == []
    output = capsys.readouterr().out
    assert re.search(r"en\s+en_core_web_sm\s+installed", output)
    assert re.search(r"ja\s+ja_core_news_sm\s+missing", output)


# ---------------------------------------------------------------------------
# Behaviour when a model is not installed
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_nlp_cache(monkeypatch):
    monkeypatch.setattr(keyword_proximity, "_nlp_cache", {})


def test_missing_model_logs_a_warning_and_falls_back(
    empty_nlp_cache, monkeypatch, caplog
):
    import spacy

    def model_not_found(name):
        raise OSError(f"[E050] Can't find model '{name}'")

    monkeypatch.setattr(spacy, "load", model_not_found)

    with caplog.at_level(logging.WARNING, logger=keyword_proximity.logger.name):
        assert keyword_proximity._load_nlp("de") is None

    assert "de_core_news_sm" in caplog.text
    assert "not installed" in caplog.text

    # The capital-letter fallback still finds the proper noun.
    concepts = keyword_proximity._extract_concepts("Sie wohnte in Berlin.", "de")
    assert "berlin" in concepts


def test_language_without_a_model_does_not_try_to_load_one(
    empty_nlp_cache, monkeypatch
):
    import spacy

    def should_not_be_called(name):
        raise AssertionError(f"spacy.load was called for {name}")

    monkeypatch.setattr(spacy, "load", should_not_be_called)
    assert keyword_proximity._load_nlp("sk") is None


@pytest.mark.parametrize("language", DEFAULT_SPACY_LANGUAGES)
def test_installed_default_models_load_and_tag_entities(language, empty_nlp_cache):
    model_name = SPACY_MODEL_MAP[language]
    if not install_spacy_models.is_installed(model_name):
        pytest.skip(f"{model_name} is not installed")

    nlp = keyword_proximity._load_nlp(language)
    assert nlp is not None
    assert "ner" in nlp.pipe_names
