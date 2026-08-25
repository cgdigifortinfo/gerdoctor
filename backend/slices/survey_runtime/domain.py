"""Pure rules for survey visibility, progress and journey metrics."""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any, Mapping

from slices.survey_runtime.models import (
    OrderState, RuntimeMetrics, RuntimeStep, RuntimeVisibility, SurveyRuntimeContext,
)


def add_duration(start: datetime, value: int, unit: str) -> datetime:
    if unit == "days":
        return start + timedelta(days=value)
    if unit == "weeks":
        return start + timedelta(weeks=value)
    if unit in ("months", "years"):
        month_index = start.month - 1 + (value if unit == "months" else value * 12)
        year, month_offset = divmod(month_index, 12)
        target_year = start.year + year
        target_month = month_offset + 1
        target_day = min(start.day, calendar.monthrange(target_year, target_month)[1])
        return start.replace(year=target_year, month=target_month, day=target_day)
    return start


def is_progress_gate_condition(condition: Mapping[str, Any]) -> bool:
    if isinstance(condition.get("all_of"), list):
        return all(is_progress_gate_condition(item) for item in condition["all_of"])
    if isinstance(condition.get("any_of"), list):
        return all(is_progress_gate_condition(item) for item in condition["any_of"])
    return condition.get("operator") in ("status_is", "status_not") and not condition.get("field")


def evaluate_condition(condition: Mapping[str, Any], order_state: OrderState) -> bool:
    if isinstance(condition.get("all_of"), list):
        return all(evaluate_condition(item, order_state) for item in condition["all_of"])
    if isinstance(condition.get("any_of"), list):
        return any(evaluate_condition(item, order_state) for item in condition["any_of"])
    source_order = condition.get("source_step_order")
    if not isinstance(source_order, (int, float)):
        return False
    source = order_state.get(float(source_order))
    if not source:
        return False
    field = condition.get("field")
    data = source.get("data") or {}
    field_value = data.get(field) if field else source.get("status")
    expected = condition.get("value")
    operator = str(condition.get("operator", "equals"))
    if operator == "equals":
        return str(field_value) == str(expected)
    if operator == "not_equals":
        return str(field_value) != str(expected)
    if operator in ("one_of", "not_one_of"):
        expected_values = expected if isinstance(expected, list) else [expected]
        normalized = {str(item) for item in expected_values if item is not None}
        matches = (
            any(str(item) in normalized for item in field_value)
            if isinstance(field_value, list) else str(field_value) in normalized
        )
        return matches if operator == "one_of" else not matches
    if operator == "contains":
        return str(expected) in str(field_value or "")
    if operator == "not_empty":
        return bool(field_value)
    if operator == "empty":
        return not bool(field_value)
    if operator == "status_is":
        return source.get("status") == expected
    if operator == "status_not":
        return source.get("status") != expected
    if operator in ("has_upload", "missing_upload"):
        uploads = data.get(field) or []
        if not isinstance(uploads, list):
            return operator == "missing_upload"
        found = any(
            isinstance(upload, dict)
            and upload.get("file_id")
            and (expected in (None, "") or upload.get("document_type") == expected)
            for upload in uploads
        )
        return found if operator == "has_upload" else not found
    return False


def order_state(context: SurveyRuntimeContext) -> dict[float, Mapping[str, Any]]:
    progress = {row.step_id: row for row in context.progress}
    return {
        step.order: {
            "data": progress[step.id].data if step.id in progress else {},
            "status": progress[step.id].status if step.id in progress else "pending",
        }
        for step in context.steps
    }


def visibility(context: SurveyRuntimeContext) -> RuntimeVisibility:
    state = order_state(context)
    hidden: set[str] = set()
    blocked: set[str] = set()
    for step in context.steps:
        for condition in step.conditions:
            action = condition.get("action")
            if action in ("hide", "block") and evaluate_condition(condition, state):
                (hidden if action == "hide" else blocked).add(step.id)
    return RuntimeVisibility(frozenset(hidden), frozenset(blocked))


def completion_steps(
    steps: tuple[RuntimeStep, ...], hidden_step_ids: frozenset[str],
) -> tuple[RuntimeStep, ...]:
    result: list[RuntimeStep] = []
    for step in steps:
        if step.id not in hidden_step_ids:
            result.append(step)
            continue
        hide_rules = tuple(rule for rule in step.conditions if rule.get("action") == "hide")
        if hide_rules and all(is_progress_gate_condition(rule) for rule in hide_rules):
            result.append(step)
    return tuple(result)


def auto_complete_step_ids(context: SurveyRuntimeContext) -> tuple[str, ...]:
    state = order_state(context)
    hidden = visibility(context).hidden_step_ids
    statuses = {row.step_id: row.status for row in context.progress}
    return tuple(
        step.id for step in context.steps
        if step.id not in hidden
        and statuses.get(step.id) != "completed"
        and any(
            rule.get("action") == "auto_complete" and evaluate_condition(rule, state)
            for rule in step.conditions
        )
    )


def calculate_metrics(context: SurveyRuntimeContext, now: datetime) -> RuntimeMetrics:
    hidden = visibility(context).hidden_step_ids
    progress = {row.step_id: row for row in context.progress}
    denominator = completion_steps(context.steps, hidden)
    completed = sum(1 for step in denominator if progress.get(step.id) and progress[step.id].status == "completed")
    percentage = round(completed / len(denominator) * 100) if denominator else 0
    if not context.steps:
        return RuntimeMetrics(percentage, None)
    timestamps: list[datetime] = []
    for step in context.steps:
        row = progress.get(step.id)
        if step.id in hidden or row is None or row.status != "completed" or not row.completed_at:
            continue
        try:
            timestamps.append(datetime.fromisoformat(row.completed_at))
        except (ValueError, AttributeError):
            continue
    current = max(timestamps) if timestamps else now
    for step in context.steps:
        if step.id not in hidden and (step.id not in progress or progress[step.id].status != "completed"):
            current = add_duration(current, step.duration_value, step.duration_unit)
    return RuntimeMetrics(percentage, current.date().isoformat())
