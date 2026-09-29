"""Tests for keyword_proximity entity handling across NER label schemes.

English spaCy models label people PERSON (OntoNotes), while most other
*_core_news_sm models label them PER / MISC (WikiNER).  These tests use blank
pipelines with an entity ruler so they run offline without extra models.
"""

from __future__ import annotations

import pytest
import spacy
from spacy.language import Language

from app.services import keyword_proximity
from app.services.keyword_proximity import _extract_concepts, extract_exclusive_keywords

_ADVERBS = {"Además", "También", "Previamente"}


@Language.component("test_pos_stub")
def _pos_stub(doc):
    """Stand-in tagger: capitalised words are proper nouns unless listed as adverbs."""
    for token in doc:
        if token.text in _ADVERBS:
            token.pos_ = "ADV"
        elif token.text[:1].isupper():
            token.pos_ = "PROPN"
        else:
            token.pos_ = "X"
    return doc


def _ruler_pipeline(lang: str, patterns: list[dict]):
    nlp = spacy.blank(lang)
    nlp.add_pipe("test_pos_stub")
    nlp.add_pipe("entity_ruler").add_patterns(patterns)
    return nlp


@pytest.fixture
def fake_models(monkeypatch):
    """English pipeline with OntoNotes labels, Spanish with WikiNER labels."""
    en = _ruler_pipeline(
        "en",
        [
            {"label": "PERSON", "pattern": "Picasso"},
            {"label": "PERSON", "pattern": "Braque"},
            {"label": "GPE", "pattern": "Paris"},
        ],
    )
    es = _ruler_pipeline(
        "es",
        [
            {"label": "PER", "pattern": "Picasso"},
            {"label": "PER", "pattern": "Braque"},
            {"label": "LOC", "pattern": "París"},
            {"label": "MISC", "pattern": "Guernica"},
        ],
    )
    monkeypatch.setitem(keyword_proximity._nlp_cache, "en", en)
    monkeypatch.setitem(keyword_proximity._nlp_cache, "es", es)


def test_wikiner_person_and_misc_entities_are_concepts(fake_models):
    concepts = _extract_concepts("Picasso pintó el Guernica en París.", "es")
    assert {"picasso", "guernica", "parís"} <= concepts


def test_person_in_both_languages_is_not_exclusive(fake_models):
    en_only, es_only = extract_exclusive_keywords(
        "Picasso met Braque in Paris.",
        "Picasso conoció a Braque en París.",
        "en",
        "es",
    )
    assert "picasso" not in en_only
    assert "braque" not in en_only
    assert "picasso" not in es_only


def test_person_missing_from_target_is_still_exclusive(fake_models):
    en_only, _ = extract_exclusive_keywords(
        "Picasso met Braque in Paris.",
        "Picasso vivió en París.",
        "en",
        "es",
    )
    assert "braque" in en_only
    assert "picasso" not in en_only


def test_wikiner_entity_without_proper_noun_is_dropped(monkeypatch):
    # The small Spanish model tags adverbs like these as PER, LOC or MISC.
    # "Aviñón" makes the last span a real title.
    nlp = _ruler_pipeline(
        "es",
        [
            {"label": "PER", "pattern": "Además"},
            {"label": "LOC", "pattern": "Previamente"},
            {"label": "MISC", "pattern": "También"},
            {"label": "MISC", "pattern": "Las señoritas de Aviñón"},
        ],
    )
    monkeypatch.setitem(keyword_proximity._nlp_cache, "es", nlp)

    concepts = _extract_concepts(
        "Además pintó Las señoritas de Aviñón. Previamente vivió en París. "
        "También pintó mucho.",
        "es",
    )
    assert "además" not in concepts
    assert "previamente" not in concepts
    assert "también" not in concepts
    assert "lasseñoritasdeaviñón" in concepts


def test_ontonotes_entity_without_proper_noun_is_kept(monkeypatch):
    # English models tag nationalities like "Spanish" as NORP adjectives;
    # the proper noun requirement must not apply to them.
    nlp = _ruler_pipeline("en", [{"label": "NORP", "pattern": "spanish"}])
    monkeypatch.setitem(keyword_proximity._nlp_cache, "en", nlp)

    assert "spanish" in _extract_concepts("He was a spanish painter.", "en")


@pytest.mark.skipif(
    not spacy.util.is_package("es_core_news_sm"),
    reason="es_core_news_sm not installed",
)
def test_real_spanish_model_keeps_people(monkeypatch):
    monkeypatch.delitem(keyword_proximity._nlp_cache, "es", raising=False)
    concepts = _extract_concepts(
        "Picasso y Fernande pasaron el verano de 1910 en Cadaqués, "
        "donde su amigo Ramón Pichot pasaba las vacaciones.",
        "es",
    )
    assert "picasso" in concepts
    assert "ramónpichot" in concepts
