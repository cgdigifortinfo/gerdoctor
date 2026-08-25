"""Exhaustive tests for partner insight aggregation and mapping."""
from datetime import datetime, timezone

from slices.partner_insights.domain import build_partner_insights
from slices.partner_insights.mappers import (
    insight_partner_from_document,
    insight_profile_from_document,
    insight_submission_from_document,
)
from slices.partner_insights.models import (
    InsightPartner,
    InsightProfile,
    InsightSnapshot,
    InsightSubmission,
)


NOW = datetime(2026, 8, 24, 12, 34, 56, 789, tzinfo=timezone.utc)


def snapshot(partner, submissions=(), accepted=(), profiles=None):
    return InsightSnapshot(partner, tuple(submissions), frozenset(accepted), profiles or {})


def test_mappers_normalize_current_legacy_and_missing_documents():
    active = insight_partner_from_document({
        "_id": 1, "name": "P", "registration_status": "active",
        "is_active": True, "survey_ids": ["s"], "linked_user_ids": [2],
    })
    assert active == InsightPartner("1", "P", False, frozenset({"2"}))
    assert insight_partner_from_document(None) == InsightPartner("", "", True)
    assert insight_partner_from_document({
        "id": "public", "_id": "mongo", "registration_status": "active",
        "is_active": True, "survey_ids": ["s"],
    }).id == "public"
    assert insight_partner_from_document({
        "registration_status": "pending", "is_active": True, "survey_ids": ["s"],
    }).awaiting_assignment
    assert insight_partner_from_document({
        "registration_status": "active", "is_active": False, "survey_ids": ["s"],
    }).awaiting_assignment
    assert insight_partner_from_document({"registration_status": "active", "is_active": True}).awaiting_assignment
    assert insight_submission_from_document({
        "user_id": 1, "step_id": 2, "created_at": "current", "submitted_at": "legacy",
    }) == InsightSubmission("1", "2", "current")
    assert insight_submission_from_document({"submitted_at": "legacy"}).submitted_at == "legacy"
    assert insight_submission_from_document({}) == InsightSubmission("", "", "")
    assert insight_profile_from_document({"fachrichtung_gewuenscht": "A", "anerkennungsverfahren_bundesland": "B"}) == InsightProfile("A", "B")
    assert insight_profile_from_document({"fachrichtung_praktiziert": "P"}).specialty == "P"
    assert insight_profile_from_document({"field_of_study": "F"}).specialty == "F"
    assert insight_profile_from_document({}) == InsightProfile()


def test_awaiting_partner_gets_empty_continuous_30_day_result():
    result = build_partner_insights(snapshot(InsightPartner("p", "P", True)), {}, {}, NOW)
    assert set(result) == {
        "new_submissions_7d", "new_submissions_30d", "total_linked_users",
        "by_fachrichtung", "by_bundesland", "conversion_funnel",
        "conversion_rate_pct", "timeline_30d",
    }
    assert result == {
        "new_submissions_7d": 0, "new_submissions_30d": 0,
        "total_linked_users": 0, "by_fachrichtung": [], "by_bundesland": [],
        "conversion_funnel": {"received": 0, "accepted": 0, "completed": 0},
        "conversion_rate_pct": 0,
        "timeline_30d": result["timeline_30d"],
    }
    assert len(result["timeline_30d"]) == 30
    assert result["timeline_30d"][0] == {"date": "2026-07-26", "count": 0}


def test_active_insights_aggregate_windows_funnel_profiles_and_fallback_completion():
    partner = InsightPartner("p", "P", False, frozenset({"linked", "u1"}))
    submissions = (
        InsightSubmission("u1", "s1", "2026-08-24T10:00:00+00:00"),
        InsightSubmission("u1", "s2", "2026-08-18T10:00:00+00:00"),
        InsightSubmission("u2", "s3", "2026-07-26T10:00:00+00:00"),
        InsightSubmission("", "", ""),
    )
    result = build_partner_insights(snapshot(
        partner, submissions, {"u1"},
        {"u1": InsightProfile("Innere", "Berlin"), "u2": InsightProfile("Innere", "Hamburg")},
    ), {("u1", "s1"): True, ("u1", "s2"): False}, {"u2": True}, NOW)
    assert result["new_submissions_7d"] == 2
    assert result["new_submissions_30d"] == 3
    assert result["total_linked_users"] == 3
    assert result["conversion_funnel"] == {"received": 4, "accepted": 2, "completed": 2}
    assert result["conversion_rate_pct"] == 50
    assert result["by_fachrichtung"][0] == {"label": "Innere", "count": 2}
    assert sum(row["count"] for row in result["timeline_30d"]) == 3
    assert all(set(row) == {"date", "count"} for row in result["timeline_30d"])


def test_empty_active_partner_has_zero_rate_and_facets_are_limited_to_ten():
    profiles = {f"u{i}": InsightProfile(f"S{i}", f"B{i}") for i in range(12)}
    partner = InsightPartner("p", "P", False, frozenset(profiles))
    result = build_partner_insights(snapshot(partner, profiles=profiles), {}, {}, NOW)
    assert result["conversion_rate_pct"] == 0
    assert len(result["by_fachrichtung"]) == 10
    assert len(result["by_bundesland"]) == 10


def test_boundaries_duplicates_explicit_completion_and_conversion_are_exact():
    partner = InsightPartner("p", "P", False)
    submissions = (
        InsightSubmission("accepted", "now", NOW.isoformat()),
        InsightSubmission("accepted", "cutoff7", "2026-08-17T12:34:56.000789+00:00"),
        InsightSubmission("other", "cutoff30", "2026-07-26T00:00:00+00:00"),
        InsightSubmission("other", "same-day", "2026-07-26T01:00:00+00:00"),
        InsightSubmission("other", "outside7", "2026-08-16T18:00:00+00:00"),
        InsightSubmission("other", "outside30", "2026-07-25T12:00:00+00:00"),
    )
    result = build_partner_insights(snapshot(
        partner, submissions, {"accepted"},
        {
            "accepted": InsightProfile("S", "Same"),
            "other": InsightProfile("T", "Same"),
        },
    ), {("accepted", "now"): False}, {"accepted": True, "other": False}, NOW)
    assert result["new_submissions_7d"] == 2
    assert result["new_submissions_30d"] == 5
    assert result["conversion_funnel"] == {"received": 6, "accepted": 2, "completed": 1}
    assert result["conversion_rate_pct"] == 33
    assert result["by_bundesland"] == [{"label": "Same", "count": 2}]
    assert next(row for row in result["timeline_30d"] if row["date"] == "2026-07-26")["count"] == 2


def test_single_accepted_submission_has_hundred_percent_conversion():
    submission = InsightSubmission("u", "s", "")
    result = build_partner_insights(snapshot(
        InsightPartner("p", "P", False), (submission,), {"u"},
    ), {}, {}, NOW)
    assert result["conversion_rate_pct"] == 100
