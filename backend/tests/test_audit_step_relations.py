from audit_step_relations import audit_steps


def test_audit_detects_invalid_requirement_condition_and_mapping():
    issues = audit_steps([
        {"order": 1, "title": "Quelle", "fields": [{"name": "choice", "field_type": "text"}]},
        {"order": 2, "title": "Ziel", "fields": [], "required_fields": ["missing"], "conditions": [
            {"action": "hide", "source_step_order": 1, "field": "unknown", "operator": "empty"},
        ], "field_mappings": [{"source_step_order": 1, "source_field": "choice", "target_field": "missing"}]},
    ])
    assert len(issues) == 3


def test_audit_accepts_partner_upload_system_field():
    assert audit_steps([
        {"order": 1, "title": "Dokumente", "step_type": "milestone", "fields": []},
        {"order": 2, "title": "Entscheidung", "fields": [], "conditions": [
            {"action": "read_only", "source_step_order": 1, "field": "partner_uploads", "operator": "has_upload", "value": ""},
        ]},
    ]) == []
