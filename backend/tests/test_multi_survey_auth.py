import os
import time
import uuid
import asyncio

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv


load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"
RUN = f"multi-survey-{int(time.time())}-{uuid.uuid4().hex[:6]}"


def _login(email, password):
    session = requests.Session()
    response = session.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    assert response.status_code == 200, response.text
    session.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
    return session, response.json()


@pytest.fixture(scope="module", autouse=True)
def cleanup_registered_users():
    yield

    async def _cleanup():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        users = await db.users.find({"email": {"$regex": f"^{RUN}-"}}, {"_id": 1}).to_list(50)
        ids = [str(user["_id"]) for user in users]
        if ids:
            await db.user_progress.delete_many({"user_id": {"$in": ids}})
            await db.partner_submissions.delete_many({"user_id": {"$in": ids}})
            await db.progress_history.delete_many({"user_id": {"$in": ids}})
        await db.users.delete_many({"email": {"$regex": f"^{RUN}-"}})
        client.close()

    asyncio.run(_cleanup())


def test_admin_seed_credentials_work():
    _, admin = _login("admin@example.com", "Admin123!")
    assert admin["role"] == "admin"


def test_public_pflege_survey_exists():
    response = requests.get(f"{API}/surveys/slug/pflege", timeout=15)
    assert response.status_code == 200, response.text
    survey = response.json()
    assert survey["slug"] == "pflege"
    assert survey["name"] == "FSP Pflege"


def test_register_with_survey_slug_assigns_user_to_pflege():
    email = f"{RUN}-pflege@chrizz1001.de"
    session = requests.Session()
    response = session.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": "Test123!",
            "name": "Pflege Test",
            "survey_slug": "pflege",
        },
        timeout=15,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["survey_slug"] == "pflege"
    assert payload["survey_id"]

    session.headers.update({"Authorization": f"Bearer {payload['access_token']}"})
    me = session.get(f"{API}/auth/me", timeout=15)
    assert me.status_code == 200, me.text
    assert me.json()["survey_slug"] == "pflege"


def test_admin_steps_are_filterable_by_survey():
    session, _ = _login("admin@example.com", "Admin123!")
    surveys_response = session.get(f"{API}/admin/surveys", timeout=15)
    assert surveys_response.status_code == 200, surveys_response.text
    surveys = {survey["slug"]: survey for survey in surveys_response.json()}
    assert {"aerzte", "pflege"}.issubset(surveys)

    aerzte_steps = session.get(
        f"{API}/admin/steps?survey_id={surveys['aerzte']['id']}",
        timeout=15,
    )
    assert aerzte_steps.status_code == 200, aerzte_steps.text
    assert len(aerzte_steps.json()) > 0

    pflege_steps = session.get(
        f"{API}/admin/steps?survey_id={surveys['pflege']['id']}",
        timeout=15,
    )
    assert pflege_steps.status_code == 200, pflege_steps.text
    assert all(step.get("survey_id") == surveys["pflege"]["id"] for step in pflege_steps.json())
