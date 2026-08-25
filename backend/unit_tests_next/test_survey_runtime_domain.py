from __future__ import annotations

from datetime import datetime, timezone

import pytest

from slices.survey_runtime.domain import (
    add_duration, auto_complete_step_ids, calculate_metrics, completion_steps,
    evaluate_condition, is_progress_gate_condition, order_state, visibility,
)
from slices.survey_runtime.mappers import runtime_context_from_documents
from slices.survey_runtime.models import RuntimeMetrics


NOW = datetime(2024, 1, 31, tzinfo=timezone.utc)
STATE = {
    1.0: {"status": "completed", "data": {"choice": ["a", "b"], "text": "hello", "empty": ""}},
    2.0: {"status": "pending", "data": {"uploads": [{"document_type": "cv", "file_id": "f"}]}},
}


@pytest.mark.parametrize(("rule", "expected"), [
    ({"source_step_order": 1, "field": "choice", "operator": "one_of", "value": "b"}, True),
    ({"source_step_order": 1, "field": "choice", "operator": "not_one_of", "value": ["x"]}, True),
    ({"source_step_order": 1, "field": "text", "operator": "equals", "value": "hello"}, True),
    ({"source_step_order": 1, "field": "text", "operator": "not_equals", "value": "bye"}, True),
    ({"source_step_order": 1, "field": "text", "operator": "contains", "value": "ell"}, True),
    ({"source_step_order": 1, "field": "text", "operator": "not_empty"}, True),
    ({"source_step_order": 1, "field": "empty", "operator": "empty"}, True),
    ({"source_step_order": 1, "operator": "status_is", "value": "completed"}, True),
    ({"source_step_order": 1, "operator": "status_not", "value": "pending"}, True),
    ({"source_step_order": 2, "field": "uploads", "operator": "has_upload"}, True),
    ({"source_step_order": 2, "field": "uploads", "operator": "has_upload", "value": "cv"}, True),
    ({"source_step_order": 2, "field": "uploads", "operator": "missing_upload", "value": "license"}, True),
    ({"source_step_order": "bad", "operator": "equals"}, False),
    ({"source_step_order": 9, "operator": "equals"}, False),
    ({"source_step_order": 1, "operator": "unknown"}, False),
])
def test_condition_leaf_truth_table(rule: dict[str, object], expected: bool) -> None:
    assert evaluate_condition(rule, STATE) is expected


def test_compound_conditions_and_non_list_uploads() -> None:
    yes = {"source_step_order": 1, "operator": "status_is", "value": "completed"}
    no = {"source_step_order": 1, "operator": "status_is", "value": "pending"}
    assert evaluate_condition({"all_of": [yes, yes]}, STATE)
    assert not evaluate_condition({"all_of": [yes, no]}, STATE)
    assert evaluate_condition({"any_of": [no, yes]}, STATE)
    invalid_uploads = {3.0: {"status": "pending", "data": {"uploads": "invalid"}}}
    assert not evaluate_condition({"source_step_order": 3, "field": "uploads", "operator": "has_upload"}, invalid_uploads)
    assert evaluate_condition({"source_step_order": 3, "field": "uploads", "operator": "missing_upload"}, invalid_uploads)


@pytest.mark.parametrize(("rule", "expected"), [
    ({"source_step_order": 1, "operator": "equals", "value": "completed"}, True),
    ({"source_step_order": 1, "field": "text", "operator": "not_equals", "value": "hello"}, False),
    ({"source_step_order": 1, "field": "text", "operator": "one_of", "value": ["hello"]}, True),
    ({"source_step_order": 1, "field": "text", "operator": "not_one_of", "value": ["hello"]}, False),
    ({"source_step_order": 1, "field": "missing", "operator": "contains", "value": "XXXX"}, False),
    ({"source_step_order": 1, "field": "empty", "operator": "not_empty"}, False),
    ({"source_step_order": 1, "field": "text", "operator": "empty"}, False),
    ({"source_step_order": 1, "operator": "status_not", "value": "completed"}, False),
    ({"source_step_order": 2, "field": "uploads", "operator": "has_upload", "value": ""}, True),
])
def test_condition_negative_and_fallback_cases(rule: dict[str, object], expected: bool) -> None:
    assert evaluate_condition(rule, STATE) is expected


def test_context_visibility_completion_and_auto_complete_are_consistent() -> None:
    context = runtime_context_from_documents([
        {"_id": "decision", "order": 1},
        {"_id": "branch", "order": 2, "conditions": [{"action": "hide", "source_step_order": 1, "field": "choice", "value": "self"}]},
        {"_id": "gate", "order": 3, "conditions": [{"action": "hide", "source_step_order": 1, "operator": "status_is", "value": "pending"}]},
        {"_id": "blocked", "order": 4, "conditions": [{"action": "block", "source_step_order": 1, "operator": "status_is", "value": "completed"}]},
        {"_id": "auto", "order": 5, "conditions": [{"action": "auto_complete", "source_step_order": 1, "operator": "status_is", "value": "completed"}]},
    ], [{"step_id": "decision", "status": "completed", "data": {"choice": "self"}}])
    assert order_state(context)[2.0] == {"data": {}, "status": "pending"}
    shown = visibility(context)
    assert shown.hidden_step_ids == frozenset({"branch"})
    assert shown.blocked_step_ids == frozenset({"blocked"})
    assert [step.id for step in completion_steps(context.steps, shown.hidden_step_ids)] == ["decision", "gate", "blocked", "auto"]
    assert auto_complete_step_ids(context) == ("auto",)
    completed_auto = runtime_context_from_documents(
        list(step.document for step in context.steps),
        [{"step_id": "decision", "status": "completed", "data": {"choice": "self"}},
         {"step_id": "auto", "status": "completed"}],
    )
    assert auto_complete_step_ids(completed_auto) == ()


