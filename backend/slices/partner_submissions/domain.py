"""Pure resolution of per-service partner submission completion."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from slices.partner_submissions.models import (
    PartnerSubmission,
    SubmissionContext,
    SubmissionProgress,
    SubmissionStep,
    SubmissionStepKind,
    SubmissionWorkStatus,
)


def submission_work_status(
    submission: PartnerSubmission,
    steps: Iterable[SubmissionStep],
    progress_by_step: Mapping[str, SubmissionProgress],
) -> SubmissionWorkStatus:
    ordered_steps = tuple(steps)
    service_index = next(
        (index for index, step in enumerate(ordered_steps) if step.id == submission.service_step_id),
        None,
    )
    service_step = ordered_steps[service_index] if service_index is not None else None
    milestone = None  # pragma: no mutate - any falsy sentinel is behaviorally identical here
    if service_index is not None:
        for candidate in ordered_steps[service_index + 1:]:
            if candidate.kind is SubmissionStepKind.DECISION:
                break
            if candidate.kind is SubmissionStepKind.MILESTONE:
                milestone = candidate
                break
    milestone_progress = progress_by_step.get(milestone.id) if milestone else None
    return SubmissionWorkStatus(
        completed=bool(milestone_progress and milestone_progress.status == "completed"),
        completed_at=milestone_progress.completed_at if milestone_progress else None,
        milestone_step_id=milestone.id if milestone else None,
        service_step_id=submission.service_step_id,
        service_step_title=service_step.title if service_step else "",
        milestone_step_title=milestone.title if milestone else "",
    )


def submission_work_statuses(
    submissions: Iterable[PartnerSubmission],
    context: SubmissionContext,
) -> dict[tuple[str, str], SubmissionWorkStatus]:
    result: dict[tuple[str, str], SubmissionWorkStatus] = {}
    for submission in submissions:
        if not submission.user_id or not submission.service_step_id:
            continue
        survey_id = context.survey_by_user.get(submission.user_id)
        survey_steps = context.steps_by_survey.get(survey_id, ()) if survey_id else ()
        user_progress = context.progress_by_user.get(submission.user_id) or {}
        result[(submission.user_id, submission.service_step_id)] = submission_work_status(
            submission,
            survey_steps,
            user_progress,
        )
    return result
