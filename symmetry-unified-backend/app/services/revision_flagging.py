"""
revision_flagging.py

Standalone utility that analyses a DiffResponse and returns a list of Flags
for revisions that are significant enough to surface to editors.

Flagging rules
--------------
1. high_volume_change     – more than VOLUME_THRESHOLD of total article content
                            changed in a single revision.
2. section_removed        – one or more entire sections were deleted.
3. lead_section_modified  – the "Lead section" was significantly modified
                            (similarity below LEAD_SIMILARITY_THRESHOLD).
4. rapid_successive_edits – multiple revisions by different users within
                            RAPID_EDIT_WINDOW_HOURS (potential edit war).
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from app.models.revision import DiffResponse, Flag, Revision

# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

# Fraction of old article size that must change to trigger high_volume_change.
VOLUME_THRESHOLD: float = 0.20

# Lead-section cosine/sequence similarity below this value triggers a flag.
LEAD_SIMILARITY_THRESHOLD: float = 0.85

# How many hours to look back when detecting rapid successive edits.
RAPID_EDIT_WINDOW_HOURS: float = 1.0

# Minimum number of revisions in the window before flagging an edit war.
RAPID_EDIT_MIN_REVISIONS: int = 3


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def flag_revision(diff: DiffResponse, prev_revisions: List[Revision]) -> List[Flag]:
    """
    Analyse *diff* (a comparison between two Wikipedia revisions) together
    with the recent *prev_revisions* history and return every Flag that
    applies to the new revision.

    Parameters
    ----------
    diff:
        Structured diff produced by the revision-diff endpoint.
    prev_revisions:
        Recent revisions for the same article, newest-first.  The list
        should include the revision being reviewed (diff.new_revid) at
        index 0 so that the rapid-edit window is computed correctly.

    Returns
    -------
    List of Flag objects (may be empty).
    """
    flags: List[Flag] = []

    flags.extend(_check_volume(diff))
    flags.extend(_check_section_removed(diff))
    flags.extend(_check_lead_section(diff))
    flags.extend(_check_rapid_edits(diff, prev_revisions))

    return flags


# ---------------------------------------------------------------------------
# Individual rule implementations
# ---------------------------------------------------------------------------

def _check_volume(diff: DiffResponse) -> List[Flag]:
    """Flag when more than VOLUME_THRESHOLD of article content changed."""
    if diff.total_chars_old == 0:
        return []

    # Sum the absolute character deltas across all non-unchanged sections.
    total_changed = sum(
        abs(sd.char_delta)
        for sd in diff.section_diffs
        if sd.status in ("modified", "added", "removed")
    )

    change_ratio = total_changed / diff.total_chars_old
    if change_ratio <= VOLUME_THRESHOLD:
        return []

    severity = "high" if change_ratio > 0.50 else "medium"
    return [
        Flag(
            revid=diff.new_revid,
            reason="high_volume_change",
            severity=severity,
            detail=(
                f"{change_ratio:.1%} of article content changed in revision "
                f"{diff.new_revid} (threshold: {VOLUME_THRESHOLD:.0%})."
            ),
        )
    ]


def _check_section_removed(diff: DiffResponse) -> List[Flag]:
    """Flag when one or more entire sections were deleted."""
    removed = [sd for sd in diff.section_diffs if sd.status == "removed"]
    if not removed:
        return []

    titles = ", ".join(f'"{sd.section_title}"' for sd in removed)
    return [
        Flag(
            revid=diff.new_revid,
            reason="section_removed",
            severity="high",
            detail=f"Section(s) removed in revision {diff.new_revid}: {titles}.",
        )
    ]


def _check_lead_section(diff: DiffResponse) -> List[Flag]:
    """Flag when the Lead section was significantly modified or removed."""
    lead = next(
        (sd for sd in diff.section_diffs if sd.section_title == "Lead section"),
        None,
    )
    if lead is None or lead.status == "unchanged":
        return []

    if lead.status == "removed":
        return [
            Flag(
                revid=diff.new_revid,
                reason="lead_section_modified",
                severity="high",
                detail=f"Lead section was removed entirely in revision {diff.new_revid}.",
            )
        ]

    # status == "modified" or "added" — check similarity
    sim = lead.similarity_score
    if sim is None or sim >= LEAD_SIMILARITY_THRESHOLD:
        return []

    severity = "high" if sim < 0.60 else "medium"
    return [
        Flag(
            revid=diff.new_revid,
            reason="lead_section_modified",
            severity=severity,
            detail=(
                f"Lead section significantly modified in revision {diff.new_revid} "
                f"(similarity: {sim:.2f}, threshold: {LEAD_SIMILARITY_THRESHOLD:.2f})."
            ),
        )
    ]


def _check_rapid_edits(diff: DiffResponse, prev_revisions: List[Revision]) -> List[Flag]:
    """
    Flag when multiple different users made edits within RAPID_EDIT_WINDOW_HOURS.

    We look at all revisions (including the current one) that fall inside the
    time window anchored at the newest revision's timestamp.
    """
    if len(prev_revisions) < RAPID_EDIT_MIN_REVISIONS:
        return []

    # Parse timestamps; skip any that are malformed.
    def _parse(ts: str) -> datetime | None:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    newest_ts = _parse(prev_revisions[0].timestamp)
    if newest_ts is None:
        return []

    window_revisions = []
    for rev in prev_revisions:
        ts = _parse(rev.timestamp)
        if ts is None:
            continue
        delta_hours = abs((newest_ts - ts).total_seconds()) / 3600
        if delta_hours <= RAPID_EDIT_WINDOW_HOURS:
            window_revisions.append(rev)

    if len(window_revisions) < RAPID_EDIT_MIN_REVISIONS:
        return []

    unique_users = {r.user for r in window_revisions}
    if len(unique_users) < 2:
        return []

    oldest_in_window = _parse(window_revisions[-1].timestamp)
    elapsed = (
        abs((newest_ts - oldest_in_window).total_seconds()) / 3600
        if oldest_in_window
        else 0.0
    )

    return [
        Flag(
            revid=diff.new_revid,
            reason="rapid_successive_edits",
            severity="medium",
            detail=(
                f"{len(window_revisions)} revisions by {len(unique_users)} different "
                f"users within {elapsed:.1f} hours of revision {diff.new_revid} "
                f"(potential edit war)."
            ),
        )
    ]
