"""
Ask an AI agent to explain what changed between two revisions.

The comparison work (LaBSE paragraph matching, Wikidata entities, edit
comments, risk flags) is done here first, see revision_evidence.py.  The
agent only reads that evidence and writes it up for an editor: what
changed, what the changes mean, and what deserves a closer look.
"""

import json

from app.models.revision_summary import AiRevisionSummary
from app.services.ai_agent import AgentReply, AiAgentError, ask_for_json

SYSTEM_PROMPT = """\
You help Wikipedia editors understand how an article changed between two \
revisions. You get evidence produced by comparison tools, not the full \
article, and you write a structured summary of the changes for an editor \
who has not read the diff.

How to read the evidence:
- paragraph_changes lists every paragraph that differs, biggest change \
first. "modified" paragraphs were paired by a multilingual sentence \
embedding model (LaBSE): similarity near 1.0 means the meaning barely \
changed, below about 0.8 means the paragraph says something noticeably \
different. words_removed and words_added are the exact word-level edits. \
keywords_only_before and keywords_only_after are names and terms found on \
only one side.
- "added" and "removed" paragraphs had no counterpart in the other revision.
- sections lists whole sections added, removed or renamed.
- linked_entities compares the articles' links by Wikidata item, so a link \
whose title changed but still points to the same item is not a change. \
"relinked" means the same link text now points to a different item.
- edits_between holds the edit summaries editors wrote, oldest last. Treat \
them as claims by the editors, not as facts.
- heuristic_flags come from simple rules (size of change, removed sections, \
lead edits, rapid edits) and can be false alarms.
- If paragraph_changes_left_out is present, some smaller changes were not \
included; say so in the overview.

What to write:
- headline: one sentence naming the most important change.
- overall_impact: "minor" for copy edits and formatting, "moderate" for \
added or removed facts in a few places, "substantial" for rewrites, large \
removals or changes to what the article claims.
- overview: two to four sentences in plain language.
- key_changes: the meaningful changes, most important first, at most 12. \
Merge small copy edits into one entry instead of listing each. Use \
"recontextualized" when the same fact is kept but framed differently: \
moved to another section, attributed to someone else, hedged or \
unhedged, or placed next to different information.
- semantic_shifts: places where what the article implies changed even if \
the facts look similar, for example a change in tone, certainty, \
attribution or emphasis. Leave empty if there are none.
- concerns: edits an editor should double check, such as removed sourced \
content, unexplained number or date changes, loaded or promotional \
wording, claims added without support, or signs of vandalism. Explain why \
each one matters. Leave empty if nothing stands out; do not invent concerns.
- entity_changes: the linked people, places, organizations and topics \
that were added, removed or relinked and matter to the meaning. Copy the \
Wikidata id when the evidence has one, otherwise use "".
- things_to_verify: short, concrete checks for the editor, at most 6.

Rules:
- Only use the evidence. Do not add facts about the topic from your own \
knowledge, and do not guess at an editor's motives.
- old_excerpt, new_excerpt and evidence must be short quotes (under 200 \
characters) copied from the evidence, in the article's original language. \
Use "" when there is nothing to quote.
- Write everything else in English, concisely, without markdown.
"""


def _string_enum(*values: str) -> dict:
    return {"type": "string", "enum": list(values)}


def _object(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_STRING = {"type": "string"}
_SIGNIFICANCE = _string_enum("low", "medium", "high")

# JSON schema for AiRevisionSummary, written out by hand so it follows the
# strict structured-output rules (every field required, no extra fields).
SUMMARY_SCHEMA = _object(
    {
        "headline": _STRING,
        "overall_impact": _string_enum("minor", "moderate", "substantial"),
        "overview": _STRING,
        "key_changes": {
            "type": "array",
            "items": _object(
                {
                    "section": _STRING,
                    "change_type": _string_enum(
                        "added",
                        "removed",
                        "reworded",
                        "expanded",
                        "condensed",
                        "moved",
                        "recontextualized",
                    ),
                    "description": _STRING,
                    "significance": _SIGNIFICANCE,
                    "old_excerpt": _STRING,
                    "new_excerpt": _STRING,
                }
            ),
        },
        "semantic_shifts": {
            "type": "array",
            "items": _object(
                {
                    "topic": _STRING,
                    "before": _STRING,
                    "after": _STRING,
                    "why_it_matters": _STRING,
                }
            ),
        },
        "concerns": {
            "type": "array",
            "items": _object(
                {
                    "severity": _SIGNIFICANCE,
                    "category": _string_enum(
                        "removed_content",
                        "removed_sources",
                        "neutrality",
                        "unsupported_claim",
                        "factual_change",
                        "recontextualization",
                        "possible_vandalism",
                        "other",
                    ),
                    "section": _STRING,
                    "explanation": _STRING,
                    "evidence": _STRING,
                }
            ),
        },
        "entity_changes": {
            "type": "array",
            "items": _object(
                {
                    "entity": _STRING,
                    "wikidata_id": _STRING,
                    "change": _string_enum("added", "removed", "relinked"),
                    "note": _STRING,
                }
            ),
        },
        "things_to_verify": {"type": "array", "items": _STRING},
    }
)


def build_prompt(evidence: dict) -> str:
    return (
        "Summarize the changes between these two revisions. Reply with one "
        "JSON object with the fields headline, overall_impact, overview, "
        "key_changes, semantic_shifts, concerns, entity_changes and "
        "things_to_verify.\n\n<evidence>\n"
        + json.dumps(evidence, ensure_ascii=False, indent=1)
        + "\n</evidence>"
    )


async def summarize_evidence(
    evidence: dict,
    provider: str,
    api_key: str,
    model: str | None,
    base_url: str | None = None,
) -> tuple[AiRevisionSummary, AgentReply]:
    """Send *evidence* to the agent and check its reply against the schema."""
    if not evidence["paragraph_changes"] and not any(
        evidence["sections"][k] for k in ("added", "removed", "renamed")
    ):
        # Nothing to explain, so don't spend the user's tokens.
        summary = AiRevisionSummary(
            headline="No text changes between these revisions.",
            overall_impact="minor",
            overview=(
                "The article text is the same in both revisions. The edits "
                "may have changed formatting, templates, categories or "
                "references only."
            ),
        )
        return summary, AgentReply(data={}, model="none")

    reply = await ask_for_json(
        provider,
        api_key,
        model,
        SYSTEM_PROMPT,
        build_prompt(evidence),
        SUMMARY_SCHEMA,
        base_url=base_url,
    )
    try:
        summary = AiRevisionSummary.model_validate(reply.data)
    except ValueError:
        raise AiAgentError(
            "The AI reply did not have the expected fields. Try again or "
            "pick a different model."
        ) from None
    return summary, reply
