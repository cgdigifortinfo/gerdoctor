"""Pure validation and planning rules for partner selection."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from slices.partner_selection.models import (
    PartnerSelectionPlan,
    SelectablePartner,
    SelectionKind,
    SelectionStep,
    SelectionUser,
)


class PartnerSelectionError(ValueError):
    pass


class InvalidSelectionStep(PartnerSelectionError):
    pass


class SelectionSurveyMismatch(PartnerSelectionError):
    pass


class MultipleSelectionRequired(PartnerSelectionError):
    pass


class EmptyPartnerSelection(PartnerSelectionError):
    pass


class PartnerUnavailable(PartnerSelectionError):
    pass


class PartnerNotOffered(PartnerSelectionError):
    pass


def validate_selection_step(
    user: SelectionUser, requested_step_id: str | None, step: SelectionStep | None,
) -> SelectionStep | None:
    if requested_step_id is None:
        return None
    if step is None or step.id != requested_step_id:
        raise InvalidSelectionStep(requested_step_id)
    if user.survey_id and step.survey_id != user.survey_id:
        raise SelectionSurveyMismatch(requested_step_id)
    return step


def build_selection_plan(
    *,
    user: SelectionUser,
    requested_step_id: str | None,
    step: SelectionStep | None,
    requested_partner_ids: Iterable[str],
    partners: Iterable[SelectablePartner],
    data: Mapping[str, Any] | None,
    multiple: bool,
) -> PartnerSelectionPlan:
    validated_step = validate_selection_step(user, requested_step_id, step)
    if multiple and validated_step and validated_step.kind is not SelectionKind.MULTIPLE:
        raise MultipleSelectionRequired(validated_step.id)
    partner_ids = tuple(dict.fromkeys(str(partner_id) for partner_id in requested_partner_ids if partner_id))
    if not partner_ids:
        raise EmptyPartnerSelection
    partner_by_id = {partner.id: partner for partner in partners}
    selected = []
    for partner_id in partner_ids:
        partner = partner_by_id.get(partner_id)
        if partner is None or not partner.active:
            raise PartnerUnavailable(partner_id)
        if validated_step and validated_step.filter_tag and validated_step.filter_tag not in partner.tags:
            raise PartnerNotOffered(partner_id)
        selected.append(partner)
    selection_data = {key: value for key, value in (data or {}).items() if key != "_step_id"}
    if validated_step:
        if multiple:
            selection_data.update({
                "selected_partner_ids": [partner.id for partner in selected],
                "selected_partner_names": ", ".join(partner.name for partner in selected),
            })
        else:
            partner = selected[0]
            selection_data.update({"selected_partner_id": partner.id, "selected_partner_name": partner.name})
    return PartnerSelectionPlan(validated_step, tuple(selected), selection_data)


def sorted_partner_documents(partners: Iterable[SelectablePartner]) -> tuple[Mapping[str, Any], ...]:
    return tuple(partner.document for partner in sorted(partners, key=lambda row: (row.name.casefold(), row.id)))
