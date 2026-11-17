"""
Tests for the AI summary of a revision-to-revision diff.

Everything runs offline: LaBSE comparison, Wikipedia, Wikidata and the AI
providers are replaced with small fakes.
"""

import asyncio
import json
from types import SimpleNamespace
from typing import ClassVar

import httpx
import pytest

from app.models.comparison.models import (
    ParagraphDiff,
    SectionCompareResponse,
    SectionDiff,
)
from app.models.revision import Flag, Revision
from app.models.wiki.structure import Article, Section, WikiLink
from app.routers import structured_wiki
from app.services import ai_agent, revision_evidence, revision_summary
from app.services.ai_agent import AiAgentError, ask_for_json
from app.services.revision_evidence import (
    build_revision_evidence,
    entity_changes,
    word_changes,
)
from app.services.revision_summary import SUMMARY_SCHEMA, summarize_evidence

SAMPLE_SUMMARY = {
    "headline": "The population figure was updated.",
    "overall_impact": "minor",
    "overview": "One number changed in the demographics section.",
    "key_changes": [
        {
            "section": "Demographics",
            "change_type": "reworded",
            "description": "Population raised from 3 to 3.6 million.",
            "significance": "medium",
            "old_excerpt": "3 million people",
            "new_excerpt": "3.6 million residents",
        }
    ],
    "semantic_shifts": [],
    "concerns": [
        {
            "severity": "low",
            "category": "factual_change",
            "section": "Demographics",
            "explanation": "The number changed without a new citation.",
            "evidence": "3.6 million",
        }
    ],
    "entity_changes": [],
    "things_to_verify": ["Check the census source for the new figure."],
}


def _article(sections: list[Section], title: str = "Lisbon") -> Article:
    return Article(
        title=title, lang="en", source="test", sections=sections, references=[]
    )


def _section(title: str, text: str, links: list[WikiLink] | None = None) -> Section:
    return Section(title=title, raw_content=text, clean_content=text, links=links or [])


def _link(title: str, text: str, wikidata_id: str | None) -> WikiLink:
    return WikiLink(title=title, text=text, start=0, wikidata_id=wikidata_id)


def _fake_comparison(section_diffs: list[SectionDiff]) -> SectionCompareResponse:
    return SectionCompareResponse(
        source_title="Lisbon",
        target_title="Lisbon",
        source_lang="en",
        target_lang="en",
        source_section_count=1,
        target_section_count=1,
        matched_section_count=1,
        missing_section_count=0,
        added_section_count=0,
        overall_similarity=0.95,
        section_diffs=section_diffs,
    )


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def test_word_changes_lists_removed_and_added_phrases():
    removed, added = word_changes(
        "The city has 3 million people.", "The city has 3.6 million residents."
    )
    assert removed == ["3", "people."]
    assert added == ["3.6", "residents."]


def test_entities_are_compared_by_wikidata_id():
    old = _article(
        [
            _section(
                "History",
                "text",
                [
                    _link("Portugal", "Portugal", "Q45"),
                    _link("Marquis of Pombal", "Pombal", "Q310953"),
                    _link("Georgia", "Georgia", "Q230"),
                ],
            )
        ]
    )
    new = _article(
        [
            _section(
                "History",
                "text",
                [
                    # Same item under another title: not a change.
                    _link("Portuguese Republic", "Portugal", "Q45"),
                    _link("Tagus", "Tagus", "Q14295"),
                    # Same text, different item.
                    _link("Georgia (U.S. state)", "Georgia", "Q1428"),
                ],
            )
        ]
    )
    changes = entity_changes(old, new)
    removed_ids = {e["wikidata_id"] for e in changes["removed"]}
    added_ids = {e["wikidata_id"] for e in changes["added"]}
    assert "Q45" not in removed_ids and "Q45" not in added_ids
    assert {"Q310953", "Q230"} == removed_ids
    assert {"Q14295", "Q1428"} == added_ids
    assert changes["relinked"] == [
        {
            "link_text": "georgia",
            "before": {"title": "Georgia", "wikidata_id": "Q230"},
            "after": {"title": "Georgia (U.S. state)", "wikidata_id": "Q1428"},
        }
    ]


def test_links_without_ids_fall_back_to_titles():
    old = _article([_section("A", "t", [_link("Red link page", "x", None)])])
    new = _article([_section("A", "t", [_link("Red link page", "x", None)])])
    changes = entity_changes(old, new)
    assert changes["removed"] == [] and changes["added"] == []


