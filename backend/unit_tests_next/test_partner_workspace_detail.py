import asyncio

import pytest

from slices.partner_workspace.detail_service import PartnerWorkspaceDetailService
from slices.partner_workspace.models import (
    PartnerWorkspace, WorkspaceProgress, WorkspaceStep, WorkspaceUser,
)
from slices.partner_workspace.read_service import PartnerNotLinked


def run(value): return asyncio.run(value)


class Workspace:
    async def load(self, user_id, partner_id, partner_name):
        assert (user_id, partner_id, partner_name) == ("user", "partner", "Partner")
        return PartnerWorkspace(
            WorkspaceUser("user", "Doctor", "doctor@example.test", "survey", {}),
            (
                WorkspaceStep("choice", 1, "Choice", "partner_selection", "medical", "", {"title": "Choice"}),
                WorkspaceStep("milestone", 2, "Milestone", "milestone", "", "", {"title": "Milestone"}),
            ),
            (WorkspaceProgress("choice", "completed", 1, {"selected_partner_id": "partner"},
                               {"step_id": "choice", "data": {"selected_partner_id": "partner"}}),),
            ("choice", "milestone"),
        )


class Repository:
    async def partner(self, _partner_id):
        return {"name": "Partner", "tags": ["medical"]}


def service():
    async def revisions(_user_id): return [
        {"step_id": "choice", "revision": 1, "changed_by_partner_id": "", "data": {}},
        {"step_id": "hidden", "revision": 1, "changed_by_partner_id": "", "data": {}},
    ]
    async def completion(_user_id): return 42
    async def email(_actor, _partner, value): return f"visible:{value}"
    return PartnerWorkspaceDetailService(Workspace(), Repository(), revisions, completion, email)


def test_detail_requires_linked_partner():
    with pytest.raises(PartnerNotLinked): run(service().detail({}, "user"))


def test_detail_builds_sanitized_revision_aware_workspace():
    result = run(service().detail({"partner_id": "partner"}, "user"))
    assert result["id"] == "user"
    assert result["email"] == "visible:doctor@example.test"
    assert result["completion_pct"] == 42
    assert result["partner_step_id"] == "choice"
    assert result["partner_managed_step_ids"] == ["choice", "milestone"]
    assert [row["step_id"] for row in result["revisions"]] == ["choice"]
    assert result["steps"][0]["id"] == "choice"
    assert result["progress"][0]["configuration_changed"] is None
