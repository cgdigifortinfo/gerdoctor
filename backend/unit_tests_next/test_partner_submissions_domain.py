"""Exhaustive tests for per-service partner submission completion."""
from slices.partner_submissions.domain import submission_work_status, submission_work_statuses
from slices.partner_submissions.mappers import (
    submission_from_document,
    submission_progress_from_document,
    submission_step_from_document,
)
from slices.partner_submissions.models import (
    PartnerSubmission,
    SubmissionContext,
    SubmissionProgress,
    SubmissionStep,
    SubmissionStepKind,
    SubmissionWorkStatus,
)


def step(step_id: str, order: float, kind: SubmissionStepKind, title: str = "") -> SubmissionStep:
    return SubmissionStep(step_id, order, title, kind)


def test_mappers_normalize_documents_and_defaults():
    assert submission_from_document({"user_id": 1, "step_id": 2}) == PartnerSubmission("1", "2")
    assert submission_from_document({}) == PartnerSubmission("", "")
    assert submission_step_from_document({"_id": 1, "title": "M", "step_type": "milestone"}) == step(
        "1", 0, SubmissionStepKind.MILESTONE, "M",
    )
    assert submission_step_from_document({"id": "d", "order": 2, "step_type": "decision"}).kind is SubmissionStepKind.DECISION
    assert submission_step_from_document({}).kind is SubmissionStepKind.OTHER
    assert submission_step_from_document({}) == step("", 0, SubmissionStepKind.OTHER, "")
    assert submission_step_from_document({
        "id": "public", "_id": "mongo", "order": 4.5, "title": "Title", "step_type": "other",
    }) == step("public", 4.5, SubmissionStepKind.OTHER, "Title")
    assert submission_progress_from_document({}) == SubmissionProgress("")
    assert submission_progress_from_document({
        "step_id": "m", "status": "completed", "completed_at": "now",
    }) == SubmissionProgress("m", "completed", "now")


def test_status_resolves_next_milestone_and_completion():
    steps = (
        step("service", 1, SubmissionStepKind.OTHER, "Sprachprüfung"),
        step("plain", 2, SubmissionStepKind.OTHER),
        step("milestone", 3, SubmissionStepKind.MILESTONE, "Dokumente"),
    )
    status = submission_work_status(
        PartnerSubmission("u", "service"), steps,
        {"milestone": SubmissionProgress("milestone", "completed", "2026-01-01")},
    )
    assert status == SubmissionWorkStatus(
        True, "2026-01-01", "milestone", "service", "Sprachprüfung", "Dokumente",
    )
    assert status.to_dict()["completed"] is True


def test_status_is_incomplete_without_progress_or_when_decision_stops_flow():
    service = step("service", 1, SubmissionStepKind.OTHER, "Service")
    milestone = step("milestone", 3, SubmissionStepKind.MILESTONE, "Milestone")
    pending = submission_work_status(
        PartnerSubmission("u", "service"), (service, milestone),
        {"milestone": SubmissionProgress("milestone", "pending")},
    )
    assert pending == SubmissionWorkStatus(False, None, "milestone", "service", "Service", "Milestone")
    stopped = submission_work_status(
        PartnerSubmission("u", "service"),
        (service, step("decision", 2, SubmissionStepKind.DECISION), milestone),
        {},
    )
    assert stopped == SubmissionWorkStatus(False, None, None, "service", "Service", "")


def test_status_handles_unknown_service_and_multiple_submission_keys():
    context = SubmissionContext(
        survey_by_user={"u": "survey"},
        steps_by_survey={"survey": (step("service", 1, SubmissionStepKind.OTHER),)},
        progress_by_user={},
    )
    statuses = submission_work_statuses((
        PartnerSubmission("", "service"),
        PartnerSubmission("u", ""),
        PartnerSubmission("u", "service"),
        PartnerSubmission("u", "unknown"),
    ), context)
    assert set(statuses) == {("u", "service"), ("u", "unknown")}
    assert statuses[("u", "unknown")].service_step_title == ""
    assert statuses[("u", "unknown")].milestone_step_id is None


def test_status_handles_user_without_survey_context():
    statuses = submission_work_statuses((
        PartnerSubmission("missing", "service"),
        PartnerSubmission("stale", "service"),
    ), SubmissionContext({"stale": "deleted-survey"}, {}, {}))
    assert statuses[("missing", "service")].completed is False
    assert statuses[("stale", "service")].completed is False


def test_bulk_status_uses_each_users_survey_steps_and_progress():
    milestone = step("milestone", 2, SubmissionStepKind.MILESTONE, "Done")
    context = SubmissionContext(
        survey_by_user={"u": "survey", "other": "other-survey"},
        steps_by_survey={
            "survey": (step("service", 1, SubmissionStepKind.OTHER, "Selected"), milestone),
            "other-survey": (step("different", 1, SubmissionStepKind.OTHER),),
        },
        progress_by_user={
            "u": {"milestone": SubmissionProgress("milestone", "completed", "now")},
        },
    )
    status = submission_work_statuses((PartnerSubmission("u", "service"),), context)[("u", "service")]
    assert status == SubmissionWorkStatus(True, "now", "milestone", "service", "Selected", "Done")
