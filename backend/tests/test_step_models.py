"""Contract tests for nested survey-step models."""

import math

import pytest
from pydantic import ValidationError

from models import StepCondition, StepCreate, StepLayoutBulk


def test_compound_condition_preserves_nested_rules_and_extensions():
    condition = StepCondition.model_validate({
        "action": "block",
        "all_of": [
            {"source_step_order": 2, "field": "decision", "operator": "equals", "value": "upload"},
            {"source_step_order": 3, "field": "documents", "operator": "missing_upload", "value": ""},
        ],
        "message": "Upload required",
        "future_option": True,
    })

    payload = condition.model_dump(exclude_none=True)
    assert payload["all_of"][1]["operator"] == "missing_upload"
    assert payload["future_option"] is True


def test_condition_rejects_ambiguous_and_or_group():
    with pytest.raises(ValidationError, match="both all_of and any_of"):
        StepCondition.model_validate({"all_of": [], "any_of": []})


def test_step_create_validates_field_mapping_contract():
    with pytest.raises(ValidationError):
        StepCreate.model_validate({
            "title": "Target",
            "description": "",
            "order": 2,
            "step_type": "form",
            "field_mappings": [{"source_step_order": 1, "source_field": "name"}],
        })


@pytest.mark.parametrize("coordinate", [math.inf, math.nan])
def test_layout_rejects_non_finite_coordinates(coordinate):
    with pytest.raises(ValidationError):
        StepLayoutBulk.model_validate({"positions": {"step-id": {"x": coordinate, "y": 1}}})
