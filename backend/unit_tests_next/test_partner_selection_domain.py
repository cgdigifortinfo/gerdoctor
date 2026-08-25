from __future__ import annotations

import pytest

from slices.partner_selection.domain import (
    EmptyPartnerSelection,
    InvalidSelectionStep,
    MultipleSelectionRequired,
    PartnerNotOffered,
    PartnerUnavailable,
    SelectionSurveyMismatch,
    build_selection_plan,
    sorted_partner_documents,
    validate_selection_step,
)
from slices.partner_selection.models import SelectablePartner, SelectionKind, SelectionStep, SelectionUser


USER = SelectionUser("user", "survey")


def step(kind: SelectionKind = SelectionKind.SINGLE, tag: str = "medical", survey: str | None = "survey") -> SelectionStep:
    return SelectionStep("step", kind, survey, tag, {"id": "step"})


def partner(partner_id: str, name: str = "Partner", *, tags: tuple[str, ...] = ("medical",), active: bool = True) -> SelectablePartner:
    return SelectablePartner(partner_id, name, frozenset(tags), active, {"id": partner_id, "name": name})


def test_step_validation_supports_legacy_request_and_rejects_invalid_context() -> None:
    assert validate_selection_step(USER, None, None) is None
    selected_step = step()
    assert validate_selection_step(USER, "step", selected_step) is selected_step
    with pytest.raises(InvalidSelectionStep) as missing:
        validate_selection_step(USER, "missing", selected_step)
    assert missing.value.args == ("missing",)
    with pytest.raises(InvalidSelectionStep):
        validate_selection_step(USER, "step", None)
    with pytest.raises(SelectionSurveyMismatch) as mismatch:
        validate_selection_step(USER, "step", step(survey="other"))
    assert mismatch.value.args == ("step",)
    assert validate_selection_step(SelectionUser("legacy", None), "step", step(survey="other")).id == "step"


def test_single_selection_canonicalizes_data_and_partner_identity() -> None:
    selected = partner("p", "Ärzte Hilfe")
    plan = build_selection_plan(
        user=USER, requested_step_id="step", step=step(), requested_partner_ids=("p",),
        partners=(selected,), data={"_step_id": "step", "note": "keep", "selected_partner_name": "stale"}, multiple=False,
    )
    assert plan.step == step()
    assert plan.partners == (selected,)
    assert plan.partner_ids == ("p",)
    assert plan.selection_data == {"note": "keep", "selected_partner_id": "p", "selected_partner_name": "Ärzte Hilfe"}


def test_multi_selection_deduplicates_and_preserves_request_order() -> None:
    alpha, beta = partner("a", "Alpha"), partner("b", "Beta")
    plan = build_selection_plan(
        user=USER, requested_step_id="step", step=step(SelectionKind.MULTIPLE),
        requested_partner_ids=("b", "a", "b", ""), partners=(alpha, beta), data=None, multiple=True,
    )
    assert plan.partner_ids == ("b", "a")
    assert plan.selection_data == {"selected_partner_ids": ["b", "a"], "selected_partner_names": "Beta, Alpha"}


def test_legacy_selection_keeps_custom_data_without_writing_step_keys() -> None:
    plan = build_selection_plan(
        user=USER, requested_step_id=None, step=None, requested_partner_ids=("p",),
        partners=(partner("p"),), data={"_step_id": None, "answer": 1}, multiple=False,
    )
    assert plan.step is None
    assert plan.selection_data == {"answer": 1}


def test_selection_rejects_wrong_cardinality_availability_and_tag() -> None:
    with pytest.raises(MultipleSelectionRequired) as cardinality:
        build_selection_plan(user=USER, requested_step_id="step", step=step(), requested_partner_ids=("p",), partners=(partner("p"),), data={}, multiple=True)
    assert cardinality.value.args == ("step",)
    with pytest.raises(EmptyPartnerSelection):
        build_selection_plan(user=USER, requested_step_id=None, step=None, requested_partner_ids=("",), partners=(), data={}, multiple=False)
    with pytest.raises(PartnerUnavailable) as missing:
        build_selection_plan(user=USER, requested_step_id=None, step=None, requested_partner_ids=("missing",), partners=(), data={}, multiple=False)
    assert missing.value.args == ("missing",)
    with pytest.raises(PartnerUnavailable):
        build_selection_plan(user=USER, requested_step_id=None, step=None, requested_partner_ids=("p",), partners=(partner("p", active=False),), data={}, multiple=False)
    with pytest.raises(PartnerNotOffered) as wrong_tag:
        build_selection_plan(user=USER, requested_step_id="step", step=step(), requested_partner_ids=("p",), partners=(partner("p", tags=("language",)),), data={}, multiple=False)
    assert wrong_tag.value.args == ("p",)


def test_empty_step_tag_offers_all_active_partners() -> None:
    plan = build_selection_plan(
        user=USER, requested_step_id="step", step=step(tag=""), requested_partner_ids=("p",),
        partners=(partner("p", tags=()),), data={}, multiple=False,
    )
    assert plan.partner_ids == ("p",)


def test_partner_documents_are_sorted_case_insensitively_and_stably() -> None:
    rows = (partner("2", "beta"), partner("3", "Alpha"), partner("1", "alpha"))
    assert [row["id"] for row in sorted_partner_documents(rows)] == ["1", "3", "2"]
