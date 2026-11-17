"""Tests for matching names across languages by their Wikidata ids.

The MediaWiki API is replaced with canned responses shaped like the real
ones (action=query&prop=pageprops&formatversion=2), and spaCy keyword
extraction is replaced with fixed keyword sets, so everything runs offline.
"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from app.models.wiki.structure import Article, Section, WikiLink
from app.services import keyword_proximity, wikidata_entities
from app.services.article_parser import _parse_article_html
from app.services.keyword_proximity import extract_exclusive_keywords
from app.services.section_comparison import (
    _paragraphs_with_offsets,
    _split_into_paragraphs,
)
from app.services.wikidata_entities import (
    _ids_from_response,
    article_entity_names,
    lookup_wikidata_ids,
    paragraph_entities,
)


@pytest.fixture(autouse=True)
def empty_caches(monkeypatch):
    monkeypatch.setattr(wikidata_entities, "_wikidata_id_cache", {})
    # The fake encoder below must not leave vectors behind for other tests.
    monkeypatch.setattr(keyword_proximity, "_name_embedding_cache", {})


def _page(title: str, entity_id: str | None, ns: int = 0) -> dict:
    page: dict = {"title": title, "ns": ns}
    if entity_id:
        page["pageprops"] = {"wikibase_item": entity_id}
    return page


# ---------------------------------------------------------------------------
# Reading API responses
# ---------------------------------------------------------------------------


def test_france_and_francia_get_the_same_id():
    english = _ids_from_response(
        ["France"], {"query": {"pages": [_page("France", "Q142")]}}
    )
    spanish = _ids_from_response(
        ["Francia"], {"query": {"pages": [_page("Francia", "Q142")]}}
    )
    assert english["France"] == spanish["Francia"] == "Q142"


def test_redirect_and_lower_case_title_resolve_to_the_article_id():
    data = {
        "query": {
            "normalized": [{"from": "pablo picasso", "to": "Pablo picasso"}],
            "redirects": [
                {"from": "Picasso", "to": "Pablo Picasso"},
                {"from": "Pablo picasso", "to": "Pablo Picasso"},
            ],
            "pages": [_page("Pablo Picasso", "Q5593")],
        }
    }
    ids = _ids_from_response(["Picasso", "pablo picasso", "Pablo Picasso"], data)
    assert ids == {
        "Picasso": "Q5593",
        "pablo picasso": "Q5593",
        "Pablo Picasso": "Q5593",
    }


def test_non_article_and_missing_pages_have_no_id():
    data = {
        "query": {
            "pages": [
                _page("Category:Cubism", "Q7215812", ns=14),
                {"title": "No such page", "ns": 0, "missing": True},
            ]
        }
    }
    ids = _ids_from_response(["Category:Cubism", "No such page"], data)
    assert ids == {"Category:Cubism": None, "No such page": None}


# ---------------------------------------------------------------------------
# Batching and caching
# ---------------------------------------------------------------------------


def test_lookup_sends_50_titles_per_request_and_caches(monkeypatch):
    requests_sent: list[list[str]] = []

    def fake_post(lang, params):
        titles = params["titles"].split("|")
        requests_sent.append(titles)
        return {"query": {"pages": [_page(t, f"Q{t[1:]}") for t in titles]}}

    monkeypatch.setattr(wikidata_entities, "_post_query_sync", fake_post)
    titles = [f"T{i}" for i in range(120)]

    ids = asyncio.run(lookup_wikidata_ids(titles + ["T0"], "en"))

    assert [len(batch) for batch in requests_sent] == [50, 50, 20]
    assert ids["T7"] == "Q7"
    assert len(ids) == 120

    asyncio.run(lookup_wikidata_ids(titles, "en"))
    assert len(requests_sent) == 3, "second lookup should come from the cache"


def test_failed_lookup_returns_no_ids_and_is_not_cached(monkeypatch):
    def failing_post(lang, params):
        raise ConnectionError("rate limited")

    monkeypatch.setattr(wikidata_entities, "_post_query_sync", failing_post)
    assert asyncio.run(lookup_wikidata_ids(["France"], "en")) == {}
    assert wikidata_entities._wikidata_id_cache == {}


# ---------------------------------------------------------------------------
# Links in the parser
# ---------------------------------------------------------------------------


def test_parser_records_links_with_their_position():
    html = (
        "<h2>Life</h2>"
        '<p>Born in <a href="/wiki/M%C3%A1laga">Málaga</a>, '
        '<a href="/wiki/Picasso">Picasso</a> painted '
        '<i><a href="/wiki/Guernica_(Picasso)">Guernica</a></i>.</p>'
        '<p>He met <a href="/wiki/Georges_Braque#Cubism">Braque</a>.</p>'
        '<p><a href="/w/index.php?title=Red&amp;redlink=1">Red</a> link.</p>'
    )
    article = _parse_article_html(html, "Test", "en", "test")
    section = next(s for s in article.sections if s.title == "Life")

    assert [(link.title, link.text) for link in section.links] == [
        ("Málaga", "Málaga"),
        ("Picasso", "Picasso"),
        ("Guernica (Picasso)", "Guernica"),
        ("Georges Braque", "Braque"),
    ]
    for link in section.links:
        assert section.clean_content[link.start :].startswith(link.text)


def test_links_are_left_out_of_api_output():
    section = Section(
        title="T",
        raw_content="x",
        clean_content="x",
        links=[WikiLink(title="X", text="x", start=0)],
    )
    assert "links" not in section.model_dump()


def test_paragraph_offsets_point_back_into_the_section():
    section = Section(
        title="T",
        raw_content="",
        clean_content="First one.\n\nSecond one.\n\n\nThird.",
    )
    spans = _paragraphs_with_offsets(section)
    assert [text for text, _, _ in spans] == ["First one.", "Second one.", "Third."]
    for text, start, end in spans:
        assert section.clean_content[start:end] == text


def test_long_single_paragraph_chunks_keep_offsets():
    sentence = "Picasso painted many things in Paris. "
    content = (sentence * 40).strip()
    section = Section(title="T", raw_content="", clean_content=content)

    spans = _paragraphs_with_offsets(section)

    assert len(spans) > 1
    assert [text for text, _, _ in spans] == _split_into_paragraphs(section)
    for text, start, end in spans:
        assert content[start:end] == text


# ---------------------------------------------------------------------------
# Entities per paragraph
# ---------------------------------------------------------------------------


def _linked_section(content: str, links: list[tuple[str, str, str]]) -> Section:
    """Section whose links are (title, linked words, Wikidata id)."""
    return Section(
        title="T",
        raw_content=content,
        clean_content=content,
        links=[
            WikiLink(title=title, text=text, start=content.index(text), wikidata_id=qid)
            for title, text, qid in links
        ],
    )


def _article(lang: str, *sections: Section) -> Article:
    return Article(
        title="T", lang=lang, source="test", sections=list(sections), references=[]
    )


def test_name_linked_only_in_first_paragraph_is_found_later():
    content = (
        "Picasso was born in Málaga.\n\nLater Picasso moved to Paris with his family."
    )
    section = _linked_section(
        content,
        [("Pablo Picasso", "Picasso", "Q5593"), ("Málaga", "Málaga", "Q8851")],
    )
    names = article_entity_names(_article("en", section))
    (_, first_start, first_end), (second, second_start, second_end) = (
        _paragraphs_with_offsets(section)
    )

    later = paragraph_entities(section, second_start, second_end, second, names)
    first = paragraph_entities(
        section, first_start, first_end, content[first_start:first_end], names
    )

    assert "Q5593" in later.ids
    assert "Q8851" not in later.ids
    assert first.ids == {"Q5593", "Q8851"}


def test_name_linked_to_two_items_is_ignored():
    section = _linked_section(
        "Barcelona won. The city of Barcelona grew.",
        [
            ("FC Barcelona", "Barcelona", "Q7156"),
            ("Barcelona", "Barcelona grew", "Q1492"),
        ],
    )
    names = article_entity_names(_article("en", section))
    assert "barcelona" not in names
    assert names["fc barcelona"] == "Q7156"


# ---------------------------------------------------------------------------
# Keyword matching by id
# ---------------------------------------------------------------------------


@pytest.fixture
def fixed_keywords(monkeypatch):
    """Use the given keyword set for each text instead of running spaCy."""
    keywords_by_text: dict[str, set[str]] = {}

    def fake_extract(text, language):
        return set(keywords_by_text[text])

    monkeypatch.setattr(keyword_proximity, "_extract_concepts", fake_extract)
    return keywords_by_text


def _entities(names: dict[str, str]):
    return keyword_proximity.ParagraphEntities(
        names=names, ids=frozenset(names.values())
    )


def test_cross_script_names_match_by_id(fixed_keywords):
    fixed_keywords["en"] = {"moscow", "red square"}
    fixed_keywords["ru"] = {"москва", "красная площадь"}

    without_ids = extract_exclusive_keywords("en", "ru", "en", "ru")
    with_ids = extract_exclusive_keywords(
        "en",
        "ru",
        "en",
        "ru",
        source_entities=_entities({"moscow": "Q649", "red square": "Q46185"}),
        target_entities=_entities({"москва": "Q649", "красная площадь": "Q46185"}),
    )

    assert without_ids == (["moscow", "red square"], ["красная площадь", "москва"])
    assert with_ids == ([], [])


def test_translated_name_matches_by_id_without_an_encoder(fixed_keywords):
    fixed_keywords["en"] = {"france"}
    fixed_keywords["es"] = {"francia"}

    result = extract_exclusive_keywords(
        "en",
        "es",
        "en",
        "es",
        source_entities=_entities({"france": "Q142"}),
        target_entities=_entities({"francia": "Q142"}),
    )
    assert result == ([], [])


def test_short_name_resolves_through_full_linked_name(fixed_keywords):
    fixed_keywords["en"] = {"picasso"}
    fixed_keywords["ru"] = {"пикассо"}

    result = extract_exclusive_keywords(
        "en",
        "ru",
        "en",
        "ru",
        source_entities=_entities({"pablo picasso": "Q5593"}),
        target_entities=_entities({"пабло пикассо": "Q5593"}),
    )
    assert result == ([], [])


def test_item_linked_on_the_other_side_but_not_a_keyword_still_matches(
    fixed_keywords,
):
    fixed_keywords["en"] = {"germany"}
    fixed_keywords["de"] = {"berlin"}
    target = keyword_proximity.ParagraphEntities(
        names={"berlin": "Q64"}, ids=frozenset({"Q64", "Q183"})
    )

    source_only, _ = extract_exclusive_keywords(
        "en",
        "de",
        "en",
        "de",
        source_entities=_entities({"germany": "Q183"}),
        target_entities=target,
    )
    assert source_only == []


def test_different_items_stay_exclusive(fixed_keywords):
    fixed_keywords["en"] = {"sweden"}
    fixed_keywords["de"] = {"schweiz"}

    result = extract_exclusive_keywords(
        "en",
        "de",
        "en",
        "de",
        source_entities=_entities({"sweden": "Q34"}),
        target_entities=_entities({"schweiz": "Q39"}),
    )
    assert result == (["sweden"], ["schweiz"])


def test_unlinked_names_fall_back_to_spelling(fixed_keywords):
    fixed_keywords["en"] = {"barcelona", "unknown name"}
    fixed_keywords["fr"] = {"barcelone"}

    result = extract_exclusive_keywords(
        "en",
        "fr",
        "en",
        "fr",
        source_entities=_entities({}),
        target_entities=_entities({}),
    )
    assert result == (["unknown name"], [])


# ---------------------------------------------------------------------------
# Listing an article's links in one query, and retries
# ---------------------------------------------------------------------------


def test_article_links_are_resolved_from_the_link_list(monkeypatch):
    link_list_pages = [
        {
            "continue": {"gplcontinue": "next", "continue": "gplcontinue||"},
            "query": {
                "redirects": [{"from": "Picasso", "to": "Pablo Picasso"}],
                "pages": [_page("Pablo Picasso", "Q5593")],
            },
        },
        {"query": {"pages": [_page("Málaga", "Q8851")]}},
    ]
    requests_sent: list[dict] = []

    def fake_post(lang, params):
        requests_sent.append(params)
        if params.get("generator") == "links":
            return link_list_pages.pop(0)
        # The article itself is never in its own link list.
        return {"query": {"pages": [_page("T", "Q1")]}}

    monkeypatch.setattr(wikidata_entities, "_post_query_sync", fake_post)
    section = _linked_section(
        "Picasso was born in Málaga.",
        [("Picasso", "Picasso", None), ("Málaga", "Málaga", None)],
    )
    article = _article("en", section)

    asyncio.run(wikidata_entities.attach_wikidata_ids(article))

    assert [link.wikidata_id for link in article.sections[0].links] == [
        "Q5593",
        "Q8851",
    ]
    assert article.wikidata_id == "Q1"
    assert requests_sent[1]["gplcontinue"] == "next"
    assert [p.get("titles") for p in requests_sent[2:]] == ["T"], (
        "only the article title should need a title lookup"
    )


def test_article_title_counts_as_a_name():
    section = _linked_section("Moscow is big.", [])
    article = _article("en", section)
    article.title = "Moscow"
    article.wikidata_id = "Q649"

    names = article_entity_names(article)
    entities = paragraph_entities(section, 0, 14, "Moscow is big.", names)

    assert names == {"moscow": "Q649"}
    assert entities.ids == {"Q649"}


def test_title_lookup_stops_at_the_request_limit(monkeypatch):
    requests_sent: list[list[str]] = []

    def fake_post(lang, params):
        titles = params["titles"].split("|")
        requests_sent.append(titles)
        return {"query": {"pages": [_page(t, "Q1") for t in titles]}}

    monkeypatch.setattr(wikidata_entities, "_post_query_sync", fake_post)
    titles = [f"T{i}" for i in range(500)]

    ids = asyncio.run(lookup_wikidata_ids(titles, "en", max_requests=2))

    assert len(requests_sent) == 2
    assert len(ids) == 100


def test_ids_only_remove_flags_after_labse(fixed_keywords):
    """A pair LaBSE finds must survive when one side also matches by id."""
    fixed_keywords["en"] = {"moscow", "moskva"}
    fixed_keywords["ru"] = {"москва"}

    class Encoder:
        def __call__(self, names):
            vectors = {"moscow": [1.0, 0.0], "moskva": [0.0, 1.0], "москва": [1.0, 0.0]}
            return np.array([vectors[n] for n in names])

    result = extract_exclusive_keywords(
        "en",
        "ru",
        "en",
        "ru",
        encode_names=Encoder(),
        source_entities=_entities({"moskva": "Q649"}),
        target_entities=_entities({"москва": "Q649"}),
    )
    assert result == ([], [])


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self.headers = {"Retry-After": "0"}
        self._body = body or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._body


def test_rate_limited_request_is_retried(monkeypatch):
    replies = [_FakeResponse(429), _FakeResponse(200, {"query": {"pages": []}})]
    monkeypatch.setattr(
        wikidata_entities.requests, "post", lambda *a, **k: replies.pop(0)
    )
    assert wikidata_entities._post_query_sync("en", {"titles": "France"}) == {
        "query": {"pages": []}
    }


def test_rate_limit_gives_up_after_retries(monkeypatch):
    calls = []

    def always_limited(*args, **kwargs):
        calls.append(1)
        return _FakeResponse(429)

    monkeypatch.setattr(wikidata_entities.requests, "post", always_limited)
    with pytest.raises(RuntimeError):
        wikidata_entities._post_query_sync("en", {"titles": "France"})
    assert len(calls) == wikidata_entities._RETRIES + 1
