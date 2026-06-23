import os
import uuid

import requests
from dotenv import load_dotenv


load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"


def _admin_session():
    session = requests.Session()
    response = session.post(
        f"{API}/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
        timeout=15,
    )
    assert response.status_code == 200, response.text
    session.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
    return session


def test_admin_created_user_is_scoped_to_selected_survey():
    admin = _admin_session()
    surveys = admin.get(f"{API}/admin/surveys", timeout=15).json()
    pflege = next(survey for survey in surveys if survey["slug"] == "pflege")
    pflege_steps = admin.get(
        f"{API}/admin/steps?survey_id={pflege['id']}", timeout=15
    ).json()
    email = f"admin-survey-{uuid.uuid4().hex[:10]}@test.de"
    user_id = None

    try:
        created = admin.post(
            f"{API}/admin/users",
            json={
                "email": email,
                "password": "Test123!",
                "name": "Admin Survey Test",
                "role": "user",
                "survey_id": pflege["id"],
            },
            timeout=15,
        )
        assert created.status_code == 200, created.text
        body = created.json()
        user_id = body["id"]
        assert body["survey_id"] == pflege["id"]
        assert body["survey_slug"] == "pflege"

        detail = admin.get(f"{API}/admin/users/{user_id}", timeout=15)
        assert detail.status_code == 200, detail.text
        user = detail.json()
        assert user["survey_id"] == pflege["id"]
        assert user["survey_slug"] == "pflege"
        assert len(user["progress"]) == len(pflege_steps)
        assert {row["step_id"] for row in user["progress"]} == {step["id"] for step in pflege_steps}
        assert all(row["survey_id"] == pflege["id"] for row in user["progress"])
        assert all(row["status"] == "pending" for row in user["progress"])

        login = requests.post(
            f"{API}/auth/login",
            json={"email": email, "password": "Test123!"},
            timeout=15,
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        visible_steps = requests.get(
            f"{API}/steps",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert visible_steps.status_code == 200, visible_steps.text
        assert {step["id"] for step in visible_steps.json()} == {step["id"] for step in pflege_steps}
    finally:
        if user_id:
            admin.delete(f"{API}/admin/users/{user_id}", timeout=15)


def test_admin_create_user_rejects_unknown_survey():
    admin = _admin_session()
    email = f"admin-invalid-survey-{uuid.uuid4().hex[:10]}@test.de"
    response = admin.post(
        f"{API}/admin/users",
        json={
            "email": email,
            "password": "Test123!",
            "name": "Invalid Survey",
            "role": "user",
            "survey_id": "000000000000000000000000",
        },
        timeout=15,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or inactive survey"
