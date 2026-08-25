import asyncio

import pytest

from slices.partner_workspace.action_service import (
    PartnerWorkspaceActionService, WorkspaceActionCommand,
    WorkspaceActionStepNotFound, WorkspaceActionStepNotManaged,
)
from slices.partner_workspace.domain import InvalidWorkspaceAction, RejectionReasonRequired
from slices.partner_workspace.read_service import PartnerNotLinked


def run(value): return asyncio.run(value)


class Repository:
    def __init__(self, partner=None, progress=None):
        self.partner_value = partner
        self.progress_values = progress or {}
        self.updates, self.histories = [], []

    async def partner(self, _partner_id): return self.partner_value
    async def progress(self, _user_id, step_id): return self.progress_values.get(step_id)
    async def update_progress(self, user_id, step_id, update, *, upsert=True):
        self.updates.append((user_id, step_id, update, upsert))
    async def history(self, document, *, tolerant=False):
        self.histories.append((dict(document), tolerant))


def make_service(*, partner=None, managed=None, progress=None, visibility=None,
                 target=None, steps=None):
    repository = Repository(partner, progress)
    steps = steps or [
        {"_id": "before", "id": "before", "order": 1, "title": "Before"},
        {"_id": "current", "id": "current", "order": 2, "title": "Current", "description": "Desc"},
        {"_id": "after", "id": "after", "order": 3, "title": "After"},
    ]
    progress_rows = list((progress or {}).values())
    target = target or {"name": "Doctor", "email": "doctor@example.test", "survey_id": "survey"}
    writes, events, charges, autos, audits = [], [], [], [], []

    async def context(*_args): return target, progress_rows, steps, managed if managed is not None else ["current"]
    async def write(**values): writes.append(values)
    async def emit(name, payload, actor):
        result = {"name": name, "payload": payload, "actor": actor}; events.append(result); return result
    async def charge(*args): charges.append(args)
    def service_step(*_args): return {"id": "service"}
    async def auto(user_id): autos.append(user_id)
    hidden_values = iter(visibility or [set(), set()])
    async def visible(_user_id): return steps, [], next(hidden_values), set()
    async def audit(*args): audits.append(args)
    subject = PartnerWorkspaceActionService(
        repository, context, write, emit, charge, service_step, auto, visible,
        audit, lambda: "now",
    )
    return subject, repository, writes, events, charges, autos, audits


def actor(**extra):
    return {"_id": "actor", "email": "partner@example.test", "name": "Actor",
            "partner_id": "partner", **extra}


def command(action="complete", reason=None, data=None):
    return WorkspaceActionCommand(action, reason, data)


def test_action_validates_partner_action_reason_membership_and_step():
    subject, *_ = make_service()
    with pytest.raises(PartnerNotLinked): run(subject.execute({}, "user", "current", command()))
    with pytest.raises(InvalidWorkspaceAction): run(subject.execute(actor(), "user", "current", command("x")))
    with pytest.raises(RejectionReasonRequired): run(subject.execute(actor(), "user", "current", command("reject")))
    with pytest.raises(WorkspaceActionStepNotManaged):
        run(make_service(managed=[])[0].execute(actor(), "user", "current", command()))
    with pytest.raises(WorkspaceActionStepNotFound):
        run(make_service(managed=["missing"])[0].execute(actor(), "user", "missing", command()))


def test_complete_merges_data_unlocks_next_and_records_history_and_audit():
    existing = {"step_id": "current", "data": {"old": 1}, "status": "pending"}
    subject, repository, writes, events, charges, autos, audits = make_service(progress={"current": existing})
    result = run(subject.execute(actor(), "user", "current", command(data={"new": 2})))
    assert result["status"] == "completed" and result["reopened_step"] is None
    assert writes[0]["data"] == {"old": 1, "new": 2}
    assert repository.updates[0][1] == "after"
    assert events[-1]["name"] == "partner.step.completed"
    assert charges == [] and autos == ["user"]
    assert repository.histories[0][0]["action"] == "completed_by_partner"
    assert audits[0][2] == "completed_by_partner"