def test_metrics_use_latest_valid_completion_and_skip_hidden_duration() -> None:
    context = runtime_context_from_documents([
        {"_id": "done", "order": 1, "duration_value": 99},
        {"_id": "next", "order": 2, "duration_value": 1, "duration_unit": "months"},
    ], [
        {"step_id": "done", "status": "completed", "completed_at": "2024-01-31T00:00:00+00:00"},
        {"step_id": "unknown", "status": "completed", "completed_at": "invalid"},
    ])
    assert calculate_metrics(context, NOW) == RuntimeMetrics(50, "2024-02-29")
    assert calculate_metrics(runtime_context_from_documents([], []), NOW).as_dict() == {
        "completion_pct": 0, "estimated_completion": None,
    }
    invalid = runtime_context_from_documents(
        [{"_id": "broken", "order": 1}],
        [{"step_id": "broken", "status": "completed", "completed_at": "invalid"}],
    )
    assert calculate_metrics(invalid, NOW).estimated_completion == "2024-01-31"


def test_metrics_distinguish_pending_missing_hidden_and_zulu_timestamps() -> None:
    context = runtime_context_from_documents([
        {"_id": "done", "order": 1},
        {"_id": "pending", "order": 2, "duration_value": 2},
        {"_id": "missing", "order": 3, "duration_value": 3},
        {"_id": "hidden", "order": 4, "duration_value": 100,
         "conditions": [{"action": "hide", "source_step_order": 1, "operator": "status_is", "value": "completed", "field": "x"}]},
    ], [
        {"step_id": "done", "status": "completed", "completed_at": "2024-02-01T00:00:00Z", "data": {"x": "ignored"}},
        {"step_id": "pending", "status": "pending", "completed_at": "2025-01-01T00:00:00Z"},
    ])
    metrics = calculate_metrics(context, NOW)
    assert metrics.completion_pct == 33
    assert metrics.estimated_completion == "2024-02-06"


def test_metrics_continue_after_skipped_and_invalid_rows() -> None:
    context = runtime_context_from_documents([
        {"_id": "missing", "order": 1},
        {"_id": "invalid", "order": 2},
        {"_id": "valid", "order": 3},
        {"_id": "remaining", "order": 4, "duration_value": 1},
    ], [
        {"step_id": "invalid", "status": "completed", "completed_at": "broken"},
        {"step_id": "valid", "status": "completed", "completed_at": "2024-03-10T00:00:00+00:00"},
    ])
    assert calculate_metrics(context, NOW).estimated_completion == "2024-03-11"


def test_mapper_normalizes_every_runtime_field_and_keeps_document() -> None:
    step_doc = {"_id": 7, "order": "2.5", "conditions": [{"action": "hide"}],
                "duration_value": "3", "duration_unit": "weeks", "step_type": "milestone"}
    progress_doc = {"step_id": 7, "status": "completed", "data": {"a": 1}, "completed_at": 123}
    context = runtime_context_from_documents([step_doc], [progress_doc])
    step, progress = context.steps[0], context.progress[0]
    assert (step.id, step.order, step.conditions, step.duration_value, step.duration_unit, step.step_type) == (
        "7", 2.5, ({"action": "hide"},), 3, "weeks", "milestone")
    assert step.document is step_doc
    assert (progress.step_id, progress.status, progress.data, progress.completed_at) == (
        "7", "completed", {"a": 1}, "123")
    defaults = runtime_context_from_documents([{}], [{}])
    assert (defaults.steps[0].id, defaults.steps[0].order, defaults.steps[0].conditions,
            defaults.steps[0].duration_value, defaults.steps[0].duration_unit,
            defaults.steps[0].step_type) == ("", 0.0, (), 0, "days", "")
    assert (defaults.progress[0].step_id, defaults.progress[0].status,
            defaults.progress[0].data, defaults.progress[0].completed_at) == ("", "pending", {}, None)


@pytest.mark.parametrize(("unit", "expected"), [
    ("days", "2024-02-01"), ("weeks", "2024-02-07"),
    ("months", "2024-02-29"), ("years", "2025-01-31"), ("bad", "2024-01-31"),
])
def test_duration_units(unit: str, expected: str) -> None:
    assert add_duration(NOW, 1, unit).date().isoformat() == expected


def test_progress_gate_recurses_through_both_group_kinds() -> None:
    leaf = {"operator": "status_is"}
    assert is_progress_gate_condition({"all_of": [leaf]})
    assert is_progress_gate_condition({"any_of": [leaf]})
    assert not is_progress_gate_condition({"operator": "equals", "field": "answer"})
    assert not is_progress_gate_condition({"operator": "status_is", "field": "answer"})
    assert not is_progress_gate_condition({"operator": "equals"})
