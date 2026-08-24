"""Regression tests for role/group consistency during user impersonation."""

import os
from uuid import uuid4

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient


BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"


@pytest.fixture()
def admin_case():
    session = requests.Session()
    login = session.post(
        f"{API}/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
        timeout=20,
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    groups = session.get(f"{API}/admin/permission-groups", timeout=20).json()
    group_by_role = {group["role"]: group["id"] for group in groups if group["is_system"]}
    survey = next(
        item for item in session.get(f"{API}/admin/surveys", timeout=20).json()
        if item["slug"] == "aerzte"
    )
    mongo = MongoClient(os.environ["MONGO_URL"])
    db = mongo[os.environ["DB_NAME"]]
    user_ids = []
    partner_ids = []
    yield session, db, group_by_role, survey, user_ids, partner_ids
    for user_id in user_ids:
        session.delete(f"{API}/admin/users/{user_id}", timeout=20)
    for partner_id in partner_ids:
        session.delete(f"{API}/admin/partners/{partner_id}", timeout=20)
    mongo.close()


def _create_user(case):
    session, _, _, survey, user_ids, _ = case
    response = session.post(
        f"{API}/admin/users",
        json={
            "email": f"empty-progress-impersonation-{uuid4().hex[:10]}@test.de",
            "password": "Test123!",
            "name": "Empty Progress Impersonation",
            "role": "user",
            "survey_id": survey["id"],
        },
        timeout=20,
    )
    response.raise_for_status()
    user_ids.append(response.json()["id"])
    return response.json()["id"]


def _create_partner(case):
    session, _, _, survey, _, partner_ids = case
    response = session.post(
        f"{API}/admin/partners",
        json={
            "name": f"Role Group Partner {uuid4().hex[:8]}",
            "description": "Temporary role/group regression partner",
            "survey_ids": [survey["id"]],
        },
        timeout=20,
    )
    response.raise_for_status()
    partner_ids.append(response.json()["id"])
    return response.json()["id"]


def test_impersonation_repairs_foreign_group_for_user_with_empty_progress(admin_case):
    session, db, groups, _, _, _ = admin_case
    user_id = _create_user(admin_case)
    db.user_progress.delete_many({"user_id": user_id})
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": "user", "group_ids": [groups["partner"]]}},
    )

    response = session.post(f"{API}/admin/impersonate/{user_id}", timeout=20)
    response.raise_for_status()
    target = response.json()["user"]
    assert target["role"] == "user"
    assert target["group_ids"] == [groups["user"]]
    assert "portal.user.access" in target["permissions"]
    assert db.user_progress.count_documents({"user_id": user_id}) == 0
    assert db.users.find_one({"_id": ObjectId(user_id)})["group_ids"] == [groups["user"]]


def test_link_and_unlink_switch_role_and_system_group_together(admin_case):
    session, db, groups, _, _, _ = admin_case
    user_id = _create_user(admin_case)
    partner_id = _create_partner(admin_case)

    linked = session.put(
        f"{API}/admin/partners/{partner_id}/link-user",
        params={"user_id": user_id},
        timeout=20,
    )
    linked.raise_for_status()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    assert user["role"] == "partner"
    assert user["group_ids"] == [groups["partner"]]

    session.put(f"{API}/admin/partners/{partner_id}/unlink-user", timeout=20).raise_for_status()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    assert user["role"] == "user"
    assert user["group_ids"] == [groups["user"]]
    assert "partner_id" not in user


def test_deleting_partner_restores_linked_dashboard_user_group(admin_case):
    session, db, groups, _, _, partner_ids = admin_case
    user_id = _create_user(admin_case)
    partner_id = _create_partner(admin_case)
    session.put(
        f"{API}/admin/partners/{partner_id}/link-user",
        params={"user_id": user_id},
        timeout=20,
    ).raise_for_status()

    session.delete(f"{API}/admin/partners/{partner_id}", timeout=20).raise_for_status()
    partner_ids.remove(partner_id)
    user = db.users.find_one({"_id": ObjectId(user_id)})
    assert user["role"] == "user"
    assert user["group_ids"] == [groups["user"]]
    assert "partner_id" not in user
