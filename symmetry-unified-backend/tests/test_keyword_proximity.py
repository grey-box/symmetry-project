"""Tests for keyword_proximity entity handling across NER label schemes.

English spaCy models label people PERSON (OntoNotes), while most other
*_core_news_sm models label them PER / MISC (WikiNER).  These tests use blank
pipelines with an entity ruler so they run offline without extra models.
Translated-name matching uses a fake encoder with hand-set similarities
instead of LaBSE for the same reason.
"""

from __future__ import annotations

import numpy as np
import pytest
import spacy
from spacy.language import Language

from app.services import keyword_proximity
from app.services.keyword_proximity import (
    _extract_concepts,
    _names_match,
    _normalise,
    _pair_translated_names,
    extract_exclusive_keywords,
)

_ADVERBS = {"Además", "También", "Previamente"}
# Lower-case words the stub still tags as proper nouns, like the Spanish "y"
# that the English model treats as part of "José Ruiz y Blasco".
_FORCED_PROPN = {"y"}


@Language.component("test_pos_stub")
def _pos_stub(doc):
    """Stand-in tagger: capitalised words are proper nouns unless listed as adverbs."""
    for token in doc:
        token.lemma_ = token.text
        if token.text in _ADVERBS:
            token.pos_ = "ADV"
        elif token.text[:1].isupper() or token.text in _FORCED_PROPN:
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
    assert "las señoritas de aviñón" in concepts


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
    assert "ramón pichot" in concepts


# ---------------------------------------------------------------------------
# Multi-word names, elisions, accents and translated names
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def empty_name_embedding_cache(monkeypatch):
    """Each test's fake encoder must not see vectors cached by another test."""
    monkeypatch.setattr(keyword_proximity, "_name_embedding_cache", {})


def _axis(index: int, dims: int) -> np.ndarray:
    v = np.zeros(dims)
    v[index] = 1.0
    return v


def _similar(base: np.ndarray, extra_axis: int, cosine: float) -> np.ndarray:
    """A unit vector whose cosine similarity with unit vector *base* is *cosine*."""
    return cosine * base + np.sqrt(1 - cosine**2) * _axis(extra_axis, len(base))


class FakeEncoder:
    """Stands in for LaBSE: returns fixed vectors and records what it was asked."""

    def __init__(self, vectors: dict[str, np.ndarray]):
        self.vectors = vectors
        self.calls: list[list[str]] = []

    def __call__(self, names: list[str]) -> np.ndarray:
        self.calls.append(list(names))
        return np.stack([self.vectors[n] for n in names])


def _country_encoder() -> FakeEncoder:
    italy, france = _axis(0, 6), _axis(1, 6)
    return FakeEncoder(
        {
            "italy": italy,
            "italia": _similar(italy, 4, 0.95),
            "france": france,
            "francia": _similar(france, 5, 0.92),
        }
    )


@pytest.fixture
def name_models(monkeypatch):
    """Pipelines whose entities include full names and country names."""
    en = _ruler_pipeline(
        "en",
        [
            {"label": "PERSON", "pattern": "Pablo Ruiz Picasso"},
            {"label": "GPE", "pattern": "Italy"},
            {"label": "GPE", "pattern": "France"},
        ],
    )
    es = _ruler_pipeline(
        "es",
        [
            {"label": "PER", "pattern": "Pablo Picasso"},
            {"label": "LOC", "pattern": "Italia"},
            {"label": "LOC", "pattern": "Francia"},
        ],
    )
    monkeypatch.setitem(keyword_proximity._nlp_cache, "en", en)
    monkeypatch.setitem(keyword_proximity._nlp_cache, "es", es)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Pablo Ruiz Picasso", "pablo ruiz picasso"),
        ("golfe d'Italie", "golfe italie"),
        ("l’Aquila", "aquila"),
        ("Sant'Angelo", "sant angelo"),
        ("the Gulf of Naples", "gulf of naples"),
        ("Picasso's", "picasso"),
        ("Basel-Stadt", "basel stadt"),
    ],
)
def test_normalise_keeps_words_apart_and_drops_elisions(text, expected):
    assert _normalise(text) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("pablo picasso", "pablo ruiz picasso", True),
        ("picasso", "pablo ruiz picasso", True),
        ("josé ruiz y blasco", "blasco", True),
        ("málaga", "malaga", True),
        ("barcelona", "barcelone", True),
        ("josé ruiz", "pablo ruiz picasso", False),
        ("iran", "iraq", False),
        ("austria", "australia", False),
        ("france", "francia", False),
    ],
)
def test_names_match_by_spelling(a, b, expected):
    assert _names_match(a, b, keyword_proximity._CROSS_LANG_MATCH_THRESHOLD) is expected


