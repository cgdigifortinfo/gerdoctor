"""Pure business-rule tests for permissions, conditions, dates, and metrics."""

from datetime import datetime

import pytest

from helpers import (
    _completion_denominator_steps,
    _evaluate_condition,
    _is_progress_gate_condition,
    _replace_vars,
    add_duration,
    calculate_metrics_from_loaded_context,
)
from permissions import (
    normalize_permissions,
    partner_is_awaiting_assignment,
    permission_for_admin_request,
    permission_for_portal_request,
)


class TestPermissionRouting:
    @pytest.mark.parametrize("method,path,expected", [
        ("GET", "/api/admin/users", "users.view"),
        ("POST", "/api/admin/users", "users.create"),
        ("DELETE", "/api/admin/users/id", "users.delete"),
        ("GET", "/api/admin/steps", "steps.view"),
        ("PUT", "/api/admin/steps/id", "steps.manage"),
        ("GET", "/api/admin/settings", "settings.view"),
        ("PUT", "/api/admin/settings", "settings.manage"),
    ])
    def test_admin_use_cases_map_to_least_required_permission(self, method, path, expected):
        assert permission_for_admin_request(method, path) == expected

    @pytest.mark.parametrize("method,path,expected", [
        ("GET", "/api/steps", "survey.own.view"),
        ("PUT", "/api/steps/progress", "survey.own.submit"),
        ("GET", "/api/partner/submissions", "partner.users.view"),
        ("PUT", "/api/partner/profile", "profile.self.manage"),
        ("POST", "/api/partner/users/id/complete", "partner.users.manage"),
        ("GET", "/api/partners", None),
    ])
    def test_portal_use_cases_map_to_least_required_permission(self, method, path, expected):
        assert permission_for_portal_request(method, path) == expected

    def test_unrelated_paths_do_not_accidentally_receive_admin_rights(self):
        assert permission_for_admin_request("GET", "/api/administrator") is None
        assert permission_for_admin_request("GET", "/api/auth/login") is None

    def test_permission_normalization_deduplicates_and_rejects_unknowns(self):
        assert normalize_permissions(["users.view", "unknown", "users.view", "*"]) == ["users.view"]
        assert normalize_permissions(["*"], allow_wildcard=True) == ["*"]


class TestPartnerAssignmentAccess:
    @pytest.mark.parametrize("partner", [
        {"registration_source": "admin", "registration_status": "active", "is_active": True, "survey_ids": ["survey-a"]},
        {"registration_source": "self_service", "registration_status": "active", "is_active": True, "survey_ids": ["survey-a"]},
    ])
    def test_operational_access_is_not_blocked_for_non_pending_cases(self, partner):
        assert partner_is_awaiting_assignment(partner) is False

    @pytest.mark.parametrize("partner", [
        None,
        {"registration_source": "admin", "registration_status": "pending", "is_active": False, "survey_ids": []},
        {"registration_source": "self_service", "registration_status": "pending", "is_active": False, "survey_ids": []},
        {"registration_source": "self_service", "registration_status": "active", "is_active": True, "survey_ids": []},
        {"registration_source": "self_service", "registration_status": "pending", "is_active": True, "survey_ids": ["survey-a"]},
    ])
    def test_each_incomplete_activation_state_blocks_operational_access(self, partner):
        assert partner_is_awaiting_assignment(partner) is True


class TestConditionEvaluation:
    context = {
        1: {"status": "completed", "data": {"choice": ["a", "b"], "text": "hello world", "empty": ""}},
        2: {"status": "pending", "data": {"uploads": [{"document_type": "cv", "file_id": "file-1"}]}},
    }

    @pytest.mark.parametrize("condition,expected", [
        ({"source_step_order": 1, "field": "choice", "operator": "one_of", "value": ["b", "c"]}, True),
        ({"source_step_order": 1, "field": "choice", "operator": "not_one_of", "value": ["c"]}, True),
        ({"source_step_order": 1, "field": "text", "operator": "contains", "value": "world"}, True),
        ({"source_step_order": 1, "field": "empty", "operator": "empty"}, True),
        ({"source_step_order": 1, "operator": "status_is", "value": "completed"}, True),
        ({"source_step_order": 1, "operator": "status_not", "value": "pending"}, True),
        ({"source_step_order": 2, "field": "uploads", "operator": "has_upload", "value": "cv"}, True),
        ({"source_step_order": 2, "field": "uploads", "operator": "missing_upload", "value": "license"}, True),
        ({"source_step_order": 99, "operator": "status_is", "value": "completed"}, False),
        ({"source_step_order": 1, "operator": "unknown"}, False),
    ])
    def test_leaf_condition_truth_table(self, condition, expected):
        assert _evaluate_condition(condition, self.context) is expected

    def test_compound_all_and_any_truth_tables(self):
        true_rule = {"source_step_order": 1, "operator": "status_is", "value": "completed"}
        false_rule = {"source_step_order": 1, "operator": "status_is", "value": "pending"}
        assert _evaluate_condition({"all_of": [true_rule, true_rule]}, self.context) is True
        assert _evaluate_condition({"all_of": [true_rule, false_rule]}, self.context) is False
        assert _evaluate_condition({"any_of": [false_rule, true_rule]}, self.context) is True
        assert _evaluate_condition({"any_of": [false_rule, false_rule]}, self.context) is False

    def test_missing_data_field_does_not_leak_step_status(self):
        condition = {"source_step_order": 1, "field": "missing", "operator": "equals", "value": "completed"}
        assert _evaluate_condition(condition, self.context) is False


class TestCompletionRules:
    def test_progress_gate_detection_handles_compound_rules(self):
        gate = {"all_of": [
            {"operator": "status_is", "field": None},
            {"operator": "status_not", "field": None},
        ]}
        assert _is_progress_gate_condition(gate) is True
        assert _is_progress_gate_condition({"operator": "equals", "field": "choice"}) is False

    def test_hidden_data_branch_is_removed_but_hidden_progress_gate_stays_in_denominator(self):
        steps = [
            {"_id": "visible"},
            {"_id": "data-hidden", "conditions": [{"action": "hide", "operator": "equals", "field": "choice"}]},
            {"_id": "gate-hidden", "conditions": [{"action": "hide", "operator": "status_is"}]},
        ]
        result = _completion_denominator_steps(steps, {"data-hidden", "gate-hidden"})
        assert [step["_id"] for step in result] == ["visible", "gate-hidden"]

    def test_metrics_have_zero_safe_defaults(self):
        assert calculate_metrics_from_loaded_context([], []) == {
            "completion_pct": 0,
            "estimated_completion": None,
        }


class TestUtilityRules:
    def test_template_variables_replace_known_and_clear_unknown_tokens(self):
        assert _replace_vars("Hallo {{ name }} / {{missing}}", {"name": "Ada"}) == "Hallo Ada / "

    def test_none_template_is_safe(self):
        assert _replace_vars(None, {}) == ""

    @pytest.mark.parametrize("unit,expected", [
        ("days", datetime(2024, 2, 1)),
        ("weeks", datetime(2024, 2, 7)),
        ("months", datetime(2024, 2, 29)),
        ("years", datetime(2025, 1, 31)),
        ("unsupported", datetime(2024, 1, 31)),
    ])
    def test_add_duration_use_cases(self, unit, expected):
        assert add_duration(datetime(2024, 1, 31), 1, unit) == expected
