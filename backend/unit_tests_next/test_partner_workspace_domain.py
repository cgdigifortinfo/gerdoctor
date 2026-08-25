from __future__ import annotations

import pytest

from slices.partner_workspace.domain import (
    InvalidWorkspaceAction,
    RejectionReasonRequired,
    adjacent_visible_step,
    merge_progress_data,
    new_partner_uploads,
    partner_selection_step_id,
    revision_is_visible,
    sanitize_progress,
    validate_workspace_action,
)
from slices.partner_workspace.models import (
    WorkspaceAction,
    WorkspaceProgress,
    WorkspaceRevision,
    WorkspaceStep,
)


def step(step_id: str, order: float, kind: str = "content", tag: str = "") -> WorkspaceStep:
    return WorkspaceStep(step_id, order, step_id, kind, tag, "", {"title": step_id})


def progress(step_id: str, data: object = None, revision: int | None = 1) -> WorkspaceProgress:
    mapped = data if isinstance(data, dict) else {}
    return WorkspaceProgress(step_id, "pending", revision, mapped, {"step_id": step_id, "revision": revision, "data": mapped})


def test_action_validation_and_data_merge() -> None:
    assert validate_workspace_action("complete", None) is WorkspaceAction.COMPLETE
    assert validate_workspace_action("reject", " reason ") is WorkspaceAction.REJECT
    assert merge_progress_data({"old": 1, "same": 1}, {"new": 2, "same": 3}) == {"old": 1, "new": 2, "same": 3}
    assert merge_progress_data({"old": 1}, None) == {"old": 1}
    with pytest.raises(InvalidWorkspaceAction) as invalid:
        validate_workspace_action("skip", None)
    assert invalid.value.args == ("skip",)
    with pytest.raises(RejectionReasonRequired):
        validate_workspace_action("reject", "  ")
    with pytest.raises(RejectionReasonRequired):
        validate_workspace_action("reject", None)


def test_only_new_well_formed_partner_uploads_are_returned() -> None:
    old = {"partner_uploads": [{"file_id": "old"}, "bad"]}
    merged = {"partner_uploads": [
        {"file_id": "old"}, {"file_id": "new", "filename": "new.pdf"}, {}, "bad",
    ]}
    uploads = new_partner_uploads(old, merged)
    assert [(row.file_id, row.filename) for row in uploads] == [("new", "new.pdf")]
    assert uploads[0].document == {"file_id": "new", "filename": "new.pdf"}
    assert new_partner_uploads({}, {"partner_uploads": [{"file_id": "without-name"}]})[0].filename == ""
    assert new_partner_uploads({}, {"partner_uploads": "bad"}) == ()
    assert new_partner_uploads({"partner_uploads": "bad"}, {}) == ()


def test_adjacent_visible_step_respects_direction_order_and_hidden_steps() -> None:
    steps = (step("far-late", 6), step("late", 4), step("before", 1), step("current", 3), step("hidden", 2), step("far-before", 0))
    current = steps[3]
    assert adjacent_visible_step(steps, current, {"hidden"}, forward=False).id == "before"  # type: ignore[union-attr]
    assert adjacent_visible_step(steps, current, (), forward=True).id == "late"  # type: ignore[union-attr]
    assert adjacent_visible_step((current,), current, (), forward=True) is None
    assert adjacent_visible_step((current,), current, (), forward=False) is None


def test_partner_selection_step_uses_supported_kind_and_matching_tag() -> None:
    steps = (
        step("wrong-kind", 1, "content", "medical"),
        step("wrong-tag", 2, "partner_selection", "language"),
        step("right", 3, "partner_multiselection", "medical"),
    )
    assert partner_selection_step_id(steps, {"medical"}) == "right"
    assert partner_selection_step_id((step("single", 1, "partner_selection", "medical"),), {"medical"}) == "single"
    assert partner_selection_step_id(steps, {"missing"}) is None


@pytest.mark.parametrize(
    ("revision", "managed", "partner_id", "partner_name", "expected"),
    [
        (WorkspaceRevision("s", 1, "", {}), ("s",), "p", "Partner", True),
        (WorkspaceRevision("s", 1, "p", {}), (), "p", "Partner", True),
        (WorkspaceRevision("s", 1, "", {"nested": [{"id": "p"}]}), (), "p", "Partner", True),
        (WorkspaceRevision("s", 1, "", {"partners": ("Partner",)}), (), "p", "Partner", True),
        (WorkspaceRevision("s", 1, "", {"text": "prefix-p-suffix"}), (), "p", "Partner", False),
        (WorkspaceRevision("s", 1, "", {}), (), "p", "", False),
    ],
)
def test_revision_visibility(
    revision: WorkspaceRevision, managed: tuple[str, ...], partner_id: str, partner_name: str, expected: bool,
) -> None:
    assert revision_is_visible(revision, managed, partner_id, partner_name) is expected


def test_progress_for_another_partner_is_sanitized_and_marked() -> None:
    rows = (
        progress("selection", {"selected_partner_id": "other", "secret": True}),
        progress("own", {"answer": 1}, revision=None),
    )
    steps = (step("selection", 1, "partner_selection"), step("own", 2))
    markers = {
        ("selection", 1): {"configuration_changed": True, "current_step_version": 2, "step_snapshot": {"title": "Old"}},
        ("own", None): {"removed_field_names": ["legacy"]},
    }
    result = sanitize_progress(rows, steps, "mine", markers)
    assert result[0]["data"] == {}
    assert result[0]["configuration_changed"] is True
    assert result[0]["current_step_version"] == 2
    assert result[0]["step_snapshot"] == {"title": "Old"}
    assert result[1]["data"] == {"answer": 1}
    assert result[1]["removed_field_names"] == ["legacy"]
    assert result[1]["step_deleted"] is None


def test_own_empty_selection_and_non_selection_data_are_not_sanitized() -> None:
    rows = (
        progress("mine", {"selected_partner_id": "mine"}),
        progress("empty", {}),
        progress("content", {"selected_partner_id": "other"}),
    )
    steps = (step("mine", 1, "partner_selection"), step("empty", 2, "partner_selection"), step("content", 3))
    result = sanitize_progress(rows, steps, "mine", {})
    assert [row["data"] for row in result] == [
        {"selected_partner_id": "mine"}, {}, {"selected_partner_id": "other"},
    ]
    multi = sanitize_progress(
        (progress("multi", {"selected_partner_id": "other"}),),
        (step("multi", 1, "partner_multiselection"),), "mine", {},
    )
    assert multi[0]["data"] == {}
