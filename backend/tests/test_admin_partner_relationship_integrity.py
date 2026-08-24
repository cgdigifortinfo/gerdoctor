"""Regression coverage for partner references exposed by the admin APIs."""

import os
from uuid import uuid4

import pytest
import requests


BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"


@pytest.fixture(scope="module")
def admin_context():
    session = requests.Session()
    login = session.post(
        f"{API}/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
        timeout=20,
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    surveys = session.get(f"{API}/admin/surveys", timeout=20).json()
    aerzte = next(survey for survey in surveys if survey["slug"] == "aerzte")
    steps = session.get(f"{API}/admin/steps?survey_slug=aerzte", timeout=20).json()
    partner_step = next(step for step in steps if step["step_type"] == "partner_selection")

    suffix = uuid4().hex[:8]
    partner_ids = []
    user_ids = []
    for name in (f"zulu integrity {suffix}", f"Alpha Integrity {suffix}"):
        created = session.post(
            f"{API}/admin/partners",
            json={"name": name, "description": "Temporary relationship test partner", "survey_ids": [aerzte["id"]]},
            timeout=20,
        )
        created.raise_for_status()
        partner_ids.append(created.json()["id"])

    yield {
        "session": session,
        "survey": aerzte,
        "partner_step": partner_step,
        "partner_ids": partner_ids,
        "partner_names": [f"zulu integrity {suffix}", f"Alpha Integrity {suffix}"],
        "user_ids": user_ids,
    }

    for user_id in user_ids:
        session.delete(f"{API}/admin/users/{user_id}", timeout=20)
    for partner_id in partner_ids:
        session.delete(f"{API}/admin/partners/{partner_id}", timeout=20)


def _create_user(ctx, role="user", partner_id=None):
    payload = {
        "email": f"partner-integrity-{uuid4().hex[:10]}@test.de",
        "password": "Test123!",
        "name": "Partner Integrity Test",
        "role": role,
    }
    if role == "user":
        payload["survey_id"] = ctx["survey"]["id"]
    if partner_id is not None:
        payload["partner_id"] = partner_id
    response = ctx["session"].post(f"{API}/admin/users", json=payload, timeout=20)
    if response.status_code == 200:
        ctx["user_ids"].append(response.json()["id"])
    return response


def _admin_user(ctx, user_id):
    users = ctx["session"].get(f"{API}/admin/users", timeout=20).json()
    return next(user for user in users if user["id"] == user_id)


def _set_partner_progress(ctx, user_id, data):
    response = ctx["session"].put(
        f"{API}/admin/users/{user_id}/progress",
        json={"step_id": ctx["partner_step"]["id"], "status": "completed", "data": data},
        timeout=20,
    )
    response.raise_for_status()


def test_admin_partner_list_is_alphabetical(admin_context):
    partners = admin_context["session"].get(f"{API}/admin/partners", timeout=20).json()
    names = [partner["name"] for partner in partners]
    assert names == sorted(names, key=str.casefold)


def test_name_only_legacy_reference_never_becomes_a_phantom_partner(admin_context):
    created = _create_user(admin_context)
    created.raise_for_status()
    user_id = created.json()["id"]

    _set_partner_progress(admin_context, user_id, {"selected_partner_name": "Demo Partner"})
    row = _admin_user(admin_context, user_id)
    assert row["partner_names"] == []
    assert {("legacy_name", "Demo Partner")} <= {
        (item["type"], item["value"]) for item in row["orphaned_partner_references"]
    }


def test_legacy_name_resolves_only_to_a_current_partner(admin_context):
    created = _create_user(admin_context)
    created.raise_for_status()
    user_id = created.json()["id"]
    canonical_name = admin_context["partner_names"][1]

    _set_partner_progress(admin_context, user_id, {"selected_partner_name": canonical_name.upper()})
    row = _admin_user(admin_context, user_id)
    assert row["partner_names"] == [canonical_name]
    assert row["orphaned_partner_references"] == []


def test_ids_are_authoritative_and_stale_ids_are_reported(admin_context):
    created = _create_user(admin_context)
    created.raise_for_status()
    user_id = created.json()["id"]
    valid_id = admin_context["partner_ids"][0]
    canonical_name = admin_context["partner_names"][0]

    _set_partner_progress(
        admin_context,
        user_id,
        {"selected_partner_id": valid_id, "selected_partner_name": "Misleading old label"},
    )
    row = _admin_user(admin_context, user_id)
    assert row["partner_names"] == [canonical_name]
    assert row["orphaned_partner_references"] == []

    stale_id = "507f1f77bcf86cd799439011"
    _set_partner_progress(
        admin_context,
        user_id,
        {"selected_partner_id": stale_id, "selected_partner_name": canonical_name},
    )
    row = _admin_user(admin_context, user_id)
    assert row["partner_names"] == []
    assert {("partner_id", stale_id)} <= {
        (item["type"], item["value"]) for item in row["orphaned_partner_references"]
    }


@pytest.mark.parametrize("partner_id", ["not-an-object-id", "507f1f77bcf86cd799439011"])
def test_partner_user_creation_rejects_invalid_or_unknown_partner(admin_context, partner_id):
    response = _create_user(admin_context, role="partner", partner_id=partner_id)
    assert response.status_code == 400
    assert "partner id" in response.json()["detail"].lower()


def test_only_partner_role_can_receive_partner_id(admin_context):
    response = _create_user(
        admin_context, role="user", partner_id=admin_context["partner_ids"][0]
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only partner users can be assigned to a partner"


def test_partner_user_creation_persists_a_valid_relationship(admin_context):
    partner_id = admin_context["partner_ids"][0]
    response = _create_user(admin_context, role="partner", partner_id=partner_id)
    response.raise_for_status()
    row = _admin_user(admin_context, response.json()["id"])
    assert row["partner_names"] == [admin_context["partner_names"][0]]
    assert row["orphaned_partner_references"] == []