def _evidence_with(monkeypatch, paragraph_diffs, section_diffs_extra=()):
    comparison = _fake_comparison(
        [
            SectionDiff(
                source_title="Demographics",
                target_title="Demographics",
                section_similarity=0.95,
                status="matched",
                paragraph_diffs=paragraph_diffs,
            ),
            *section_diffs_extra,
        ]
    )
    monkeypatch.setattr(
        revision_evidence, "compare_article_sections", lambda a, b: comparison
    )
    old = _article([_section("Demographics", "old")])
    new = _article([_section("Demographics", "new")])
    edits = [
        Revision(
            revid=2,
            parentid=1,
            timestamp="t",
            user="Ana",
            comment="update census",
            size=10,
        )
    ]
    flags = [
        Flag(
            revid=2,
            reason="lead_section_modified",
            severity="medium",
            detail="Lead changed",
        )
    ]
    return build_revision_evidence(old, new, 1, 2, edits, flags)


def test_evidence_skips_unchanged_paragraphs_and_keeps_the_rest(monkeypatch):
    evidence, stats = _evidence_with(
        monkeypatch,
        [
            ParagraphDiff(
                source_text="Same text.",
                target_text="Same text.",
                similarity_score=1.0,
                status="matched",
            ),
            ParagraphDiff(
                source_text="The city has 3 million people.",
                target_text="The city has 3.6 million residents.",
                similarity_score=0.93,
                status="matched",
                source_exclusive_keywords=["people"],
                target_exclusive_keywords=["residents"],
            ),
            ParagraphDiff(
                source_text="A removed paragraph.", status="missing_in_target"
            ),
        ],
        [
            SectionDiff(target_title="Climate", status="added_in_target"),
        ],
    )
    statuses = [c["status"] for c in evidence["paragraph_changes"]]
    assert sorted(statuses) == ["modified", "removed"]
    modified = next(
        c for c in evidence["paragraph_changes"] if c["status"] == "modified"
    )
    assert modified["words_added"] == ["3.6", "residents."]
    assert modified["keywords_only_before"] == ["people"]
    assert evidence["sections"]["added"] == ["Climate"]
    assert evidence["edits_between"][0]["comment"] == "update census"
    assert evidence["heuristic_flags"][0]["reason"] == "lead_section_modified"
    assert stats["paragraphs_modified"] == 1
    assert stats["paragraphs_removed"] == 1
    assert stats["sections_added"] == 1
    assert stats["changes_left_out"] == 0


def test_evidence_is_capped_and_counts_what_was_left_out(monkeypatch):
    monkeypatch.setattr(revision_evidence, "_MAX_EVIDENCE_CHARS", 5_000)
    many = [
        ParagraphDiff(
            source_text=f"Paragraph {i} " + "word " * 200, status="missing_in_target"
        )
        for i in range(20)
    ]
    evidence, stats = _evidence_with(monkeypatch, many)
    assert 0 < len(evidence["paragraph_changes"]) < 20
    assert evidence["paragraph_changes_left_out"] == stats["changes_left_out"]
    assert len(evidence["paragraph_changes"]) + stats["changes_left_out"] == 20
    assert len(json.dumps(evidence)) < 5_000 + 2_000


def test_long_paragraphs_keep_their_start_and_end():
    text = "start " + "middle " * 1000 + "end"
    short = revision_evidence._shorten(text, 100)
    assert short.startswith("start") and short.endswith("end") and "[...]" in short
    assert len(short) <= 100


# ---------------------------------------------------------------------------
# AI providers
# ---------------------------------------------------------------------------


class FakeAnthropic:
    """Stands in for anthropic.AsyncAnthropic and records the request."""

    last_request: ClassVar[dict] = {}
    last_key: str = ""

    def __init__(self, api_key, timeout):
        FakeAnthropic.last_key = api_key
        self.messages = SimpleNamespace(create=self._create)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        FakeAnthropic.last_request = kwargs
        return SimpleNamespace(
            stop_reason=FakeAnthropic.stop_reason,
            content=[SimpleNamespace(type="text", text=json.dumps(SAMPLE_SUMMARY))],
            model=kwargs["model"],
            usage=SimpleNamespace(input_tokens=1200, output_tokens=300),
        )

    stop_reason = "end_turn"


@pytest.fixture
def fake_anthropic(monkeypatch):
    FakeAnthropic.stop_reason = "end_turn"
    monkeypatch.setattr(ai_agent.anthropic, "AsyncAnthropic", FakeAnthropic)
    return FakeAnthropic


