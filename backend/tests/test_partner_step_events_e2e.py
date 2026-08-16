"""FIA Academy partner Step actions and domain-event management E2E test."""
from __future__ import annotations

import copy
import os
import time
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from playwright.sync_api import expect, sync_playwright
from pymongo import MongoClient

from e2e_screenshots import capture_page, install_api_proxy


load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
API = f"{BACKEND}/api"
ADMIN = ("admin@example.com", "Admin123!")
FIA_PARTNER = ("partner-fia-academy@chrizz1001.de", "Partner123!")
FIXTURE = Path(__file__).parent / "fixtures" / "partner-nachweis.txt"


def _login(email: str, password: str) -> str:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _browser_login(page, email: str, password: str, destination: str):
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.locator('[data-testid="login-email-input"]').fill(email)
    page.locator('[data-testid="login-password-input"]').fill(password)
    page.locator('[data-testid="login-submit-btn"]').click()
    page.wait_for_url(f"**{destination}**", timeout=20000)


@pytest.fixture()
def fia_case():
    admin_token = _login(*ADMIN)
    partner_token = _login(*FIA_PARTNER)
    admin_headers = _headers(admin_token)
    partner_headers = _headers(partner_token)

    users = requests.get(f"{API}/admin/users", headers=admin_headers, timeout=30).json()
    fia_user = next(user for user in users if user["email"] == FIA_PARTNER[0])
    submissions = requests.get(f"{API}/partner/submissions", headers=partner_headers, timeout=30).json()

    candidate = None
    detail = None
    milestone = None
    for submission in submissions:
        if submission.get("partner_work_completed"):
            continue
        current_detail = requests.get(
            f"{API}/partner/users/{submission['user_id']}", headers=partner_headers, timeout=30
        ).json()
        steps_by_id = {step["id"]: step for step in current_detail.get("steps", [])}
        progress_by_id = {row["step_id"]: row for row in current_detail.get("progress", [])}
        pending_milestones = [
            steps_by_id[step_id]
            for step_id in current_detail.get("partner_managed_step_ids", [])
            if step_id in steps_by_id
            and steps_by_id[step_id].get("step_type") == "milestone"
            and progress_by_id.get(step_id, {}).get("status", "pending") != "completed"
        ]
        if pending_milestones:
            candidate = submission
            detail = current_detail
            milestone = pending_milestones[0]
            break

    if not candidate or not detail or not milestone:
        pytest.skip("FIA Academy has no active user with a pending managed milestone")

    visible_steps = sorted(detail["steps"], key=lambda step: step["order"])
    previous_step = [step for step in visible_steps if step["order"] < milestone["order"]][-1]
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

    mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017"))
    database = mongo[os.environ.get("DB_NAME", "gerdoctor")]
    original_progress = copy.deepcopy(list(database.user_progress.find({"user_id": candidate["user_id"]})))
    original_rejected_config = copy.deepcopy(database.event_configs.find_one({"event_type": "partner.step.rejected"}))
    original_rejected_template = copy.deepcopy(database.email_templates.find_one({"key": "user_partner_step_rejected"}))

    case = {
        "admin_token": admin_token,
        "partner_token": partner_token,
        "fia_user_id": fia_user["id"],
        "candidate": candidate,
        "detail": detail,
        "milestone": milestone,
        "previous_step": previous_step,
        "started_at": started_at,
        "database": database,
    }
    try:
        yield case
    finally:
        database.user_progress.delete_many({"user_id": candidate["user_id"]})
        if original_progress:
            database.user_progress.insert_many(original_progress)
        if original_rejected_config:
            database.event_configs.replace_one(
                {"event_type": "partner.step.rejected"}, original_rejected_config, upsert=True
            )
        if original_rejected_template:
            database.email_templates.replace_one(
                {"key": "user_partner_step_rejected"}, original_rejected_template, upsert=True
            )
        event_query = {
            "created_at": {"$gte": started_at},
            "actor.email": FIA_PARTNER[0],
            "payload.user_id": candidate["user_id"],
        }
        database.domain_events.delete_many(event_query)
        database.notification_outbox.delete_many({
            "user_id": candidate["user_id"],
            "created_at": {"$gte": started_at},
        })
        database.progress_history.delete_many({
            "user_id": candidate["user_id"],
            "changed_by": FIA_PARTNER[0],
            "timestamp": {"$gte": started_at},
        })
        database.audit_logs.delete_many({
            "actor_email": FIA_PARTNER[0],
            "timestamp": {"$gte": started_at},
        })
        file_documents = list(database.files.find({
            "user_id": fia_user["id"],
            "original_filename": FIXTURE.name,
            "created_at": {"$gte": started_at},
        }))
        storage_root = Path(os.environ.get("LOCAL_STORAGE_ROOT", "/var/lib/gerdoctor/uploads"))
        for file_document in file_documents:
            try:
                (storage_root / file_document["storage_path"]).unlink(missing_ok=True)
            except OSError:
                pass
        if file_documents:
            database.files.delete_many({"_id": {"$in": [document["_id"] for document in file_documents]}})
        mongo.close()


