import pytest
from slices.admin_user_management.domain import (
    ConflictingPermissionOverrides, InvalidPartnerAssignment, InvalidRole, PrimaryAdminProtected,
    archived_user_fields, ensure_primary_admin_change, initial_progress, new_user_document,
    permission_overrides, role_fields, search_query, validate_partner_assignment, validated_role,
)


def test_role_and_partner_rules():
    assert validated_role("user") == "user"
    with pytest.raises(InvalidRole): validated_role("guest")
    validate_partner_assignment("partner", "p")
    validate_partner_assignment("user", None)
    with pytest.raises(InvalidPartnerAssignment): validate_partner_assignment("user", "p")


def test_search_and_permission_rules_cover_optional_inputs():
    assert search_query("", "") == {}
    assert search_query("Ada", "all") == {"$or": [{"name": {"$regex": "Ada", "$options": "i"}}, {"email": {"$regex": "Ada", "$options": "i"}}]}
    assert search_query("", "partner") == {"role": "partner"}
    assert permission_overrides(["a"], ["b"]) == {"allow": ["a"], "deny": ["b"]}
    with pytest.raises(ConflictingPermissionOverrides): permission_overrides(["a"], ["a"])


def test_role_fields_and_primary_admin_protection():
    assert role_fields("partner", "g") == {"role": "partner", "group_ids": ["g"], "permission_overrides": {"allow": [], "deny": []}}
    assert role_fields("user", None)["group_ids"] == []
    ensure_primary_admin_change("other", "admin", None)
    ensure_primary_admin_change("admin", "admin", "admin")
    with pytest.raises(PrimaryAdminProtected): ensure_primary_admin_change("admin", "admin", "user")
    with pytest.raises(PrimaryAdminProtected): ensure_primary_admin_change("admin", "admin")


def test_new_user_progress_and_archive_documents_are_stable():
    survey = {"_id": 7}
    document = new_user_document(" ADA@EXAMPLE.COM ", "hash", "Ada", "user", ["g"], "now", survey)
    assert document == {"email": "ada@example.com", "password_hash": "hash", "name": "Ada",
                        "role": "user", "profile": {}, "created_at": "now",
                        "permission_overrides": {"allow": [], "deny": []}, "group_ids": ["g"],
                        "survey_id": "7", "survey_slug": "aerzte"}
    assert new_user_document("x@y.de", "h", "X", "user", [], "now", {"_id": 8, "slug": "custom"})["survey_slug"] == "custom"
    with pytest.raises(InvalidPartnerAssignment):
        new_user_document("x@y.de", "h", "X", "user", [], "now", partner_id="p")
    partner = new_user_document("p@x.de", "h", "P", "partner", [], "now", None, "pid")
    assert partner == {"email": "p@x.de", "password_hash": "h", "name": "P", "role": "partner",
                       "profile": {}, "created_at": "now", "permission_overrides": {"allow": [], "deny": []},
                       "group_ids": [], "partner_id": "pid"}
    progress = initial_progress("u", "s", ({"_id": 1, "order": 2}, {"_id": 2}), "now")
    assert progress == [
        {"user_id": "u", "step_id": "1", "survey_id": "s", "step_order": 2, "status": "pending",
         "data": {}, "created_at": "now", "updated_at": "now"},
        {"user_id": "u", "step_id": "2", "survey_id": "s", "step_order": None, "status": "pending",
         "data": {}, "created_at": "now", "updated_at": "now"},
    ]
    assert archived_user_fields("u", "x@y.de", None, "a", "now") == {
        "email": "deleted+u+x@y.de", "archived_original_email": "x@y.de", "is_deleted": True,
        "deleted_at": "now", "deleted_by": "a", "is_active": False,
    }
    assert archived_user_fields("u", "x@y.de", "old@y.de", "a", "now")["archived_original_email"] == "old@y.de"
