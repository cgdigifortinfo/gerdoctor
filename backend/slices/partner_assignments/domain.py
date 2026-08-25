"""Pure partner assignment and milestone completion rules."""
from __future__ import annotations

from collections.abc import Iterable

from slices.partner_assignments.models import (
    FlowStep, PartnerWorkStatus, StepKind, StepProgress,
)


PARTNER_SELECTION_KINDS = {
    StepKind.PARTNER_SELECTION,
    StepKind.PARTNER_MULTI_SELECTION,
}


def is_selected_partner(
    progress: StepProgress | None,
    partner_id: str,
    partner_name: str,
) -> bool:
    if progress is None:
        return False
    return (
        str(partner_id) in progress.selected_partner_ids
        or bool(partner_name) and progress.selected_partner_name == partner_name
    )


def managed_step_ids(
    steps: Iterable[FlowStep],
    progress: Iterable[StepProgress],
    partner_id: str,
    partner_name: str,
) -> tuple[str, ...]:
    """Return each selected service step and its following milestone once."""
    steps = tuple(steps)
    progress_by_step = {row.step_id: row for row in progress}
    managed: list[str] = []
    for selection in steps:
        if selection.kind not in PARTNER_SELECTION_KINDS:
            continue
        if not is_selected_partner(progress_by_step.get(selection.id), partner_id, partner_name):
            continue
        managed.append(selection.id)
        for following in steps:
            if following.order <= selection.order:
                continue
            if following.kind is StepKind.MILESTONE:
                managed.append(following.id)
                break
            if following.kind is StepKind.DECISION:
                break
    return tuple(dict.fromkeys(managed))


def partner_work_status(
    steps: Iterable[FlowStep],
    progress: Iterable[StepProgress],
    partner_id: str,
    partner_name: str,
) -> PartnerWorkStatus:
    """Aggregate completion over every milestone assigned to this partner."""
    steps = tuple(steps)
    progress_by_step = {row.step_id: row for row in progress}
    milestone_ids: list[str] = []
    for index, selection in enumerate(steps):
        if selection.kind not in PARTNER_SELECTION_KINDS:
            continue
        if not is_selected_partner(progress_by_step.get(selection.id), partner_id, partner_name):
            continue
        for following in steps[index + 1:]:
            if following.kind is StepKind.DECISION:
                break
            if following.kind is StepKind.MILESTONE:
                milestone_ids.append(following.id)
                break
    if not milestone_ids:
        return PartnerWorkStatus()
    completion_dates: list[str] = []
    for milestone_id in milestone_ids:
        milestone_progress = progress_by_step.get(milestone_id)
        if milestone_progress and milestone_progress.completed_at:
            completion_dates.append(milestone_progress.completed_at)
    completed_at = max(completion_dates, default=None)
    return PartnerWorkStatus(
        completed=all(
            progress_by_step.get(mid) is not None
            and progress_by_step[mid].status == "completed"
            for mid in milestone_ids
        ),
        completed_at=completed_at,
        milestone_step_id=milestone_ids[-1],
    )
