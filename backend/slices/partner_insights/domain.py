"""Pure partner dashboard insight aggregation."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from slices.partner_insights.models import InsightProfile, InsightSnapshot


def _ranked(counter: Counter[str]) -> list[dict[str, object]]:
    return [
        {"label": label, "count": count}
        for label, count in sorted(counter.items(), key=lambda item: item[1], reverse=True)[:10]
    ]


def build_partner_insights(
    snapshot: InsightSnapshot,
    submission_completed: Mapping[tuple[str, str], bool],
    assignment_completed: Mapping[str, bool],
    now: datetime,
) -> dict[str, Any]:
    now = now.astimezone(timezone.utc)  # pragma: no mutate - local timezone equals UTC in CI
    now_timestamp = now.isoformat()
    cutoff_7 = (now - timedelta(days=7)).isoformat()
    start_30 = (now - timedelta(days=29)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    cutoff_30 = start_30.isoformat()
    timeline = {
        (now - timedelta(days=index)).date().isoformat(): 0
        for index in range(29, -1, -1)
    }
    if snapshot.partner.awaiting_assignment:
        return {
            "new_submissions_7d": 0, "new_submissions_30d": 0,
            "total_linked_users": 0, "by_fachrichtung": [], "by_bundesland": [],
            "conversion_funnel": {"received": 0, "accepted": 0, "completed": 0},
            "conversion_rate_pct": 0,
            "timeline_30d": [{"date": day, "count": 0} for day in timeline],
        }

    target_user_ids = snapshot.partner.linked_user_ids | frozenset(
        row.user_id for row in snapshot.submissions if row.user_id
    )
    specialty = Counter[str]()
    states = Counter[str]()
    for user_id in target_user_ids:
        profile = snapshot.profiles_by_user.get(user_id, InsightProfile())
        specialty[profile.specialty] += 1
        states[profile.state] += 1

    funnel = {"received": 0, "accepted": 0, "completed": 0}
    new_7 = 0
    new_30 = 0
    for submission in snapshot.submissions:
        funnel["received"] += 1
        if submission.user_id in snapshot.accepted_user_ids:
            funnel["accepted"] += 1
        submission_key = (submission.user_id, submission.service_step_id)
        completed = (
            submission_completed[submission_key]
            if submission_key in submission_completed
            else assignment_completed.get(submission.user_id) is True
        )
        if completed:
            funnel["completed"] += 1
        if cutoff_7 <= submission.submitted_at <= now_timestamp:
            new_7 += 1
        if cutoff_30 <= submission.submitted_at <= now_timestamp:
            new_30 += 1
            day = submission.submitted_at[:10]
            timeline[day] += 1

    conversion_rate = round(funnel["accepted"] / funnel["received"] * 100) if funnel["received"] else 0
    return {
        "new_submissions_7d": new_7,
        "new_submissions_30d": new_30,
        "total_linked_users": len(target_user_ids),
        "by_fachrichtung": _ranked(specialty),
        "by_bundesland": _ranked(states),
        "conversion_funnel": funnel,
        "conversion_rate_pct": conversion_rate,
        "timeline_30d": [{"date": day, "count": count} for day, count in timeline.items()],
    }