def test_neighbouring_proper_nouns_form_one_name(monkeypatch):
    nlp = _ruler_pipeline("en", [])
    monkeypatch.setitem(keyword_proximity._nlp_cache, "en", nlp)

    assert _extract_concepts("Pablo Ruiz Picasso painted.", "en") == {
        "pablo ruiz picasso"
    }


def test_joining_word_is_trimmed_from_name(monkeypatch):
    nlp = _ruler_pipeline("en", [{"label": "PERSON", "pattern": "José Ruiz"}])
    monkeypatch.setitem(keyword_proximity._nlp_cache, "en", nlp)

    assert _extract_concepts("José Ruiz y Blasco painted.", "en") == {
        "josé ruiz",
        "blasco",
    }


def test_full_and_short_name_are_not_exclusive(name_models):
    en_only, es_only = extract_exclusive_keywords(
        "Pablo Ruiz Picasso painted.", "Pablo Picasso pintó.", "en", "es"
    )
    assert en_only == []
    assert es_only == []


def test_translated_countries_stay_exclusive_without_encoder(name_models):
    en_only, es_only = extract_exclusive_keywords(
        "Pablo Ruiz Picasso visited Italy and France.",
        "Pablo Picasso visitó Italia y Francia.",
        "en",
        "es",
    )
    assert en_only == ["france", "italy"]
    assert es_only == ["francia", "italia"]


def test_encoder_matches_translated_countries(name_models):
    encoder = _country_encoder()
    en_only, es_only = extract_exclusive_keywords(
        "Pablo Ruiz Picasso visited Italy and France.",
        "Pablo Picasso visitó Italia y Francia.",
        "en",
        "es",
        encode_names=encoder,
    )
    assert en_only == []
    assert es_only == []
    # Names already matched by spelling never reach the encoder.
    asked = {name for call in encoder.calls for name in call}
    assert asked == {"italy", "france", "italia", "francia"}


def test_encoder_is_skipped_when_spelling_matches_everything(name_models):
    encoder = _country_encoder()
    extract_exclusive_keywords(
        "Pablo Ruiz Picasso painted.",
        "Pablo Picasso pintó.",
        "en",
        "es",
        encode_names=encoder,
    )
    assert encoder.calls == []


def test_failing_encoder_falls_back_to_spelling(name_models):
    def broken(names):
        raise RuntimeError("model not available")

    en_only, es_only = extract_exclusive_keywords(
        "Pablo Ruiz Picasso visited Italy.",
        "Pablo Picasso visitó Italia.",
        "en",
        "es",
        encode_names=broken,
    )
    assert en_only == ["italy"]
    assert es_only == ["italia"]


def test_translation_pairs_must_be_mutual_best_matches():
    # "sweden" is close to the German "schweiz" (Switzerland), but
    # "switzerland" is closer, so only that pair counts.
    switzerland = _axis(0, 6)
    sweden = _similar(switzerland, 1, 0.8)
    encoder = FakeEncoder(
        {
            "switzerland": switzerland,
            "sweden": sweden,
            "schweiz": _similar(switzerland, 3, 0.95),
        }
    )
    pairs = _pair_translated_names(["sweden", "switzerland"], ["schweiz"], encoder)
    assert pairs == {("switzerland", "schweiz")}


def test_translation_pairs_below_threshold_are_ignored():
    manet = _axis(0, 4)
    encoder = FakeEncoder({"manet": manet, "mañach": _similar(manet, 2, 0.73)})
    assert _pair_translated_names(["manet"], ["mañach"], encoder) == set()
