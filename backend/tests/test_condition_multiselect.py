"""Regression coverage for multi-value survey-step conditions."""

try:
    from backend.helpers import _evaluate_condition
except ModuleNotFoundError:  # container test runs use /app/backend as cwd
    from helpers import _evaluate_condition


def _condition(operator, expected):
    return {
        "source_step_order": 4,
        "field": "decision",
        "operator": operator,
        "value": expected,
    }


def test_one_of_matches_scalar_field_against_selected_values():
    order_map = {4: {"status": "completed", "data": {"decision": "partner"}}}

    assert _evaluate_condition(_condition("one_of", ["upload", "partner"]), order_map)
    assert not _evaluate_condition(_condition("one_of", ["upload", "selbst"]), order_map)


def test_not_one_of_is_inverse_for_scalar_field():
    order_map = {4: {"status": "completed", "data": {"decision": "selbst"}}}

    assert _evaluate_condition(_condition("not_one_of", ["upload", "partner"]), order_map)
    assert not _evaluate_condition(_condition("not_one_of", ["partner", "selbst"]), order_map)


def test_multi_value_condition_supports_array_source_fields():
    order_map = {4: {"status": "completed", "data": {"regions": ["Berlin", "Hamburg"]}}}
    condition = {
        "source_step_order": 4,
        "field": "regions",
        "operator": "one_of",
        "value": ["Bayern", "Hamburg"],
    }

    assert _evaluate_condition(condition, order_map)
    condition["operator"] = "not_one_of"
    assert not _evaluate_condition(condition, order_map)


def test_legacy_scalar_expected_value_remains_supported():
    order_map = {4: {"status": "completed", "data": {"decision": "partner"}}}

    assert _evaluate_condition(_condition("one_of", "partner"), order_map)
