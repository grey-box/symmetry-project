"""
Unit tests for app/services/revision_flagging.py

All tests are fully offline — no Wikipedia API calls are made.
Each test exercises one flagging rule in isolation so failures are easy to trace.
"""

from app.models.revision import DiffResponse, Revision, SectionDiff
from app.services.revision_flagging import (
    flag_revision,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_diff(section_diffs, total_chars_old=1000, total_chars_new=1000, new_revid=101):
    return DiffResponse(
        old_revid=100,
        new_revid=new_revid,
        title="Test Article",
        section_diffs=section_diffs,
        total_chars_old=total_chars_old,
        total_chars_new=total_chars_new,
    )


def make_revision(revid, user, minutes_ago, size=1000):
    from datetime import datetime, timezone, timedelta
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    return Revision(revid=revid, parentid=revid - 1, timestamp=ts, user=user, comment="", size=size)


def unchanged_section(title="History"):
    return SectionDiff(
        section_title=title,
        status="unchanged",
        old_content="same",
        new_content="same",
        similarity_score=1.0,
        char_delta=0,
    )


# ---------------------------------------------------------------------------
# high_volume_change
# ---------------------------------------------------------------------------

class TestVolumeFlag:
    def test_no_flag_below_threshold(self):
        diff = make_diff(
            [SectionDiff(section_title="History", status="modified",
                         old_content="a" * 100, new_content="b" * 100,
                         similarity_score=0.5, char_delta=0)],
            total_chars_old=1000,
        )
        flags = flag_revision(diff, [])
        assert not any(f.reason == "high_volume_change" for f in flags)

    def test_flag_fires_above_threshold(self):
        # section grew by 300 chars out of 1000 total = 30%, above 20% threshold
        diff = make_diff(
            [SectionDiff(section_title="History", status="modified",
                         old_content="a" * 100, new_content="b" * 400,
                         similarity_score=0.0, char_delta=300)],
            total_chars_old=1000,
        )
        flags = flag_revision(diff, [])
        reasons = [f.reason for f in flags]
        assert "high_volume_change" in reasons

    def test_severity_medium_between_thresholds(self):
        # 30% change → medium
        diff = make_diff(
            [SectionDiff(section_title="S", status="modified",
                         old_content="x", new_content="y",
                         similarity_score=0.0, char_delta=300)],
            total_chars_old=1000,
        )
        flags = flag_revision(diff, [])
        volume_flags = [f for f in flags if f.reason == "high_volume_change"]
        assert volume_flags[0].severity == "medium"

    def test_severity_high_above_50_percent(self):
        # 600 chars changed out of 1000 = 60% → high
        diff = make_diff(
            [SectionDiff(section_title="S", status="modified",
                         old_content="x", new_content="y",
                         similarity_score=0.0, char_delta=600)],
            total_chars_old=1000,
        )
        flags = flag_revision(diff, [])
        volume_flags = [f for f in flags if f.reason == "high_volume_change"]
        assert volume_flags[0].severity == "high"

    def test_no_flag_when_old_article_empty(self):
        diff = make_diff([], total_chars_old=0)
        flags = flag_revision(diff, [])
        assert not any(f.reason == "high_volume_change" for f in flags)

    def test_unchanged_sections_not_counted(self):
        diff = make_diff(
            [unchanged_section("History"), unchanged_section("Background")],
            total_chars_old=1000,
        )
        flags = flag_revision(diff, [])
        assert not any(f.reason == "high_volume_change" for f in flags)


# ---------------------------------------------------------------------------
# section_removed
# ---------------------------------------------------------------------------

class TestSectionRemovedFlag:
    def test_flag_fires_on_removed_section(self):
        diff = make_diff([
            SectionDiff(section_title="History", status="removed",
                        old_content="content", new_content=None,
                        similarity_score=None, char_delta=-100),
        ])
        flags = flag_revision(diff, [])
        assert any(f.reason == "section_removed" for f in flags)

    def test_flag_always_high_severity(self):
        diff = make_diff([
            SectionDiff(section_title="History", status="removed",
                        old_content="content", new_content=None,
                        similarity_score=None, char_delta=-100),
        ])
        flags = flag_revision(diff, [])
        removed_flags = [f for f in flags if f.reason == "section_removed"]
        assert removed_flags[0].severity == "high"

    def test_detail_contains_section_title(self):
        diff = make_diff([
            SectionDiff(section_title="External links", status="removed",
                        old_content="links", new_content=None,
                        similarity_score=None, char_delta=-50),
        ])
        flags = flag_revision(diff, [])
        removed_flags = [f for f in flags if f.reason == "section_removed"]
        assert "External links" in removed_flags[0].detail

    def test_no_flag_when_no_sections_removed(self):
        diff = make_diff([unchanged_section()])
        flags = flag_revision(diff, [])
        assert not any(f.reason == "section_removed" for f in flags)

    def test_multiple_removed_sections_single_flag(self):
        diff = make_diff([
            SectionDiff(section_title="A", status="removed",
                        old_content="a", new_content=None,
                        similarity_score=None, char_delta=-10),
            SectionDiff(section_title="B", status="removed",
                        old_content="b", new_content=None,
                        similarity_score=None, char_delta=-10),
        ])
        flags = flag_revision(diff, [])
        removed_flags = [f for f in flags if f.reason == "section_removed"]
        assert len(removed_flags) == 1
        assert "A" in removed_flags[0].detail
        assert "B" in removed_flags[0].detail


# ---------------------------------------------------------------------------
# lead_section_modified
# ---------------------------------------------------------------------------

class TestLeadSectionFlag:
    def test_flag_fires_when_similarity_below_threshold(self):
        diff = make_diff([
            SectionDiff(section_title="Lead section", status="modified",
                        old_content="old lead", new_content="completely different",
                        similarity_score=0.3, char_delta=0),
        ])
        flags = flag_revision(diff, [])
        assert any(f.reason == "lead_section_modified" for f in flags)

    def test_no_flag_when_similarity_above_threshold(self):
        diff = make_diff([
            SectionDiff(section_title="Lead section", status="modified",
                        old_content="old lead", new_content="new lead",
                        similarity_score=0.95, char_delta=0),
        ])
        flags = flag_revision(diff, [])
        assert not any(f.reason == "lead_section_modified" for f in flags)

    def test_no_flag_when_lead_unchanged(self):
        diff = make_diff([
            SectionDiff(section_title="Lead section", status="unchanged",
                        old_content="same", new_content="same",
                        similarity_score=1.0, char_delta=0),
        ])
        flags = flag_revision(diff, [])
        assert not any(f.reason == "lead_section_modified" for f in flags)

    def test_high_severity_when_similarity_very_low(self):
        diff = make_diff([
            SectionDiff(section_title="Lead section", status="modified",
                        old_content="old", new_content="new",
                        similarity_score=0.2, char_delta=0),
        ])
        flags = flag_revision(diff, [])
        lead_flags = [f for f in flags if f.reason == "lead_section_modified"]
        assert lead_flags[0].severity == "high"

    def test_medium_severity_between_thresholds(self):
        # Between 0.60 and LEAD_SIMILARITY_THRESHOLD → medium
        diff = make_diff([
            SectionDiff(section_title="Lead section", status="modified",
                        old_content="old", new_content="new",
                        similarity_score=0.70, char_delta=0),
        ])
        flags = flag_revision(diff, [])
        lead_flags = [f for f in flags if f.reason == "lead_section_modified"]
        assert lead_flags[0].severity == "medium"

    def test_flag_fires_when_lead_removed(self):
        diff = make_diff([
            SectionDiff(section_title="Lead section", status="removed",
                        old_content="old lead", new_content=None,
                        similarity_score=None, char_delta=-100),
        ])
        flags = flag_revision(diff, [])
        assert any(f.reason == "lead_section_modified" for f in flags)

    def test_no_flag_when_no_lead_section(self):
        diff = make_diff([unchanged_section("History")])
        flags = flag_revision(diff, [])
        assert not any(f.reason == "lead_section_modified" for f in flags)


# ---------------------------------------------------------------------------
# rapid_successive_edits
# ---------------------------------------------------------------------------

class TestRapidEditsFlag:
    def test_flag_fires_on_edit_war_pattern(self):
        revisions = [
            make_revision(104, "Alice", minutes_ago=0),
            make_revision(103, "Bob",   minutes_ago=15),
            make_revision(102, "Alice", minutes_ago=30),
            make_revision(101, "Bob",   minutes_ago=45),
        ]
        diff = make_diff([], new_revid=104)
        flags = flag_revision(diff, revisions)
        assert any(f.reason == "rapid_successive_edits" for f in flags)

    def test_no_flag_when_single_user(self):
        revisions = [
            make_revision(104, "Alice", minutes_ago=0),
            make_revision(103, "Alice", minutes_ago=15),
            make_revision(102, "Alice", minutes_ago=30),
        ]
        diff = make_diff([], new_revid=104)
        flags = flag_revision(diff, revisions)
        assert not any(f.reason == "rapid_successive_edits" for f in flags)

    def test_no_flag_when_outside_time_window(self):
        revisions = [
            make_revision(104, "Alice", minutes_ago=0),
            make_revision(103, "Bob",   minutes_ago=200),
            make_revision(102, "Alice", minutes_ago=400),
        ]
        diff = make_diff([], new_revid=104)
        flags = flag_revision(diff, revisions)
        assert not any(f.reason == "rapid_successive_edits" for f in flags)

    def test_no_flag_below_min_revisions(self):
        revisions = [
            make_revision(102, "Alice", minutes_ago=0),
            make_revision(101, "Bob",   minutes_ago=10),
        ]
        diff = make_diff([], new_revid=102)
        flags = flag_revision(diff, revisions)
        assert not any(f.reason == "rapid_successive_edits" for f in flags)

    def test_severity_is_medium(self):
        revisions = [
            make_revision(104, "Alice", minutes_ago=0),
            make_revision(103, "Bob",   minutes_ago=15),
            make_revision(102, "Alice", minutes_ago=30),
        ]
        diff = make_diff([], new_revid=104)
        flags = flag_revision(diff, revisions)
        rapid_flags = [f for f in flags if f.reason == "rapid_successive_edits"]
        assert rapid_flags[0].severity == "medium"

    def test_no_flag_with_empty_revision_list(self):
        diff = make_diff([])
        flags = flag_revision(diff, [])
        assert not any(f.reason == "rapid_successive_edits" for f in flags)


# ---------------------------------------------------------------------------
# Combined / multiple flags
# ---------------------------------------------------------------------------

class TestMultipleFlags:
    def test_multiple_rules_can_fire_together(self):
        # Large lead change + section removed
        diff = make_diff(
            [
                SectionDiff(section_title="Lead section", status="modified",
                             old_content="old", new_content="new",
                             similarity_score=0.2, char_delta=600),
                SectionDiff(section_title="History", status="removed",
                             old_content="content", new_content=None,
                             similarity_score=None, char_delta=-200),
            ],
            total_chars_old=1000,
        )
        flags = flag_revision(diff, [])
        reasons = {f.reason for f in flags}
        assert "lead_section_modified" in reasons
        assert "section_removed" in reasons
        assert "high_volume_change" in reasons

    def test_returns_empty_list_for_clean_revision(self):
        diff = make_diff([unchanged_section("History"), unchanged_section("Background")])
        flags = flag_revision(diff, [make_revision(100, "Alice", minutes_ago=0)])
        assert flags == []