def test_complete_records_new_upload_charge_and_repairs_rejected_previous_step():
    old = {"partner_uploads": [], "partner_rejection": {"reason": "old"}}
    new = {"partner_uploads": [{"file_id": "file", "filename": "doc.pdf"}]}
    progress = {
        "current": {"step_id": "current", "data": old},
        "before": {"step_id": "before", "status": "pending", "started_at": "started"},
        "after": {"step_id": "after", "status": "completed"},
    }
    partner = {"name": "Org"}
    subject, repository, writes, events, charges, *_ = make_service(
        partner=partner, progress=progress, visibility=[set(), set()],
    )
    result = run(subject.execute(actor(), "user", "current", command(data=new)))
    assert [event["name"] for event in events] == ["partner.document.uploaded", "partner.step.completed"]
    assert charges[0][0] == partner and charges[0][2]["file_id"] == "file"
    assert [update[1] for update in repository.updates] == ["before"]
    assert "partner_rejection" not in writes[0]["data"]
    assert result["message"] == "Step completed"


def test_complete_without_following_step_uses_actor_name_and_default_notifications():
    steps = [{"_id": "current", "id": "current", "order": 2, "title": "Current"}]
    target = {"name": "", "email": ""}
    subject, repository, writes, events, *_ = make_service(steps=steps, target=target)
    result = run(subject.execute(actor(name="Fallback"), "user", "current", command()))
    assert repository.updates == [] and writes[0]["status"] == "completed"
    assert events[0]["payload"]["user_email_notifications_enabled"] is True
    assert events[0]["payload"]["partner_name"] == "Fallback"
    assert result["events"] == events


def test_complete_emits_upload_without_charge_when_partner_record_is_missing():
    subject, _, _, events, charges, *_ = make_service()
    run(subject.execute(actor(), "user", "current", command(data={
        "partner_uploads": [{"file_id": "file", "filename": "doc.pdf"}],
    })))
    assert events[0]["name"] == "partner.document.uploaded"
    assert charges == []


def test_complete_rejected_first_step_has_no_previous_step_to_repair():
    steps = [{"_id": "current", "id": "current", "order": 1, "title": "Current"}]
    progress = {"current": {"step_id": "current", "data": {"partner_rejection": {"reason": "old"}}}}
    subject, repository, *_ = make_service(steps=steps, progress=progress, visibility=[set(), set()])
    run(subject.execute(actor(), "user", "current", command()))
    assert repository.updates == []


def test_reject_reopens_previous_visible_step_and_returns_reason_payload():
    subject, repository, writes, events, _, autos, audits = make_service(visibility=[set()])
    result = run(subject.execute(actor(), "user", "current", command("reject", "Please fix")))
    assert result["status"] == "pending" and result["reopened_step"]["id"] == "before"
    assert writes[0]["data"]["partner_rejection"]["reason"] == "Please fix"
    assert repository.updates[0][1] == "before"
    assert events[0]["payload"]["reopened_step_title"] == "Before"
    assert repository.histories[0][0]["action"] == "rejected_by_partner"
    assert autos == [] and audits[0][2] == "rejected_by_partner"


def test_reject_first_step_has_no_reopened_step_and_strips_reason():
    steps = [{"_id": "current", "id": "current", "order": 1, "title": "Current"}]
    subject, repository, _, events, *_ = make_service(steps=steps, visibility=[set()])
    result = run(subject.execute(actor(name=""), "user", "current", command("reject", "  reason  ")))
    assert result["message"] == "Step rejected" and result["reopened_step"] is None
    assert repository.updates == []
    assert events[0]["payload"]["rejection_reason"] == "reason"
    assert events[0]["payload"]["reopened_step_id"] == ""
