from bson import ObjectId

from recalculate_step_flow_layouts import calculate_positions


def test_merge_step_is_after_parallel_decision_branches():
    steps = [
        {"_id": ObjectId(), "order": 1, "step_type": "decision", "conditions": []},
        {"_id": ObjectId(), "order": 2, "conditions": [{"action": "hide", "source_step_order": 1, "field": "decision", "operator": "not_equals", "value": "upload"}]},
        {"_id": ObjectId(), "order": 3, "conditions": [{"action": "hide", "source_step_order": 1, "field": "decision", "operator": "not_equals", "value": "partner"}]},
        {"_id": ObjectId(), "order": 4, "step_type": "milestone", "conditions": [{"action": "hide", "source_step_order": 1, "field": "decision", "operator": "empty", "value": ""}]},
    ]
    positions = calculate_positions(steps)
    decision, upload, service, documents = [positions[str(step["_id"])] for step in steps]
    assert upload["x"] == service["x"]
    assert upload["y"] != service["y"]
    assert documents["x"] > upload["x"] > decision["x"]
    assert documents["y"] == decision["y"] == 140
