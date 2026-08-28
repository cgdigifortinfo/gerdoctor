"""Complete unit coverage for the legacy helper facade and its orchestration branches."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

import helpers


class Cursor:
    def __init__(self, rows): self.rows = list(rows)
    def __aiter__(self):
        async def values():
            for row in self.rows: yield row
        return values()
    def sort(self, *_args): return self
    async def to_list(self, _limit): return self.rows


class Collection:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.find_one = AsyncMock(return_value=None)
        self.insert_one = AsyncMock()
        self.count_documents = AsyncMock(return_value=0)
        self.update_one = AsyncMock()
    def find(self, *_args, **_kwargs): return Cursor(self.rows)


class Document:
    def __init__(self, document): self.document = document


@pytest.mark.anyio
async def test_email_facade_success_missing_and_delivery(monkeypatch) -> None:
    sent = SimpleNamespace(to_document=lambda: {"status": "success"})
    monkeypatch.setattr(helpers.smtp_email_gateway, "send_sync", MagicMock(return_value=sent))
    assert helpers.send_email_sync("a@b.test", "s", "h") == {"status": "success"}
    monkeypatch.setattr(helpers, "send_email_sync", MagicMock(return_value={"status": "thread"}))
    assert await helpers.send_email_notification("a", "s", "h") == {"status": "thread"}

    rendered = SimpleNamespace(to_document=lambda: {"subject": "S", "html": "H"})
    service = SimpleNamespace(
        email=AsyncMock(return_value=rendered), notification=AsyncMock(return_value=rendered),
        send_rendered=AsyncMock(return_value=SimpleNamespace(
            status="success", error=None, to_document=lambda: {"status": "success"})),
    )
    monkeypatch.setattr(helpers, "email_notifications_service", service)
    assert (await helpers.render_email("key", None))["subject"] == "S"
    assert (await helpers.render_notification("key", None))["html"] == "H"
    assert await helpers.send_rendered_email("a", "key", None) == {"status": "success"}
    service.email.side_effect = helpers.TemplateNotFound("key")
    service.notification.side_effect = helpers.TemplateNotFound("key")
    assert await helpers.render_email("missing", {}) == {}
    assert await helpers.render_notification("missing", {}) == {}
    service.send_rendered.return_value = SimpleNamespace(
        status="skipped", error="missing", to_document=lambda: {"status": "skipped"})
    assert await helpers.send_rendered_email("a", "key", {}) == {"status": "skipped", "reason": "missing"}


@pytest.mark.anyio
async def test_submission_notifications_cover_recipients_preferences_and_failures(monkeypatch) -> None:
    valid_id = str(ObjectId())
    users = Collection([
        {"email": "role@test", "notification_prefs": {}},
        {"email": "off@test", "notification_prefs": {"email": False}},
        {"notification_prefs": {}},
    ])
    users.find_one.side_effect = [
        {"email": "linked@test", "role": "partner", "notification_prefs": {}},
        {"email": "wrong@test", "role": "user"},
        {"email": "off2@test", "role": "partner", "notification_prefs": {"email": False}},
        {"role": "partner", "notification_prefs": {}},
    ]
    monkeypatch.setattr(helpers, "db", SimpleNamespace(users=users))
    deliveries = []
    async def send(recipient, *_args):
        deliveries.append(recipient)
        if recipient == "linked@test": raise RuntimeError("smtp")
        return {"status": "failed" if recipient == "role@test" else "success"}
    monkeypatch.setattr(helpers, "send_rendered_email", send)
    partner = {"_id": ObjectId(), "name": "School", "contact_email": "contact@test",
               "linked_user_ids": [valid_id, valid_id, valid_id, valid_id, "invalid"]}
    count = await helpers.notify_partner_of_new_submission(
        partner, {"id": "u", "email": "doctor@test"},
        {"fachrichtung_praktiziert": "Innere", "anerkennungsverfahren_bundesland": "BE", "step_order": 2},
    )
    assert count == 1
    assert set(deliveries) == {"contact@test", "role@test", "linked@test"}
    assert await helpers.notify_partner_of_new_submission({}, {}, {}) == 0
    monkeypatch.setattr(helpers, "db", SimpleNamespace(users=Collection([])))
    assert await helpers.notify_partner_of_new_submission({"id": "p"}, {}, {}) == 0


@pytest.mark.anyio
@pytest.mark.parametrize("function,pref", [
    (helpers.notify_user_awaiting_partner, "email_on_step_enter"),
    (helpers.notify_user_milestone_completed, "email_on_step_leave"),
])
async def test_user_notifications_skip_opt_out_succeed_and_fail(monkeypatch, function, pref) -> None:
    extra = ({"title": "Milestone", "order": 2, "description": "D"},) if function is helpers.notify_user_milestone_completed else ()
    assert (await function({}, {}, *extra))["status"] == "skipped"
    assert (await function({"email": "u@test", "notification_preferences": {pref: False}}, {}, *extra))["reason"] == "opt-out"
    sender = AsyncMock(return_value={"status": "success"})
    monkeypatch.setattr(helpers, "send_rendered_email", sender)
    assert (await function({"email": "u@test", "name": "U"}, {"name": "P"}, *extra))["status"] == "success"
    sender.side_effect = RuntimeError("down")
    assert (await function({"email": "u@test"}, {}, *extra))["error"] == "down"


@pytest.mark.anyio
async def test_audit_runtime_facade_and_context(monkeypatch) -> None:
    audit = SimpleNamespace(record=AsyncMock())
    monkeypatch.setattr(helpers, "audit_trail_service", audit)
    await helpers.create_audit_log("a", "e", "x", "user", "u", {"x": 1})
    audit.record.assert_awaited_once()
    monkeypatch.setattr(helpers, "runtime_add_duration", lambda *args: args)
    monkeypatch.setattr(helpers, "runtime_is_progress_gate_condition", lambda value: value == {"gate": 1})
    monkeypatch.setattr(helpers, "runtime_evaluate_condition", lambda cond, state: bool(cond and state))
    assert helpers.add_duration("d", 1, "days") == ("d", 1, "days")
    assert helpers._is_progress_gate_condition({"gate": 1})
    assert helpers._evaluate_condition({"x": 1}, {1: {}})
    context = SimpleNamespace(steps=[Document({"_id": "s"})])
    monkeypatch.setattr(helpers.survey_runtime_service, "context", AsyncMock(return_value=context))
    monkeypatch.setattr(helpers, "runtime_visibility", lambda _ctx: SimpleNamespace(
        hidden_step_ids=frozenset({"h"}), blocked_step_ids=frozenset({"b"})))
    monkeypatch.setattr(helpers, "runtime_order_state", lambda _ctx: {1: {}})
    assert await helpers._get_step_context("u") == ([{"_id": "s"}], {1: {}}, {"h"}, {"b"})
    monkeypatch.setattr(helpers, "runtime_context_from_documents", lambda steps, _progress: SimpleNamespace(steps=[Document(s) for s in steps]))
    monkeypatch.setattr(helpers, "runtime_completion_steps", lambda steps, hidden: [s for s in steps if str(s.document["_id"]) not in hidden])
    assert helpers._completion_denominator_steps([{"_id": "s"}], set()) == [{"_id": "s"}]


@pytest.mark.anyio
async def test_auto_complete_computation_and_application(monkeypatch) -> None:
    steps = [
        {"_id": "hidden", "conditions": []},
        {"_id": "done", "conditions": []},
        {"_id": "plain", "conditions": [{"action": "hide"}]},
        {"_id": "no", "conditions": [{"action": "auto_complete", "match": False}]},
        {"_id": "yes", "conditions": [{"action": "auto_complete", "match": True}]},
    ]
    monkeypatch.setattr(helpers, "_get_step_context", AsyncMock(return_value=(steps, {1: {}}, {"hidden"}, set())))
    progress = Collection([{"step_id": "done", "status": "completed"}])
    monkeypatch.setattr(helpers, "db", SimpleNamespace(user_progress=progress))
    monkeypatch.setattr(helpers, "_evaluate_condition", lambda cond, _state: cond.get("match", False))
    assert await helpers.compute_auto_complete_steps("u") == ["yes"]

    sid1, sid2, sid3 = str(ObjectId()), str(ObjectId()), str(ObjectId())
    monkeypatch.setattr(helpers, "compute_auto_complete_steps", AsyncMock(return_value=[sid1, sid2, sid3]))
    user_progress = Collection()
    user_progress.find_one.side_effect = [
        {"status": "completed"}, {"data": {"kept": True}, "started_at": "old"}, None,
    ]
    steps_collection = Collection()
    steps_collection.find_one.side_effect = [
        {"_id": ObjectId(sid2), "survey_id": "survey", "title": "T", "order": 2}, None,
    ]
    history = Collection()
    revision = AsyncMock()
    monkeypatch.setattr(helpers, "write_progress_revision", revision)
    monkeypatch.setattr(helpers, "db", SimpleNamespace(
        user_progress=user_progress, steps=steps_collection, progress_history=history))
    assert await helpers.apply_auto_completes("u") == [sid1, sid2, sid3]
    revision.assert_awaited_once()
    assert history.insert_one.await_count == 2


@pytest.mark.anyio
async def test_status_skip_all_guard_and_write_branches(monkeypatch) -> None:
    assert await helpers.apply_anerkennungsstatus_skips("u", "") == []
    assert await helpers.apply_anerkennungsstatus_skips("u", "unknown") == []
    status = "Ich habe die Fachsprachenprüfung Medizin bestanden"
    decision = {"_id": ObjectId(), "order": 7, "is_active": True, "step_type": "decision"}
    milestone = {"_id": ObjectId(), "order": 10, "is_active": True, "step_type": "milestone"}
    steps = Collection()
    steps.find_one.side_effect = [decision, None, milestone]
    progress = Collection()
    progress.find_one.side_effect = [{"status": "completed"}, {"started_at": "old"}]
    history = Collection()
    revision = AsyncMock()
    monkeypatch.setattr(helpers, "write_progress_revision", revision)
    monkeypatch.setattr(helpers, "db", SimpleNamespace(steps=steps, user_progress=progress, progress_history=history))
    result = await helpers.apply_anerkennungsstatus_skips("u", status)
    assert result == [str(milestone["_id"])]
    revision.assert_awaited_once()
    monkeypatch.setitem(helpers.BLOCK_DEFINITIONS, "Fachsprachenprüfung", (7, None, 10))
    steps.find_one.side_effect = [decision, milestone]
    progress.find_one.side_effect = [None, {"status": "completed"}]
    assert await helpers.apply_anerkennungsstatus_skips("u", status) == [str(decision["_id"])]


@pytest.mark.anyio
async def test_completion_and_user_metrics_all_paths(monkeypatch) -> None:
    step1, step2 = {"_id": "1", "duration_value": 1, "duration_unit": "days"}, {"_id": "2", "duration_value": 2, "duration_unit": "days"}
    step3 = {"_id": "3", "duration_value": 0, "duration_unit": "days"}
    monkeypatch.setattr(helpers, "_get_step_context", AsyncMock(return_value=([], {}, set(), set())))
    assert await helpers.calculate_completion_pct("u") == 0
    progress = Collection()
    progress.count_documents.return_value = 1
    monkeypatch.setattr(helpers, "_get_step_context", AsyncMock(return_value=([step1, step2, step3], {}, set(), set())))
    monkeypatch.setattr(helpers, "_completion_denominator_steps", lambda steps, _hidden: steps)
    monkeypatch.setattr(helpers, "db", SimpleNamespace(user_progress=progress))
    assert await helpers.calculate_completion_pct("u") == 33

    rows = [
        {"step_id": "1", "status": "completed", "completed_at": "2026-01-02T00:00:00+00:00"},
        {"step_id": "2", "status": "completed", "completed_at": "invalid"},
        {"step_id": "3", "status": "completed", "completed_at": "2026-01-01T00:00:00+00:00"},
    ]
    monkeypatch.setattr(helpers, "db", SimpleNamespace(user_progress=Collection(rows)))
    metrics = await helpers.calculate_user_metrics("u")
    assert metrics["completion_pct"] == 100
    assert metrics["estimated_completion"] == "2026-01-02"
    monkeypatch.setattr(helpers, "_get_step_context", AsyncMock(return_value=([], {}, set(), set())))
    assert (await helpers.calculate_user_metrics("u"))["estimated_completion"] is None
    monkeypatch.setattr(helpers, "_get_step_context", AsyncMock(return_value=([step1, step2], {}, {"1"}, set())))
    monkeypatch.setattr(helpers, "db", SimpleNamespace(user_progress=Collection([])))
    metrics = await helpers.calculate_user_metrics("u")
    assert metrics["completion_pct"] == 0 and metrics["estimated_completion"]


def test_loaded_metrics_delegates(monkeypatch) -> None:
    result = SimpleNamespace(as_dict=lambda: {"completion_pct": 10})
    monkeypatch.setattr(helpers, "runtime_context_from_documents", lambda steps, progress: (steps, progress))
    monkeypatch.setattr(helpers, "runtime_calculate_metrics", lambda *_args: result)
    assert helpers.calculate_metrics_from_loaded_context([], []) == {"completion_pct": 10}


@pytest.mark.anyio
async def test_bulk_metrics_empty_invalid_and_survey_users(monkeypatch) -> None:
    assert await helpers.calculate_users_metrics([]) == {}
    uid = str(ObjectId())
    users = Collection([{"_id": ObjectId(uid), "survey_id": "survey"}])
    steps = Collection([{"_id": "s", "survey_id": "survey"}, {"_id": "global"}])
    progress = Collection([{"user_id": uid, "step_id": "s"}])
    monkeypatch.setattr(helpers, "db", SimpleNamespace(users=users, steps=steps, user_progress=progress))
    monkeypatch.setattr(helpers, "_metrics_from_loaded_context", lambda s, p: {"completion_pct": len(s) + len(p)})
    result = await helpers.calculate_users_metrics([uid, uid, "invalid", ""])
    assert result[uid]["completion_pct"] == 2
    assert result["invalid"] == {"completion_pct": 0, "estimated_completion": None}
    users.rows = []
    assert (await helpers.calculate_users_metrics(["invalid"])) ["invalid"]["completion_pct"] == 0


@pytest.mark.anyio
async def test_estimated_completion_start_dates_visibility_and_durations(monkeypatch) -> None:
    assert_value = AsyncMock(return_value=([], {}, set(), set()))
    monkeypatch.setattr(helpers, "_get_step_context", assert_value)
    monkeypatch.setattr(helpers, "db", SimpleNamespace(user_progress=Collection([]), users=Collection([])))
    assert await helpers.calculate_estimated_completion(str(ObjectId())) is None

    steps = [
        {"_id": "done", "duration_value": 1},
        {"_id": "hidden", "duration_value": 9, "step_type": "form"},
        {"_id": "milestone", "duration_value": 2, "duration_unit": "days", "step_type": "milestone"},
        {"_id": "zero", "duration_value": 0},
        {"_id": "older", "duration_value": 0},
    ]
    rows = [{"step_id": "done", "status": "completed", "completed_at": "2026-01-01T00:00:00Z"}]
    monkeypatch.setattr(helpers, "_get_step_context", AsyncMock(return_value=(steps, {}, {"hidden", "milestone"}, set())))
    monkeypatch.setattr(helpers, "db", SimpleNamespace(user_progress=Collection(rows), users=Collection([])))
    assert (await helpers.calculate_estimated_completion(str(ObjectId()))).startswith("2026-01-03")

    rows.append({"step_id": "older", "status": "completed", "completed_at": "2025-12-01T00:00:00Z"})
    assert await helpers.calculate_estimated_completion(str(ObjectId()))

    rows[0]["completed_at"] = "invalid"
    users = Collection([{"created_at": "invalid"}]); users.find_one.return_value = {"created_at": "invalid"}
    monkeypatch.setattr(helpers, "db", SimpleNamespace(user_progress=Collection(rows), users=users))
    assert await helpers.calculate_estimated_completion(str(ObjectId()))
    monkeypatch.setattr(helpers, "db", SimpleNamespace(user_progress=Collection([]), users=users))
    users.find_one.return_value = {"created_at": "invalid"}
    assert await helpers.calculate_estimated_completion(str(ObjectId()))
    users.find_one.return_value = {"created_at": "2026-02-01T00:00:00Z"}
    assert (await helpers.calculate_estimated_completion(str(ObjectId()))).startswith("2026-02-04")
    users.find_one.return_value = None
    assert await helpers.calculate_estimated_completion(str(ObjectId()))
