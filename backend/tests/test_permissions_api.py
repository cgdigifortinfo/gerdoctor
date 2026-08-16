"""Live API regression for permission-group CRUD and per-user overrides."""
import os
import uuid

import requests


BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"


def _login(email="admin@example.com", password="Admin123!"):
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert response.status_code == 200, response.text
    return response.json()


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_permission_group_crud_assignment_overrides_and_enforcement():
    primary = _login()
    admin_headers = _headers(primary["access_token"])
    suffix = uuid.uuid4().hex[:10]
    group_id = limited_admin_id = created_user_id = None
    limited_email = f"limited-rbac-{suffix}@test.de"
    try:
        catalog = requests.get(f"{API}/admin/permission-catalog", headers=admin_headers, timeout=15)
        assert catalog.status_code == 200, catalog.text
        keys = set(catalog.json()["all_permissions"])
        assert {"groups.create", "users.permissions.manage", "steps.manage"}.issubset(keys)
        surveys = requests.get(f"{API}/admin/surveys", headers=admin_headers, timeout=15).json()
        default_survey_id = next(survey["id"] for survey in surveys if survey.get("is_default"))

        created_group = requests.post(
            f"{API}/admin/permission-groups",
            headers=admin_headers,
            json={
                "name": f"E2E Eingeschränkte Admins {suffix}",
                "description": "Nur lesender Benutzerzugriff",
                "role": "admin",
                "permissions": ["admin.access", "users.view", "groups.view"],
            },
            timeout=15,
        )
        assert created_group.status_code == 200, created_group.text
        group_id = created_group.json()["id"]

        updated_group = requests.put(
            f"{API}/admin/permission-groups/{group_id}",
            headers=admin_headers,
            json={"description": "Lesen und Gruppen anzeigen"},
            timeout=15,
        )
        assert updated_group.status_code == 200, updated_group.text
        assert updated_group.json()["description"] == "Lesen und Gruppen anzeigen"

        invalid_permission = requests.post(
            f"{API}/admin/permission-groups",
            headers=admin_headers,
            json={"name": f"Invalid {suffix}", "role": "admin", "permissions": ["unknown.permission"]},
            timeout=15,
        )
        assert invalid_permission.status_code == 400
        assert "unknown.permission" in invalid_permission.json()["detail"]

        limited_admin = requests.post(
            f"{API}/admin/users",
            headers=admin_headers,
            json={
                "email": limited_email,
                "password": "Test123!",
                "name": "Limited RBAC Admin",
                "role": "admin",
                "group_ids": [group_id],
            },
            timeout=15,
        )
        assert limited_admin.status_code == 200, limited_admin.text
        limited_admin_id = limited_admin.json()["id"]
        assigned_delete = requests.delete(
            f"{API}/admin/permission-groups/{group_id}", headers=admin_headers, timeout=15
        )
        assert assigned_delete.status_code == 400
        assert assigned_delete.json()["detail"] == "Permission group is still assigned to users"
        limited_login = _login(limited_email, "Test123!")
        assert "users.view" in limited_login["permissions"]
        assert "users.create" not in limited_login["permissions"]
        limited_headers = _headers(limited_login["access_token"])

        assert requests.get(f"{API}/admin/users", headers=limited_headers, timeout=15).status_code == 200
        denied_create = requests.post(
            f"{API}/admin/users",
            headers=limited_headers,
            json={"email": f"blocked-{suffix}@test.de", "password": "Test123!", "name": "Blocked", "role": "admin"},
            timeout=15,
        )
        assert denied_create.status_code == 403
        assert denied_create.json()["detail"] == "Missing permission: users.create"

        override = requests.put(
            f"{API}/admin/users/{limited_admin_id}/permissions",
            headers=admin_headers,
            json={"group_ids": [group_id], "allow": ["users.create"], "deny": ["users.view"]},
            timeout=15,
        )
        assert override.status_code == 200, override.text
        assert "users.create" in override.json()["effective_permissions"]
        assert "users.view" not in override.json()["effective_permissions"]
        assert requests.get(f"{API}/admin/users", headers=limited_headers, timeout=15).status_code == 403

        created_user = requests.post(
            f"{API}/admin/users",
            headers=limited_headers,
            json={"email": f"created-by-limited-{suffix}@test.de", "password": "Test123!", "name": "Created by Limited", "role": "user", "survey_id": default_survey_id},
            timeout=15,
        )
        assert created_user.status_code == 200, created_user.text
        created_user_id = created_user.json()["id"]

        escalation = requests.post(
            f"{API}/admin/users",
            headers=limited_headers,
            json={"email": f"admin-by-limited-{suffix}@test.de", "password": "Test123!", "name": "Blocked Admin", "role": "admin"},
            timeout=15,
        )
        assert escalation.status_code == 403
        assert escalation.json()["detail"] == "Missing permission: users.permissions.manage"

        primary_override = requests.put(
            f"{API}/admin/users/{primary['id']}/permissions",
            headers=admin_headers,
            json={"group_ids": [], "allow": [], "deny": ["admin.access"]},
            timeout=15,
        )
        assert primary_override.status_code == 400
    finally:
        for user_id in (created_user_id, limited_admin_id):
            if user_id:
                requests.delete(f"{API}/admin/users/{user_id}", headers=admin_headers, timeout=15)
        if group_id:
            deleted = requests.delete(f"{API}/admin/permission-groups/{group_id}", headers=admin_headers, timeout=15)
            assert deleted.status_code == 200, deleted.text
