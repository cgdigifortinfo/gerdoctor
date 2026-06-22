import os

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


def _surveys(session):
    response = session.get(f"{API}/admin/surveys", timeout=15)
    assert response.status_code == 200, response.text
    return {survey["slug"]: survey for survey in response.json()}


def _pflege_steps(session):
    surveys = _surveys(session)
    assert "pflege" in surveys
    response = session.get(
        f"{API}/admin/steps?survey_id={surveys['pflege']['id']}",
        timeout=15,
    )
    assert response.status_code == 200, response.text
    return response.json(), surveys["pflege"]["id"]


def test_pflege_survey_has_expected_step_chain():
    session = _admin_session()
    steps, pflege_survey_id = _pflege_steps(session)
    by_order = {step["order"]: step for step in steps}

    assert len(steps) == 25
    assert set(by_order) == set(range(1, 26))
    assert all(step["survey_id"] == pflege_survey_id for step in steps)

    expected_titles = {
        1: "Registrierung",
        2: "Schnellstart oder Selbststart?",
        3: "Anerkennung Pflege",
        7: "Sprachschule",
        11: "Fachsprachenprüfung",
        15: "Vorbereitungskurs Kenntnisprüfung",
        19: "Kenntnisprüfung",
        23: "Jobangebote",
        24: "Partner Jobangebote Pflege",
        25: "Übersicht Jobangebote Pflege",
    }
    for order, title in expected_titles.items():
        assert by_order[order]["title"] == title

    serialized = str(steps)
    assert "Approbation" not in serialized
    assert "Gleichwertigkeitsprüfung" not in serialized
    assert "Gleichwertigkeitspruefung" not in serialized


def test_pflege_survey_reuses_decision_upload_partner_milestone_mechanics():
    session = _admin_session()
    steps, _ = _pflege_steps(session)
    by_order = {step["order"]: step for step in steps}

    assert by_order[1]["step_type"] == "form"
    assert by_order[2]["step_type"] == "decision"

    for decision_order, upload_order, partner_order, milestone_order, tag in [
        (3, 4, 5, 6, "Pflege Anerkennung"),
        (7, 8, 9, 10, "Pflege Sprachschule"),
        (11, 12, 13, 14, "Pflege Fachsprachenprüfung"),
        (15, 16, 17, 18, "Pflege Vorbereitungskurs Kenntnisprüfung"),
        (19, 20, 21, 22, "Pflege Kenntnisprüfung"),
    ]:
        assert by_order[decision_order]["step_type"] == "decision"
        assert by_order[upload_order]["step_type"] == "form"
        assert by_order[partner_order]["step_type"] == "partner_selection"
        assert by_order[partner_order]["filter_tag"] == tag
        assert by_order[milestone_order]["step_type"] == "milestone"

        upload_conditions = by_order[upload_order]["conditions"]
        assert any(
            condition["action"] == "hide"
            and condition["source_step_order"] == decision_order
            and condition["operator"] == "not_equals"
            and condition["value"] == "upload"
            for condition in upload_conditions
        )
        partner_conditions = by_order[partner_order]["conditions"]
        assert any(
            condition["action"] == "hide"
            and condition["source_step_order"] == decision_order
            and condition["operator"] == "not_equals"
            and condition["value"] == "partner"
            for condition in partner_conditions
        )
        milestone_conditions = by_order[milestone_order]["conditions"]
        assert any(condition["action"] == "auto_complete" for condition in milestone_conditions)
        assert any(condition["action"] == "block" for condition in milestone_conditions)


def test_pflege_jobs_use_multi_partner_self_start_mechanic():
    session = _admin_session()
    steps, _ = _pflege_steps(session)
    by_order = {step["order"]: step for step in steps}

    job_decision = by_order[23]
    assert job_decision["step_type"] == "decision"
    options = job_decision["fields"][0]["options"]
    assert [option["value"] for option in options] == ["selbst", "partner_nutzen"]

    job_partner = by_order[24]
    assert job_partner["step_type"] == "partner_multiselection"
    assert job_partner["filter_tag"] == "Pflege Jobangebote"
    assert any(
        condition["action"] == "hide"
        and condition["source_step_order"] == 23
        and condition["value"] == "partner_nutzen"
        for condition in job_partner["conditions"]
    )

    job_milestone = by_order[25]
    assert job_milestone["step_type"] == "milestone"
    assert any(
        condition["action"] == "auto_complete"
        and condition["source_step_order"] == 23
        and condition["value"] == "selbst"
        for condition in job_milestone["conditions"]
    )


def test_pflege_core_stages_form_a_linear_chain():
    session = _admin_session()
    steps, _ = _pflege_steps(session)
    by_order = {step["order"]: step for step in steps}

    for decision_order, previous_milestone in [(7, 6), (11, 10), (15, 14), (19, 18), (23, 22)]:
        conditions = by_order[decision_order]["conditions"]
        assert any(
            condition["action"] == "block"
            and condition["source_step_order"] == previous_milestone
            and condition["operator"] == "status_not"
            and condition["value"] == "completed"
            for condition in conditions
        )
        assert any(
            condition["action"] == "hide"
            and condition["source_step_order"] == previous_milestone
            and condition["operator"] == "status_not"
            and condition["value"] == "completed"
            for condition in conditions
        )
