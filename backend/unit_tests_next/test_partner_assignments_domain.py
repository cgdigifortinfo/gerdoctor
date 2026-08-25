"""Exhaustive tests for partner assignment and milestone rules."""
from slices.partner_assignments.domain import is_selected_partner, managed_step_ids, partner_work_status
from slices.partner_assignments.mappers import flow_step_from_document, progress_from_document
from slices.partner_assignments.models import FlowStep, PartnerWorkStatus, StepKind, StepProgress


def step(step_id, order, kind):
    return FlowStep(step_id, order, kind)


def test_mappers_normalize_step_and_single_multi_legacy_selections():
    assert flow_step_from_document({"_id": 1, "order": 0, "step_type": "unknown"}) == FlowStep("1", 0, StepKind.OTHER)
    assert flow_step_from_document({"id": "s", "order": 2, "step_type": "milestone"}) == FlowStep("s", 2, StepKind.MILESTONE)
    progress = progress_from_document({
        "step_id": "s", "status": "completed", "completed_at": "2026-01-01",
        "data": {"selected_partner_id": 1, "selected_partner_ids": [2, "3"], "selected_partner_name": "Legacy"},
    })
    assert progress == StepProgress(
        "s", "completed", frozenset({"1", "2", "3"}), "Legacy", "2026-01-01",
    )
    assert progress_from_document({}).status == "pending"
    assert flow_step_from_document({}) == FlowStep("", 0, StepKind.OTHER)
    assert progress_from_document({}).step_id == ""
    assert progress_from_document({}).selected_partner_name == ""


def test_partner_matching_requires_id_or_nonempty_exact_legacy_name():
    progress = StepProgress("s", selected_partner_ids=frozenset({"p1"}), selected_partner_name="Legacy")
    assert is_selected_partner(progress, "p1", "")
    assert is_selected_partner(progress, "other", "Legacy")
    assert not is_selected_partner(progress, "other", "")
    assert not is_selected_partner(progress, "other", "legacy")
    assert not is_selected_partner(None, "p1", "Legacy")


def test_managed_steps_include_each_assignment_and_stop_at_decisions():
    steps = (
        step("choice-1", 1, StepKind.PARTNER_SELECTION),
        step("milestone-1", 2, StepKind.MILESTONE),
        step("choice-2", 3, StepKind.PARTNER_MULTI_SELECTION),
        step("decision", 4, StepKind.DECISION),
        step("milestone-hidden", 5, StepKind.MILESTONE),
        step("choice-3", 6, StepKind.PARTNER_SELECTION),
        step("milestone-3", 7, StepKind.MILESTONE),
    )
    progress = (
        StepProgress("choice-1", selected_partner_ids=frozenset({"p1"})),
        StepProgress("choice-2", selected_partner_name="Partner"),
        StepProgress("choice-3", selected_partner_ids=frozenset({"p1"})),
    )
    assert managed_step_ids(steps, progress, "p1", "Partner") == (
        "choice-1", "milestone-1", "choice-2", "choice-3", "milestone-3",
    )
    assert managed_step_ids(steps, (), "p1", "Partner") == ()
    trailing_choice = step("trailing", 9, StepKind.PARTNER_SELECTION)
    trailing_progress = StepProgress("trailing", selected_partner_ids=frozenset({"p1"}))
    assert managed_step_ids((trailing_choice,), (trailing_progress,), "p1", "") == ("trailing",)
    assert managed_step_ids(
        (trailing_choice, step("plain", 10, StepKind.OTHER)),
        (trailing_progress,), "p1", "",
    ) == ("trailing",)


def test_managed_steps_skip_unselected_choices_and_same_order_milestones():
    steps = (
        step("unselected", 1, StepKind.PARTNER_SELECTION),
        step("selected", 2, StepKind.PARTNER_SELECTION),
        step("same-order", 2, StepKind.MILESTONE),
        step("following", 3, StepKind.MILESTONE),
    )
    progress = (StepProgress("selected", selected_partner_ids=frozenset({"p"})),)
    assert managed_step_ids(steps, progress, "p", "") == ("selected", "following")


def test_work_status_aggregates_all_assignments_and_latest_completion():
    steps = (
        step("choice-1", 1, StepKind.PARTNER_SELECTION),
        step("milestone-1", 2, StepKind.MILESTONE),
        step("choice-2", 3, StepKind.PARTNER_SELECTION),
        step("other", 4, StepKind.OTHER),
        step("milestone-2", 5, StepKind.MILESTONE),
    )
    selections = (
        StepProgress("choice-1", selected_partner_ids=frozenset({"p"})),
        StepProgress("choice-2", selected_partner_ids=frozenset({"p"})),
    )
    incomplete = partner_work_status(
        steps, (*selections, StepProgress("milestone-1", "completed", completed_at="2026-01-01")), "p", "",
    )
    assert incomplete == PartnerWorkStatus(False, "2026-01-01", "milestone-2")
    completed = partner_work_status(steps, (
        *selections,
        StepProgress("milestone-1", "completed", completed_at="2026-01-02"),
        StepProgress("milestone-2", "completed", completed_at="2026-01-03"),
    ), "p", "")
    assert completed.to_dict() == {
        "completed": True, "completed_at": "2026-01-03", "milestone_step_id": "milestone-2",
    }


def test_work_status_without_milestone_or_beyond_decision_is_empty():
    selection = step("choice", 1, StepKind.PARTNER_SELECTION)
    progress = (StepProgress("choice", selected_partner_ids=frozenset({"p"})),)
    assert partner_work_status((selection,), progress, "p", "") == PartnerWorkStatus()
    assert partner_work_status((selection, step("d", 2, StepKind.DECISION), step("m", 3, StepKind.MILESTONE)), progress, "p", "") == PartnerWorkStatus()
    assert partner_work_status((selection,), (), "p", "") == PartnerWorkStatus()


def test_work_status_skips_other_assignments_and_supports_legacy_name():
    steps = (
        step("unselected", 1, StepKind.PARTNER_SELECTION),
        step("selected", 2, StepKind.PARTNER_SELECTION),
        step("milestone", 3, StepKind.MILESTONE),
    )
    progress = (
        StepProgress("selected", selected_partner_name="Legacy Partner"),
        StepProgress("milestone", "pending"),
    )
    assert partner_work_status(steps, progress, "missing-id", "Legacy Partner") == PartnerWorkStatus(
        completed=False,
        completed_at=None,
        milestone_step_id="milestone",
    )
