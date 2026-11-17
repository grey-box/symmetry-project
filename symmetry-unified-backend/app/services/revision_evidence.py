"""
Collect what changed between two revisions of an article, for the AI agent.

Two comparisons feed the summary:

* LaBSE section and paragraph matching (compare_article_sections), which
  pairs each paragraph of the old revision with its closest paragraph in
  the new one, so a reworded or moved paragraph shows up as "modified"
  instead of one removal plus one addition.
* Wikidata ids of every linked name, so the agent can tell which people,
  places and topics were linked before and after, even when the wording
  around them changed or a link was redirected to a different title.

The result is a plain dict that is sent to the agent as JSON.  Identical
paragraphs are left out, and the biggest changes go first, so a long edit
history still fits in one prompt.
"""

import difflib
import json
import re

from app.models.revision import Flag, Revision
from app.models.wiki.structure import Article
from app.services.section_comparison import compare_article_sections

# Most characters of one paragraph sent to the agent.  Longer ones are cut
# in the middle so the start and end both survive.
_MAX_PARAGRAPH_CHARS = 1500

# Most characters of the whole evidence (roughly 15k tokens).  Changes past
# this are counted but left out.
_MAX_EVIDENCE_CHARS = 60_000

# Most words of one removed or added phrase inside a modified paragraph.
_MAX_PHRASE_WORDS = 60

_WORD_RE = re.compile(r"\S+")


def _shorten(text: str, limit: int = _MAX_PARAGRAPH_CHARS) -> str:
    """Cut *text* to *limit* characters, keeping the start and the end."""
    text = text.strip()
    if len(text) <= limit:
        return text
    half = (limit - len(" [...] ")) // 2
    return f"{text[:half]} [...] {text[-half:]}"


