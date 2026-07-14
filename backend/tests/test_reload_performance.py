import os
import time

import pytest
import requests
from pymongo import MongoClient


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")


def login(email: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    return session


def timed_get(session: requests.Session, path: str, max_seconds: float):
    started = time.perf_counter()
    response = session.get(f"{BASE_URL}{path}", timeout=max_seconds + 5)
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    assert elapsed < max_seconds, f"{path} took {elapsed:.3f}s (limit {max_seconds}s)"
    return response.json()


def test_user_dashboard_bootstrap_is_complete_and_fast():
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    user = db.users.find_one({"role": "user", "email": {"$regex": "^demo001-"}})
    assert user
    session = login(user["email"], "Demo123!")
    payload = timed_get(session, "/api/steps/bootstrap", 1.0)
    assert payload["steps"]
    assert len(payload["progress"]) == len(payload["steps"])
    assert len(payload["all_step_data"]) == len(payload["steps"])
    assert "notification_preferences" in payload
    assert "settings" in payload
    client.close()


def test_admin_and_partner_reload_hotpaths_are_bounded():
    admin = login("admin@example.com", "Admin123!")
    users = timed_get(admin, "/api/admin/users", 3.0)
    partners = timed_get(admin, "/api/admin/partners", 3.0)
    assert len(users) >= 300
    assert partners

    partner = login("partner-fia-academy@chrizz1001.de", "Partner123!")
    submissions = timed_get(partner, "/api/partner/submissions", 3.0)
    others = timed_get(partner, "/api/partner/other-users", 3.0)
    assert submissions
    assert isinstance(others, list)


def test_reload_query_indexes_exist():
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    progress_indexes = {index["name"] for index in db.user_progress.list_indexes()}
    submission_indexes = {index["name"] for index in db.partner_submissions.list_indexes()}
    step_indexes = {index["name"] for index in db.steps.list_indexes()}
    user_indexes = {index["name"] for index in db.users.list_indexes()}
    file_indexes = {index["name"] for index in db.files.list_indexes()}
    assert "user_id_1_step_id_1" in progress_indexes
    assert "user_id_1_survey_id_1" in progress_indexes
    assert "user_id_1_step_order_1" in progress_indexes
    assert "partner_id_1_user_id_1" in submission_indexes
    assert "survey_id_1_is_active_1_order_1" in step_indexes
    assert "role_1_created_at_-1" in user_indexes
    assert "user_id_1_created_at_-1" in file_indexes
    client.close()
