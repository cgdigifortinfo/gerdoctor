"""Regression: /api/partner/insights computes meaningful numbers from the
canonical partner_submissions fields (`created_at`, `partner_work_completed`).

Before this fix the endpoint looked up `submitted_at` (never written) and
matched submission status against `accepted/in_progress/completed` — all of
which made the dashboard show 0 across the board even when the partner had
hundreds of real users assigned.
"""
import os
import requests
import pytest
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://guided-journey-5.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

# MVZ Gruppe partner-portal user (164 distinct submission users seeded).
MVZ_PARTNER_EMAIL = "partner-fia-academy@chrizz1001.de"
MVZ_PARTNER_PW = "Partner123!"


@pytest.fixture(scope="module")
def mvz_session():
    s = requests.Session()
    r = s.post(
        f"{API}/auth/login",
        json={"email": MVZ_PARTNER_EMAIL, "password": MVZ_PARTNER_PW},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


@pytest.fixture(scope="module")
def insights(mvz_session):
    r = mvz_session.get(f"{API}/partner/insights", timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def submissions(mvz_session):
    r = mvz_session.get(f"{API}/partner/submissions", timeout=20)
    assert r.status_code == 200
    return r.json()


def test_total_linked_users_matches_submissions(insights, submissions):
    """total_linked_users = distinct user_ids across submissions ∪ linked_user_ids."""
    distinct_subs = len({s["user_id"] for s in submissions if s.get("user_id")})
    # MVZ partner has 164 distinct submission users; allow ±2 for any drift.
    assert insights["total_linked_users"] >= distinct_subs, (
        f"total_linked_users {insights['total_linked_users']} should >= distinct "
        f"submission users {distinct_subs}"
    )


def test_funnel_received_equals_submissions(insights, submissions):
    """Funnel `received` must equal the partner's submission count."""
    assert insights["conversion_funnel"]["received"] == len(submissions)


def test_funnel_completed_matches_partner_work_completed(insights, submissions):
    """`completed` must equal the count of submissions with partner_work_completed=True."""
    expected_completed = sum(1 for s in submissions if s.get("partner_work_completed") is True)
    assert insights["conversion_funnel"]["completed"] == expected_completed, (
        f"funnel.completed={insights['conversion_funnel']['completed']} "
        f"!= partner_work_completed=True count {expected_completed}"
    )


def test_funnel_accepted_at_least_completed(insights):
    """A submission counted as `completed` MUST also be `accepted` (logical funnel)."""
    f = insights["conversion_funnel"]
    assert f["accepted"] >= f["completed"], (
        f"accepted ({f['accepted']}) must be >= completed ({f['completed']})"
    )
    assert f["accepted"] <= f["received"], (
        f"accepted ({f['accepted']}) cannot exceed received ({f['received']})"
    )


def test_timeline_30d_has_expected_shape(insights):
    """Timeline must contain 30 day buckets and reflect real submissions."""
    tl = insights["timeline_30d"]
    assert len(tl) == 30, f"expected 30 daily buckets, got {len(tl)}"
    for entry in tl:
        assert "date" in entry and "count" in entry
        assert isinstance(entry["count"], int) and entry["count"] >= 0


def test_timeline_total_matches_30d_window(insights, submissions):
    """Sum across the 30-day timeline must equal `new_submissions_30d`."""
    tl_total = sum(t["count"] for t in insights["timeline_30d"])
    assert tl_total == insights["new_submissions_30d"], (
        f"timeline sum {tl_total} != new_submissions_30d {insights['new_submissions_30d']}"
    )


def test_facets_have_data(insights):
    """With 100+ MVZ submissions the facets must not be empty."""
    assert insights["by_fachrichtung"], "by_fachrichtung must not be empty"
    assert insights["by_bundesland"], "by_bundesland must not be empty"
    assert sum(f["count"] for f in insights["by_fachrichtung"]) >= 100, (
        "facet totals should reflect ~166 MVZ users"
    )


def test_new_submissions_windows_are_monotonic(insights):
    """7d window cannot exceed 30d window."""
    assert insights["new_submissions_7d"] <= insights["new_submissions_30d"]