def _phrase(words: list[str]) -> str:
    if len(words) > _MAX_PHRASE_WORDS:
        words = [
            *words[: _MAX_PHRASE_WORDS // 2],
            "[...]",
            *words[-_MAX_PHRASE_WORDS // 2 :],
        ]
    return " ".join(words)


def word_changes(old_text: str, new_text: str) -> tuple[list[str], list[str]]:
    """
    Phrases removed from and added to a paragraph, word by word.

    "The city has 3 million people" -> "The city has 3.6 million residents"
    gives (["3", "people"], ["3.6", "residents"]).
    """
    old_words = _WORD_RE.findall(old_text)
    new_words = _WORD_RE.findall(new_text)
    removed: list[str] = []
    added: list[str] = []
    matcher = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op in ("delete", "replace"):
            removed.append(_phrase(old_words[i1:i2]))
        if op in ("insert", "replace"):
            added.append(_phrase(new_words[j1:j2]))
    return removed, added


# ---------------------------------------------------------------------------
# Linked entities
# ---------------------------------------------------------------------------


def _entity_key(title: str, wikidata_id: str | None) -> str:
    return wikidata_id or f"title:{title.lower()}"


def _linked_entities(article: Article) -> dict[str, dict]:
    """
    Every linked entity in *article*, keyed by Wikidata id (or by title for
    links without one), with the name it was shown as, the first section it
    appears in, and how many times it is linked.
    """
    entities: dict[str, dict] = {}
    for section in article.sections:
        for link in section.links:
            key = _entity_key(link.title, link.wikidata_id)
            if key not in entities:
                entities[key] = {
                    "name": link.title,
                    "wikidata_id": link.wikidata_id or "",
                    "section": section.title,
                    "links": 0,
                }
            entities[key]["links"] += 1
    return entities


def _relinked(old: Article, new: Article) -> list[dict]:
    """
    Link text that now points to a different item, like "Georgia" moving
    from the country to the U.S. state.
    """

    def by_text(article: Article) -> dict[str, tuple[str, str]]:
        found: dict[str, tuple[str, str]] = {}
        for section in article.sections:
            for link in section.links:
                if link.wikidata_id:
                    found.setdefault(
                        link.text.strip().lower(), (link.wikidata_id, link.title)
                    )
        return found

    old_targets = by_text(old)
    new_targets = by_text(new)
    changes = []
    for text, (old_id, old_title) in old_targets.items():
        if text in new_targets and new_targets[text][0] != old_id:
            new_id, new_title = new_targets[text]
            changes.append(
                {
                    "link_text": text,
                    "before": {"title": old_title, "wikidata_id": old_id},
                    "after": {"title": new_title, "wikidata_id": new_id},
                }
            )
    return changes


def entity_changes(old: Article, new: Article) -> dict:
    """Entities linked only in the old revision, only in the new one, or relinked."""
    old_entities = _linked_entities(old)
    new_entities = _linked_entities(new)
    removed = [v for k, v in old_entities.items() if k not in new_entities]
    added = [v for k, v in new_entities.items() if k not in old_entities]
    # Most-linked first: those matter most to the article.
    removed.sort(key=lambda e: -e["links"])
    added.sort(key=lambda e: -e["links"])
    return {"removed": removed, "added": added, "relinked": _relinked(old, new)}


# ---------------------------------------------------------------------------
# Paragraph changes
# ---------------------------------------------------------------------------


def _change_weight(change: dict) -> float:
    """Rough size of a change, used to send the biggest ones first."""
    if change["status"] == "modified":
        length = len(change.get("old_text", "")) + len(change.get("new_text", ""))
        return (1.0 - change["similarity"]) * length + 50
    return len(change.get("text", ""))


def paragraph_changes(old: Article, new: Article) -> tuple[list[dict], dict]:
    """
    Changed paragraphs between two revisions of the same article, plus the
    LaBSE section summary.  Unchanged paragraphs are skipped.
    """
    comparison = compare_article_sections(old, new)
    changes: list[dict] = []
    sections_added: list[str] = []
    sections_removed: list[str] = []
    sections_renamed: list[dict] = []

    for section in comparison.section_diffs:
        if section.status == "missing_in_target":
            sections_removed.append(section.source_title or "")
        elif section.status == "added_in_target":
            sections_added.append(section.target_title or "")
        elif section.source_title != section.target_title:
            sections_renamed.append(
                {"before": section.source_title, "after": section.target_title}
            )

        for paragraph in section.paragraph_diffs:
            old_text = (paragraph.source_text or "").strip()
            new_text = (paragraph.target_text or "").strip()
            if paragraph.status == "matched":
                if old_text == new_text:
                    continue
                removed, added = word_changes(old_text, new_text)
                changes.append(
                    {
                        "section": section.target_title or section.source_title,
                        "status": "modified",
                        "similarity": round(paragraph.similarity_score, 3),
                        "old_text": _shorten(old_text),
                        "new_text": _shorten(new_text),
                        "words_removed": removed,
                        "words_added": added,
                        "keywords_only_before": paragraph.source_exclusive_keywords,
                        "keywords_only_after": paragraph.target_exclusive_keywords,
                    }
                )
            elif paragraph.status == "missing_in_target":
                changes.append(
                    {
                        "section": section.source_title or section.target_title,
                        "status": "removed",
                        "text": _shorten(old_text),
                    }
                )
            elif paragraph.status == "added_in_target":
                changes.append(
                    {
                        "section": section.target_title or section.source_title,
                        "status": "added",
                        "text": _shorten(new_text),
                    }
                )

    changes.sort(key=_change_weight, reverse=True)
    sections = {
        "labse_overall_similarity": round(comparison.overall_similarity, 3),
        "added": sections_added,
        "removed": sections_removed,
        "renamed": sections_renamed,
    }
    return changes, sections


# ---------------------------------------------------------------------------
# Everything together
# ---------------------------------------------------------------------------


def _total_chars(article: Article) -> int:
    return sum(len(s.clean_content) for s in article.sections)


def build_revision_evidence(
    old: Article,
    new: Article,
    old_revid: int,
    new_revid: int,
    edits_between: list[Revision],
    flags: list[Flag],
) -> tuple[dict, dict]:
    """
    The evidence sent to the agent, and counts for the response.

    Wikidata ids should already be attached to both articles (see
    attach_wikidata_ids); without them entities are compared by title.
    """
    changes, sections = paragraph_changes(old, new)
    entities = entity_changes(old, new)

    evidence = {
        "article": new.title,
        "language": new.lang,
        "old_revision": old_revid,
        "new_revision": new_revid,
        "characters_before": _total_chars(old),
        "characters_after": _total_chars(new),
        "edits_between": [
            {
                "timestamp": rev.timestamp,
                "user": rev.user,
                "comment": rev.comment,
                "revision": rev.revid,
            }
            for rev in edits_between
        ],
        "heuristic_flags": [
            {"reason": f.reason, "severity": f.severity, "detail": f.detail}
            for f in flags
        ],
        "sections": sections,
        "linked_entities": {
            "removed": entities["removed"][:60],
            "added": entities["added"][:60],
            "relinked": entities["relinked"][:30],
        },
        "paragraph_changes": [],
    }

    # Add paragraph changes biggest first until the size limit.
    used = len(json.dumps(evidence, ensure_ascii=False))
    kept = 0
    for change in changes:
        size = len(json.dumps(change, ensure_ascii=False))
        if used + size > _MAX_EVIDENCE_CHARS and kept > 0:
            break
        evidence["paragraph_changes"].append(change)
        used += size
        kept += 1
    left_out = len(changes) - kept
    if left_out:
        evidence["paragraph_changes_left_out"] = left_out

    stats = {
        "sections_added": len(sections["added"]),
        "sections_removed": len(sections["removed"]),
        "paragraphs_modified": sum(1 for c in changes if c["status"] == "modified"),
        "paragraphs_added": sum(1 for c in changes if c["status"] == "added"),
        "paragraphs_removed": sum(1 for c in changes if c["status"] == "removed"),
        "entities_added": len(entities["added"]),
        "entities_removed": len(entities["removed"]),
        "edits_between": len(edits_between),
        "changes_left_out": left_out,
    }
    return evidence, stats
