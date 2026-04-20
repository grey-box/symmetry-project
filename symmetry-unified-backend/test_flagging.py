"""
Quick manual test — runs the flagging pipeline against real Wikipedia revisions.
Usage (from symmetry-unified-backend/ with venv active):
    python test_flagging.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.routers.structured_wiki import _fetch_revisions, get_diff
from app.services.article_parser import revision_fetcher
from app.models.revision import DiffResponse, SectionDiff
from app.services.revision_flagging import flag_revision

# ------------------------------------------------------------------ #
# Config — change these to test different articles or revision pairs  #
# ------------------------------------------------------------------ #

ARTICLE = "2026 Iran war"
LANG = "en"
NUM_REVISIONS = 20  # how many recent revisions to pull

# Set these manually to compare two specific revisions,
# or leave as None to auto-pick the two most recent.
OLD_REVID = 1346200709  # Iskandar990 — version before the removal
NEW_REVID = 1346203534  # MarioProtIV — removed "External links" section

# ------------------------------------------------------------------ #


async def run():
    print(f"\nFetching revision history for: {ARTICLE!r}")
    revisions = await _fetch_revisions(ARTICLE, LANG, limit=NUM_REVISIONS)

    if not revisions:
        print("No revisions found.")
        return

    print(f"\nMost recent {len(revisions)} revisions:")
    for r in revisions:
        print(
            f'  [{r.revid}] {r.timestamp}  by {r.user!r}  ({r.size} bytes)  "{r.comment}"'
        )

    old_id = OLD_REVID or revisions[1].revid
    new_id = NEW_REVID or revisions[0].revid

    print(f"\nDiffing revision {old_id} → {new_id} ...")
    old_article = await revision_fetcher(old_id, LANG)
    new_article = await revision_fetcher(new_id, LANG)

    old_sections = {
        section.title: section.clean_content for section in old_article.sections
    }
    new_sections = {
        section.title: section.clean_content for section in new_article.sections
    }

    diff_response = await get_diff(old_id, new_id, ARTICLE, LANG)

    section_diffs: list[SectionDiff] = []
    for section in diff_response.sections_added:
        section_diffs.append(
            SectionDiff(
                section_title=section.section_title,
                status="added",
                old_content=None,
                new_content=section.new_content,
                similarity_score=section.similarity_score,
                char_delta=len(section.new_content or ""),
                unified_diff=None,
            )
        )
    for section in diff_response.sections_removed:
        section_diffs.append(
            SectionDiff(
                section_title=section.section_title,
                status="removed",
                old_content=section.old_content,
                new_content=None,
                similarity_score=section.similarity_score,
                char_delta=-(len(section.old_content or "")),
                unified_diff=None,
            )
        )
    for section in diff_response.sections_modified:
        section_diffs.append(
            SectionDiff(
                section_title=section.section_title,
                status="modified",
                old_content=section.old_content,
                new_content=section.new_content,
                similarity_score=section.similarity_score,
                char_delta=(
                    len(section.new_content or "") - len(section.old_content or "")
                ),
                unified_diff=None,
            )
        )

    total_chars_old = sum(len(text) for text in old_sections.values())
    total_chars_new = sum(len(text) for text in new_sections.values())

    print(f"\nSection breakdown ({len(section_diffs)} sections):")
    for sd in section_diffs:
        sim = (
            f"sim={sd.similarity_score:.3f}"
            if sd.similarity_score is not None
            else "sim=n/a"
        )
        print(
            f"  [{sd.status.upper():10s}] {sd.section_title!r:40s}  delta={sd.char_delta:+d}  {sim}"
        )

    diff = DiffResponse(
        old_revid=old_id,
        new_revid=new_id,
        title=ARTICLE,
        section_diffs=section_diffs,
        total_chars_old=total_chars_old,
        total_chars_new=total_chars_new,
    )

    print("\nRunning flagging rules ...")
    flags = flag_revision(diff, revisions)

    if not flags:
        print("  No flags raised.")
    else:
        print(f"  {len(flags)} flag(s) raised:")
        for f in flags:
            print(f"  [{f.severity.upper()}] {f.reason}")
            print(f"         {f.detail}")


if __name__ == "__main__":
    asyncio.run(run())