def test_fia_partner_can_reject_then_complete_step_and_admin_controls_events(fia_case):
    candidate = fia_case["candidate"]
    milestone = fia_case["milestone"]
    previous_step = fia_case["previous_step"]
    reason = f"E2E-Korrektur erforderlich {int(time.time())}"

    unmanaged_step = next(
        step for step in fia_case["detail"]["steps"]
        if step["id"] not in fia_case["detail"]["partner_managed_step_ids"]
    )
    unauthorized = requests.post(
        f"{API}/partner/users/{candidate['user_id']}/steps/{unmanaged_step['id']}/action",
        headers={**_headers(fia_case["partner_token"]), "Content-Type": "application/json"},
        json={"action": "complete", "data": {}}, timeout=20,
    )
    assert unauthorized.status_code == 403

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--host-resolver-rules=MAP localhost host.docker.internal"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        install_api_proxy(context, BACKEND)
        page = context.new_page()

        _browser_login(page, *ADMIN, "/admin")
        page.locator('[data-testid="admin-users-tab"]').click()
        page.locator('[data-testid="user-search-input"]').fill(FIA_PARTNER[0])
        page.locator(f'[data-testid="impersonate-user-{fia_case["fia_user_id"]}"]').click()
        page.wait_for_url("**/partner-dashboard**", timeout=20000)

        page.goto(f"{FRONTEND}/partner-dashboard?openUser={candidate['user_id']}", wait_until="domcontentloaded")
        expect(page.get_by_role("dialog")).to_be_visible(timeout=30000)
        action_panel = page.locator(f'[data-testid="milestone-partner-action-{milestone["order"]}"]')
        expect(action_panel).to_be_visible(timeout=30000)
        action_panel.scroll_into_view_if_needed()

        page.locator(f'[data-testid="milestone-rejection-reason-{milestone["order"]}"]').fill(reason)
        page.locator(f'[data-testid="milestone-reject-btn-{milestone["order"]}"]').click()
        expect(page.locator(f'[data-testid="partner-rejection-{milestone["order"]}"]')).to_contain_text(reason, timeout=30000)
        capture_page(page, "partner-step-events", "01-fia-step-abgelehnt")

        rejected_detail = requests.get(
            f"{API}/partner/users/{candidate['user_id']}",
            headers=_headers(fia_case["partner_token"]), timeout=30,
        ).json()
        rejected_progress = {row["step_id"]: row for row in rejected_detail["progress"]}
        assert rejected_progress[milestone["id"]]["status"] == "pending"
        assert rejected_progress[previous_step["id"]]["status"] == "in_progress"
        rejected_events = list(fia_case["database"].domain_events.find({
            "event_type": "partner.step.rejected",
            "payload.user_id": candidate["user_id"],
            "payload.rejection_reason": reason,
        }))
        assert rejected_events and rejected_events[0]["status"] == "processed"
        rejected_event_id = rejected_events[0]["event_id"]

        page.locator(f'[data-testid="milestone-file-input-{milestone["order"]}"]').set_input_files(str(FIXTURE))
        expect(page.locator(f'[data-testid="milestone-file-name-{milestone["order"]}"]')).to_contain_text(FIXTURE.name)
        page.locator(f'[data-testid="milestone-complete-btn-{milestone["order"]}"]').click()
        expect(page.locator(f'[data-testid="milestone-partner-action-{milestone["order"]}"]')).to_have_count(0, timeout=30000)
        expect(page.locator(f'[data-testid="partner-uploads-{milestone["order"]}"]')).to_contain_text(FIXTURE.name)
        capture_page(page, "partner-step-events", "02-fia-upload-und-abschluss")

        completed_detail = requests.get(
            f"{API}/partner/users/{candidate['user_id']}",
            headers=_headers(fia_case["partner_token"]), timeout=30,
        ).json()
        completed_progress = {row["step_id"]: row for row in completed_detail["progress"]}
        assert completed_progress[milestone["id"]]["status"] == "completed"
        assert completed_progress[previous_step["id"]]["status"] == "completed"
        assert any(
            upload.get("filename") == FIXTURE.name
            for upload in completed_progress[milestone["id"]]["data"].get("partner_uploads", [])
        )
        assert fia_case["database"].domain_events.count_documents({
            "event_type": "partner.step.completed",
            "payload.user_id": candidate["user_id"],
            "status": "processed",
        }) >= 1
        assert fia_case["database"].domain_events.count_documents({
            "event_type": "partner.document.uploaded",
            "payload.user_id": candidate["user_id"],
            "status": "processed",
        }) >= 1

        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_have_count(0)
        page.locator('[data-testid="stop-impersonation-btn"]').click()
        page.wait_for_url("**/admin**", timeout=15000)
        page.locator('[data-testid="admin-events-tab"]').click()
        expect(page.locator('[data-testid="event-management"]')).to_be_visible(timeout=30000)
        expect(page.locator('[data-testid="event-config-partner.step.rejected"]')).to_be_visible()
        expect(page.locator('[data-testid="event-row-partner.step.rejected"]').first).to_be_visible()
        expect(page.locator('[data-testid="event-row-partner.step.completed"]').first).to_be_visible()

        rejected_switch = page.locator('[data-testid="event-enabled-partner.step.rejected"]')
        rejected_switch.click()
        page.locator('[data-testid="event-save-partner.step.rejected"]').click()
        expect(rejected_switch).to_have_attribute("data-state", "unchecked", timeout=15000)
        config_response = requests.get(
            f"{API}/admin/event-configs", headers=_headers(fia_case["admin_token"]), timeout=20
        ).json()
        assert next(config for config in config_response if config["event_type"] == "partner.step.rejected")["enabled"] is False

        rejected_switch.click()
        page.locator('[data-testid="event-save-partner.step.rejected"]').click()
        expect(rejected_switch).to_have_attribute("data-state", "checked", timeout=15000)
        capture_page(page, "partner-step-events", "03-admin-eventsteuerung")

        email_edit = page.locator('[data-testid="event-edit-template-partner.step.rejected-email"]')
        expect(email_edit).to_have_attribute(
            "href",
            "/admin?tab=email-templates&template=user_partner_step_rejected&channel=email",
        )

        notification_switch = page.locator(
            '[data-testid="event-handler-enabled-partner.step.rejected-notification"]'
        )
        expect(notification_switch).to_have_attribute("data-state", "unchecked")
        notification_switch.click()
        with page.expect_response(
            lambda response: "/api/admin/event-configs/partner.step.rejected" in response.url
            and response.request.method == "PUT",
            timeout=15000,
        ) as save_response:
            page.locator('[data-testid="event-save-partner.step.rejected"]').click()
        assert save_response.value.ok
        expect(notification_switch).to_have_attribute("data-state", "checked")

        retry = requests.post(
            f"{API}/admin/events/{rejected_event_id}/retry",
            headers=_headers(fia_case["admin_token"]),
            timeout=30,
        )
        assert retry.status_code == 200, retry.text
        outbox = fia_case["database"].notification_outbox.find_one({
            "event_id": rejected_event_id,
            "handler_id": "notify-user-browser-app",
        })
        assert outbox is not None
        assert outbox["status"] == "pending_provider"
        assert set(outbox["channels"]) == {"browser", "app"}
        assert outbox["provider"] == "unconfigured"
        assert reason in outbox["body"]

        page.locator('[data-testid="event-edit-template-partner.step.rejected-notification"]').click()
        page.wait_for_url(
            "**/admin?tab=email-templates&template=user_partner_step_rejected&channel=notification",
            timeout=15000,
        )
        expect(page.locator('[data-testid="notification-message-editor"]')).to_be_visible(timeout=30000)
        marker = f"E2E Notification {int(time.time())}"
        page.locator('[data-testid="notification-title-input"]').fill(f"{marker}: {{{{step_title}}}}")
        page.locator('[data-testid="notification-body-input"]').fill(
            f"{marker} – {{{{partner_name}}}}: {{{{rejection_reason}}}}"
        )
        expect(page.locator('[data-testid="notification-browser-preview"]')).to_contain_text(marker, timeout=15000)
        expect(page.locator('[data-testid="notification-app-preview"]')).to_contain_text(marker, timeout=15000)
        capture_page(page, "partner-step-events", "04-notification-editor-und-previews")

        with page.expect_response(
            lambda response: "/api/admin/email-templates/user_partner_step_rejected" in response.url
            and response.request.method == "PUT",
            timeout=15000,
        ) as template_save_response:
            page.locator('[data-testid="email-template-save-btn"]').click()
        assert template_save_response.value.ok
        saved_template = requests.get(
            f"{API}/admin/email-templates/user_partner_step_rejected",
            headers=_headers(fia_case["admin_token"]),
            timeout=20,
        ).json()
        assert marker in saved_template["notification_title"]
        assert marker in saved_template["notification_body"]

        context.unroute_all(behavior="ignoreErrors")
        context.close()
        browser.close()