def test_claude_request_uses_the_schema_and_fallbacks(fake_anthropic):
    reply = asyncio.run(
        ask_for_json("anthropic", "sk-test", None, "system", "prompt", SUMMARY_SCHEMA)
    )
    request = fake_anthropic.last_request
    assert fake_anthropic.last_key == "sk-test"
    assert request["model"] == "claude-opus-5-5"
    assert request["output_config"]["format"] == {
        "type": "json_schema",
        "schema": SUMMARY_SCHEMA,
    }
    assert request["output_config"]["effort"] == "medium"
    assert request["fallbacks"] == "default"
    assert reply.data["headline"] == SAMPLE_SUMMARY["headline"]
    assert (reply.input_tokens, reply.output_tokens) == (1200, 300)


def test_older_claude_models_get_no_effort_or_fallbacks(fake_anthropic):
    asyncio.run(
        ask_for_json(
            "anthropic", "sk-test", "claude-haiku-4-5", "s", "p", SUMMARY_SCHEMA
        )
    )
    request = fake_anthropic.last_request
    assert "effort" not in request["output_config"]
    assert "fallbacks" not in request


def test_claude_refusal_is_reported(fake_anthropic):
    fake_anthropic.stop_reason = "refusal"
    with pytest.raises(AiAgentError) as error:
        asyncio.run(
            ask_for_json("anthropic", "sk-test", None, "s", "p", SUMMARY_SCHEMA)
        )
    assert error.value.status == 422


def test_missing_key_is_reported_before_calling_anyone():
    with pytest.raises(AiAgentError) as error:
        asyncio.run(ask_for_json("anthropic", "", None, "s", "p", SUMMARY_SCHEMA))
    assert error.value.status == 400
    assert "Settings" in str(error.value)


def _openai_transport(monkeypatch, handler):
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        ai_agent.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=transport, **kw),
    )


