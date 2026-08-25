from slices.audit_trail.domain import audit_entry, audit_query, normalized_pagination


def test_entry_normalizes_boundary_values_and_copies_details():
    details = {"before_version": 1}
    entry = audit_entry(42, None, "step_update", "step", 7, details, "now")
    details["before_version"] = 2
    assert entry.to_document() == {
        "actor_id": "42", "actor_email": "None", "action": "step_update",
        "target_type": "step", "target_id": "7", "details": {"before_version": 1},
        "timestamp": "now",
    }
    assert audit_entry("a", "e", "x", "t", "", None, "now").details == {}


def test_query_builds_independent_optional_filters():
    assert audit_query() == {}
    assert audit_query(action="update") == {"action": "update"}
    assert audit_query(date_from="a") == {"timestamp": {"$gte": "a"}}
    assert audit_query(date_to="z") == {"timestamp": {"$lte": "z"}}
    assert audit_query("update", "a", "z") == {
        "action": "update", "timestamp": {"$gte": "a", "$lte": "z"},
    }


def test_pagination_preserves_limit_and_clamps_negative_skip():
    assert normalized_pagination(0, -5) == (0, 0)
    assert normalized_pagination(25, 3) == (25, 3)