def _chat_reply(content: str, finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "gpt-test",
            "choices": [
                {"message": {"content": content}, "finish_reason": finish_reason}
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    )


def test_openai_compatible_request_and_fenced_reply(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return _chat_reply("```json\n" + json.dumps(SAMPLE_SUMMARY) + "\n```")

    _openai_transport(monkeypatch, handler)
    reply = asyncio.run(ask_for_json("openai", "sk-o", None, "s", "p", SUMMARY_SCHEMA))
    assert str(seen[0].url) == "https://api.openai.com/v1/chat/completions"
    assert seen[0].headers["Authorization"] == "Bearer sk-o"
    body = json.loads(seen[0].content)
    assert body["response_format"]["type"] == "json_schema"
    assert reply.data["overall_impact"] == "minor"
    assert reply.output_tokens == 5


def test_json_schema_rejected_falls_back_to_json_mode(monkeypatch):
    formats = []

    def handler(request):
        body = json.loads(request.content)
        formats.append(body["response_format"]["type"])
        if body["response_format"]["type"] == "json_schema":
            return httpx.Response(400, json={"error": {"message": "not supported"}})
        return _chat_reply(json.dumps(SAMPLE_SUMMARY))

    _openai_transport(monkeypatch, handler)
    asyncio.run(ask_for_json("groq", "gsk", None, "s", "p", SUMMARY_SCHEMA))
    assert formats == ["json_schema", "json_object"]


def test_bad_key_gives_401_without_echoing_the_key(monkeypatch):
    _openai_transport(
        monkeypatch,
        lambda request: httpx.Response(
            401, json={"error": {"message": "Incorrect API key"}}
        ),
    )
    with pytest.raises(AiAgentError) as error:
        asyncio.run(
            ask_for_json("openai", "sk-secret-123", None, "s", "p", SUMMARY_SCHEMA)
        )
    assert error.value.status == 401
    assert "sk-secret-123" not in str(error.value)


def test_custom_endpoint_needs_no_key(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return _chat_reply(json.dumps(SAMPLE_SUMMARY))

    _openai_transport(monkeypatch, handler)
    asyncio.run(
        ask_for_json(
            "custom",
            "",
            "llama3.1",
            "s",
            "p",
            SUMMARY_SCHEMA,
            base_url="http://localhost:11434/v1/",
        )
    )
    assert str(seen[0].url) == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in seen[0].headers


def test_cut_off_reply_is_reported(monkeypatch):
    _openai_transport(
        monkeypatch, lambda request: _chat_reply('{"headline": "x', "length")
    )
    with pytest.raises(AiAgentError, match="cut off"):
        asyncio.run(ask_for_json("openai", "k", None, "s", "p", SUMMARY_SCHEMA))


# ---------------------------------------------------------------------------
# Summary and endpoint
# ---------------------------------------------------------------------------


def _empty_evidence():
    return {
        "paragraph_changes": [],
        "sections": {
            "added": [],
            "removed": [],
            "renamed": [],
            "labse_overall_similarity": 1.0,
        },
    }


def test_no_text_changes_skips_the_ai_call(monkeypatch):
    async def fail(*args, **kwargs):
        raise AssertionError("the AI should not be called")

    monkeypatch.setattr(revision_summary, "ask_for_json", fail)
    summary, reply = asyncio.run(
        summarize_evidence(_empty_evidence(), "anthropic", "k", None)
    )
    assert summary.overall_impact == "minor"
    assert reply.model == "none"


def test_reply_missing_fields_is_an_error(monkeypatch):
    async def bad_reply(*args, **kwargs):
        return ai_agent.AgentReply(data={"headline": "only this"}, model="m")

    monkeypatch.setattr(revision_summary, "ask_for_json", bad_reply)
    evidence = _empty_evidence()
    evidence["paragraph_changes"] = [{"status": "added", "text": "x"}]
    with pytest.raises(AiAgentError, match="expected fields"):
        asyncio.run(summarize_evidence(evidence, "anthropic", "k", None))


@pytest.fixture
def offline_endpoint(monkeypatch):
    """The revision-ai-summary endpoint with Wikipedia and the AI faked."""
    calls = {}

    async def fake_revision(revid, lang):
        text = (
            "The city has 3 million people."
            if revid == 1
            else "The city has 3.6 million residents."
        )
        return _article([_section("Demographics", text)])

    async def fake_wikidata(article):
        calls["wikidata"] = calls.get("wikidata", 0) + 1

    async def fake_between(title, lang, old, new):
        return [
            Revision(
                revid=2, parentid=1, timestamp="t", user="Ana", comment="census", size=1
            )
        ]

    comparison = _fake_comparison(
        [
            SectionDiff(
                source_title="Demographics",
                target_title="Demographics",
                status="matched",
                paragraph_diffs=[
                    ParagraphDiff(
                        source_text="The city has 3 million people.",
                        target_text="The city has 3.6 million residents.",
                        similarity_score=0.93,
                        status="matched",
                    )
                ],
            )
        ]
    )

    async def fake_ask(provider, api_key, model, system, prompt, schema, base_url=None):
        calls["key"] = api_key
        calls["prompt"] = prompt
        return ai_agent.AgentReply(
            data=SAMPLE_SUMMARY,
            model="claude-opus-5-5",
            input_tokens=9,
            output_tokens=3,
        )

    monkeypatch.setattr(structured_wiki, "revision_fetcher", fake_revision)
    monkeypatch.setattr(structured_wiki, "attach_wikidata_ids", fake_wikidata)
    monkeypatch.setattr(structured_wiki, "_fetch_revisions_between", fake_between)
    monkeypatch.setattr(
        revision_evidence, "compare_article_sections", lambda a, b: comparison
    )
    monkeypatch.setattr(revision_summary, "ask_for_json", fake_ask)
    return calls


def test_endpoint_returns_the_structured_summary(client, offline_endpoint):
    response = client.post(
        "/symmetry/v1/wiki/revision-ai-summary",
        json={"old_revid": 1, "new_revid": 2, "title": "Lisbon", "lang": "en"},
        headers={"X-AI-API-Key": " sk-test "},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"]["headline"] == SAMPLE_SUMMARY["headline"]
    assert body["summary"]["key_changes"][0]["new_excerpt"] == "3.6 million residents"
    assert body["evidence_stats"]["paragraphs_modified"] == 1
    assert body["evidence_stats"]["edits_between"] == 1
    assert body["model"] == "claude-opus-5-5"
    assert offline_endpoint["key"] == "sk-test"
    assert offline_endpoint["wikidata"] == 2
    assert "3.6 million residents" in offline_endpoint["prompt"]
    assert "sk-test" not in offline_endpoint["prompt"]


def test_endpoint_rejects_the_same_revision_twice(client, offline_endpoint):
    response = client.post(
        "/symmetry/v1/wiki/revision-ai-summary",
        json={"old_revid": 5, "new_revid": 5, "title": "Lisbon"},
    )
    assert response.status_code == 400


def test_endpoint_passes_provider_errors_through(client, offline_endpoint, monkeypatch):
    async def no_key(*args, **kwargs):
        raise AiAgentError("Add your Anthropic API key in Settings first.", 400)

    monkeypatch.setattr(revision_summary, "ask_for_json", no_key)
    response = client.post(
        "/symmetry/v1/wiki/revision-ai-summary",
        json={"old_revid": 1, "new_revid": 2, "title": "Lisbon"},
    )
    assert response.status_code == 400
    assert "Settings" in response.json()["detail"]
