"""Admin survey/steps E2E regressions.

Covers:
- The "URL öffnen" button opens the selected survey's public landing preview,
  even while the browser is authenticated as an admin.
- Switching the survey in the steps tab closes a stale step editor and reloads
  the list for the newly selected survey.
- The survey-step editor resolves referenced steps and fields through searchable
  pickers, supports multi-value conditions, and persists mappings/requirements.
"""
import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, expect

from e2e_screenshots import capture_page, install_api_proxy


load_dotenv("/app/frontend/.env")

BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
API = f"{BACKEND}/api"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PW = "Admin123!"


def _admin_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PW},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_state():
    token = _admin_token()
    surveys = requests.get(f"{API}/admin/surveys", headers=_auth(token), timeout=15).json()
    by_slug = {s["slug"]: s for s in surveys}
    assert "aerzte" in by_slug
    assert "pflege" in by_slug

    created_step_ids = []
    title = f"PFLEGE E2E First Step {int(time.time())}-{uuid.uuid4().hex[:4]}"
    second_title = f"PFLEGE E2E Flow Step {int(time.time())}-{uuid.uuid4().hex[:4]}"
    step_definitions = (
        {
            "order": 901,
            "title": title,
            "description": "Temporary source step for searchable reference pickers.",
            "step_type": "form",
            "fields": [
                {
                    "name": "decision",
                    "field_type": "decision",
                    "label": "Entscheidungsweg",
                    "options": ["upload", "partner", "selbst"],
                },
                {
                    "name": "full_name",
                    "field_type": "text",
                    "label": "Vollständiger Name",
                },
            ],
        },
        {
            "order": 902,
            "title": second_title,
            "description": "Temporary target step for the redesigned editor E2E.",
            "step_type": "form",
            "fields": [
                {
                    "name": "applicant_name",
                    "field_type": "text",
                    "label": "Name des Antragstellers",
                },
                {
                    "name": "documents",
                    "field_type": "multiupload",
                    "label": "Nachweise",
                    "options": ["Visum", "Sprachnachweis"],
                },
            ],
        },
    )
    for definition in step_definitions:
        create = requests.post(
            f"{API}/admin/steps",
            headers=_auth(token),
            json={
                "survey_id": by_slug["pflege"]["id"],
                **definition,
            },
            timeout=15,
        )
        create.raise_for_status()
        created_step_ids.append(create.json()["id"])
    yield {
        "pflege_title": title,
        "pflege_second_title": second_title,
        "source_step_id": created_step_ids[0],
        "target_step_id": created_step_ids[1],
        "pflege_survey_id": by_slug["pflege"]["id"],
    }
    for step_id in created_step_ids:
        requests.delete(f"{API}/admin/steps/{step_id}", headers=_auth(token), timeout=15)


def _login_admin(page):
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.locator('[data-testid="login-email-input"]').fill(ADMIN_EMAIL)
    page.locator('[data-testid="login-password-input"]').fill(ADMIN_PW)
    page.locator('[data-testid="login-submit-btn"]').click()
    page.wait_for_url("**/admin**", timeout=15000)


def _choose_select_option(page, trigger_testid, option_text):
    page.locator(f'[data-testid="{trigger_testid}"]').click()
    page.locator('[role="option"]').filter(has_text=option_text).last.click()


def _choose_searchable_option(page, trigger_testid, search_text, option_text):
    page.locator(f'[data-testid="{trigger_testid}"]').click()
    search = page.locator(f'[data-testid="{trigger_testid}-search"]')
    expect(search).to_be_visible(timeout=5000)
    search.fill(search_text)
    option = page.locator(f'[data-testid="{trigger_testid}-option"]').filter(has_text=option_text)
    expect(option).to_be_visible(timeout=5000)
    option.click()


def _goto_admin_steps(page, survey_slug):
    page.goto(f"{FRONTEND}/admin?tab=steps&survey={survey_slug}&step=1", wait_until="domcontentloaded")
    try:
        expect(page.locator('[data-testid="admin-survey-select"]')).to_be_visible(timeout=30000)
    except AssertionError:
        page.reload(wait_until="domcontentloaded")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_be_visible(timeout=30000)


def _show_all_steps(page):
    _choose_select_option(page, "page-size-admin-steps", "Alle")
    expect(page.locator('[data-testid="pagination-summary-admin-steps"]')).to_contain_text("Ergebnissen")


def test_admin_steps_deep_link_and_survey_switch(admin_state):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        install_api_proxy(page.context, BACKEND)
        _login_admin(page)

        _goto_admin_steps(page, "aerzte")
        expect(page.locator('[data-testid="step-row-order-1"]').first).to_contain_text("Persönliche Daten", timeout=30000)
        capture_page(page, "admin-survey-steps", "01-aerzte-schrittliste")

        open_button_link = page.locator('a:has([data-testid="open-survey-url-btn"])').first
        expect(open_button_link).to_have_attribute("href", "/s/aerzte?preview=1")

        page.locator('[data-testid^="edit-step-"]').first.click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_have_count(0)

        _choose_select_option(page, "admin-survey-select", "FSP Pflege /s/pflege")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("FSP Pflege", timeout=10000)
        expect(page.locator('[data-testid="open-survey-url-btn"]')).to_be_visible()
        expect(page.locator('a:has([data-testid="open-survey-url-btn"])').first).to_have_attribute(
            "href",
            "/s/pflege?preview=1",
        )
        _show_all_steps(page)
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.get_by_text("Persönliche Daten")).to_have_count(0)
        capture_page(page, "admin-survey-steps", "02-pflege-schrittliste-nach-wechsel")

        browser.close()


def test_admin_steps_url_survey_param_overrides_current_survey(admin_state):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        install_api_proxy(page.context, BACKEND)
        _login_admin(page)

        _goto_admin_steps(page, "aerzte")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("Ärzte Anerkennung", timeout=30000)
        expect(page.locator('[data-testid="step-row-order-1"]').first).to_contain_text("Persönliche Daten", timeout=30000)

        _goto_admin_steps(page, "pflege")

        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("FSP Pflege", timeout=30000)
        expect(page.locator('a:has([data-testid="open-survey-url-btn"])').first).to_have_attribute(
            "href",
            "/s/pflege?preview=1",
        )
        _show_all_steps(page)
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.get_by_text("Persönliche Daten")).to_have_count(0)
        capture_page(page, "admin-survey-steps", "03-pflege-url-parameter")

        browser.close()


def test_step_editor_survey_switch_keeps_editor_open_and_reloads(admin_state):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        install_api_proxy(page.context, BACKEND)
        _login_admin(page)

        _goto_admin_steps(page, "aerzte")
        expect(page.locator('[data-testid="step-row-order-1"]').first).to_contain_text("Persönliche Daten", timeout=30000)

        page.locator('[data-testid^="edit-step-"]').first.click()
        expect(page.get_by_role("dialog")).to_be_visible()
        expect(page.locator('[data-testid="step-survey-select"]')).to_contain_text("Ärzte Anerkennung")

        _choose_searchable_option(page, "step-survey-select", "FSP Pflege", "FSP Pflege")

        expect(page.get_by_role("dialog")).to_be_visible(timeout=10000)
        expect(page.locator('[data-testid="step-survey-select"]')).to_contain_text("FSP Pflege", timeout=10000)
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("FSP Pflege", timeout=10000)
        expect(page.locator('a:has([data-testid="open-survey-url-btn"])').first).to_have_attribute(
            "href",
            "/s/pflege?preview=1",
        )
        expect(page.locator('[data-testid="step-title-input"]')).to_have_value("", timeout=10000)
        capture_page(page, "admin-survey-steps", "04-pflege-step-editor")

        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_have_count(0)
        _show_all_steps(page)
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.get_by_text("Persönliche Daten")).to_have_count(0)

        browser.close()


def test_step_editor_searchable_references_multiselect_and_mappings(admin_state):
    token = _admin_token()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        install_api_proxy(page.context, BACKEND)
        _login_admin(page)
        _goto_admin_steps(page, "pflege")
        _show_all_steps(page)

        target_row = page.locator('[data-testid="step-row-order-902"]')
        expect(target_row).to_contain_text(admin_state["pflege_second_title"], timeout=30000)
        target_row.locator('[data-testid^="edit-step-"]').click()
        expect(page.locator('[data-testid="step-editor-dialog"]')).to_be_visible(timeout=10000)
        expect(page.locator('[data-testid="step-section-basic"]')).to_be_visible()

        page.locator('[data-testid="step-section-conditions"]').click()
        page.locator('[data-testid="add-condition"]').click()
        expect(page.locator('[data-testid="condition-card-0"]')).to_be_visible()

        _choose_searchable_option(
            page,
            "condition-source-step-0",
            "PFLEGE E2E First",
            admin_state["pflege_title"],
        )
        _choose_searchable_option(
            page,
            "condition-source-field-0",
            "Entscheidung",
            "Entscheidungsweg",
        )
        _choose_select_option(page, "condition-operator-0", "Ist einer von")
        expect(page.locator('[data-testid="condition-values-0"]')).to_contain_text("upload")

        page.locator('[data-testid="condition-values-0"]').click()
        value_search = page.locator('[data-testid="condition-values-0-search"]')
        value_search.fill("partner")
        page.locator('[data-testid="condition-values-0-option"]').filter(has_text="partner").click()
        page.locator('[data-testid="condition-values-0-done"]').click()

        _choose_select_option(page, "condition-action-0", "Zu anderem Schritt weiterleiten")
        _choose_searchable_option(
            page,
            "condition-target-step-0",
            "PFLEGE E2E First",
            admin_state["pflege_title"],
        )
        page.locator('[data-testid="condition-message-0"]').fill(
            "Der gewählte Weg führt zurück zum vorbereitenden Schritt."
        )
        capture_page(page, "admin-survey-steps", "11-step-editor-bedingungen-multiselect")

        page.locator('[data-testid="step-section-mappings"]').click()
        page.locator('[data-testid="add-field-mapping"]').click()
        _choose_searchable_option(
            page,
            "mapping-source-step-0",
            "PFLEGE E2E First",
            admin_state["pflege_title"],
        )
        _choose_searchable_option(
            page,
            "mapping-source-field-0",
            "Name",
            "Vollständiger Name",
        )
        _choose_searchable_option(
            page,
            "mapping-target-field-0",
            "Antragsteller",
            "Name des Antragstellers",
        )
        capture_page(page, "admin-survey-steps", "12-step-editor-feld-mapping")

        page.locator('[data-testid="step-section-requirements"]').click()
        _choose_searchable_option(
            page,
            "step-required-fields",
            "Antragsteller",
            "Name des Antragstellers",
        )
        page.locator('[data-testid="step-required-fields-done"]').click()
        _choose_searchable_option(page, "step-required-uploads", "Visum", "Visum")
        page.locator('[data-testid="step-required-uploads-done"]').click()
        capture_page(page, "admin-survey-steps", "13-step-editor-pflichtangaben")

        page.locator('[data-testid="save-step-btn"]').click()
        expect(page.get_by_text("Step updated")).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid="step-editor-dialog"]')).to_have_count(0)
        page.wait_for_load_state("networkidle")

        steps = requests.get(
            f"{API}/admin/steps?survey_id={admin_state['pflege_survey_id']}",
            headers=_auth(token),
            timeout=15,
        ).json()
        page.context.unroute_all(behavior="ignoreErrors")
        browser.close()

        saved = next(item for item in steps if item["id"] == admin_state["target_step_id"])
        assert saved["required_fields"] == ["applicant_name"]
        assert saved["required_uploads"] == ["Visum"]
        assert saved["field_mappings"] == [
            {
                "source_step_order": 901,
                "source_field": "full_name",
                "target_field": "applicant_name",
            }
        ]
        assert len(saved["conditions"]) == 1
        condition = saved["conditions"][0]
        assert condition["source_step_order"] == 901
        assert condition["field"] == "decision"
        assert condition["operator"] == "one_of"
        assert condition["value"] == ["upload", "partner"]
        assert condition["action"] == "redirect"
        assert condition["target_step_order"] == 901


def test_step_editor_visual_form_builder_persists_rich_fields(admin_state):
    token = _admin_token()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        install_api_proxy(page.context, BACKEND)
        _login_admin(page)
        _goto_admin_steps(page, "pflege")
        _show_all_steps(page)

        target_row = page.locator('[data-testid="step-row-order-902"]')
        expect(target_row).to_contain_text(admin_state["pflege_second_title"], timeout=30000)
        target_row.locator('[data-testid^="edit-step-"]').click()
        page.locator('[data-testid="step-section-fields"]').click()
        expect(page.locator('[data-testid="survey-form-builder"]')).to_be_visible(timeout=10000)
        expect(page.locator('[data-testid="builder-field-0"]')).to_contain_text("Name des Antragstellers")
        expect(page.locator('[data-testid="builder-field-1"]')).to_contain_text("Nachweise")
        capture_page(page, "form-builder", "01-bestehende-felder-uebernommen")

        page.locator('[data-testid="form-builder-search"]').fill("HTML")
        page.locator('[data-testid="add-field-html"]').click()
        page.locator('[data-testid="builder-field-label"]').fill("Hinweis zur Bewerbung")
        page.locator('[data-testid="builder-field-content"]').fill(
            "<h3>Vor dem Absenden</h3><p>Bitte prüfen Sie alle Angaben.</p>"
        )

        page.locator('[data-testid="form-builder-search"]').fill("")
        page.locator('[data-testid="add-field-image"]').click()
        page.locator('[data-testid="builder-field-label"]').fill("Ablaufgrafik")
        page.locator('[data-testid="builder-image-url"]').fill("/assets/gerdoctor-logo.svg")

        page.locator('[data-testid="add-field-textarea"]').click()
        page.locator('[data-testid="builder-field-label"]').fill("Weitere Hinweise")
        page.locator('[data-testid="builder-field-name"]').fill("weitere_hinweise")
        page.locator('[data-testid="builder-field-required"]').click()

        page.locator('[data-testid="add-field-multiselect"]').click()
        page.locator('[data-testid="builder-field-label"]').fill("Gewünschte Regionen")
        page.locator('[data-testid="builder-field-name"]').fill("regionen")
        option_inputs = page.locator('[data-testid="field-options-editor"] input[aria-label^="Bezeichnung"]')
        option_inputs.nth(0).fill("Berlin")
        option_inputs.nth(1).fill("Hamburg")
        page.locator('[data-testid="builder-field-required"]').click()
        capture_page(page, "form-builder", "02-inhalte-und-mehrfachauswahl-konfiguriert")

        page.locator('[data-testid="builder-field-5"] button[aria-label="Nach oben"]').click()
        page.locator('[data-testid="save-step-btn"]').click()
        expect(page.get_by_text("Step updated")).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid="step-editor-dialog"]')).to_have_count(0)

        saved_steps = requests.get(
            f"{API}/admin/steps?survey_id={admin_state['pflege_survey_id']}",
            headers=_auth(token),
            timeout=15,
        ).json()
        saved = next(item for item in saved_steps if item["id"] == admin_state["target_step_id"])
        assert saved["form_schema_version"] == 1
        assert len(saved["fields"]) == 6
        assert all(field.get("id") and field.get("width") for field in saved["fields"])
        html_field = next(field for field in saved["fields"] if field["field_type"] == "html")
        assert html_field["content"] == "<h3>Vor dem Absenden</h3><p>Bitte prüfen Sie alle Angaben.</p>"
        image_field = next(field for field in saved["fields"] if field["field_type"] == "image")
        assert image_field["image_url"] == "/assets/gerdoctor-logo.svg"
        regions = next(field for field in saved["fields"] if field["name"] == "regionen")
        assert regions["options"] == ["Berlin", "Hamburg"]
        assert regions["required"] is True
        assert {"weitere_hinweise", "regionen"}.issubset(set(saved["required_fields"]))

        _goto_admin_steps(page, "pflege")
        _show_all_steps(page)
        target_row = page.locator('[data-testid="step-row-order-902"]')
        target_row.locator('[data-testid^="edit-step-"]').click()
        page.locator('[data-testid="step-section-fields"]').click()
        expect(page.locator('[data-testid="survey-form-builder"]')).to_contain_text("Gewünschte Regionen")
        capture_page(page, "form-builder", "03-gespeicherte-builder-konfiguration")

        page.context.unroute_all(behavior="ignoreErrors")
        browser.close()


def test_open_survey_url_opens_public_preview_for_logged_in_admin():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        install_api_proxy(page.context, BACKEND)
        _login_admin(page)
        _goto_admin_steps(page, "pflege")

        open_button = page.locator('a:has([data-testid="open-survey-url-btn"])').first
        expect(open_button).to_have_attribute("href", "/s/pflege?preview=1")

        with page.expect_popup() as popup_info:
            page.locator('[data-testid="open-survey-url-btn"]').click()
        preview = popup_info.value
        preview.wait_for_load_state("domcontentloaded")

        assert "/s/pflege?preview=1" in preview.url
        assert "/admin" not in preview.url
        expect(preview.get_by_text("Anerkennung als Pflegefachkraft in Deutschland")).to_be_visible(timeout=30000)
        expect(preview.locator('[data-testid="hero-cta-btn"]')).to_be_visible(timeout=10000)
        capture_page(preview, "admin-survey-steps", "05-pflege-oeffentliche-vorschau")

        browser.close()


def test_form_builder_configuration_renders_for_survey_user(admin_state):
    token = _admin_token()
    headers = _auth(token)
    suffix = uuid.uuid4().hex[:10]
    email = f"form-builder-user-{suffix}@test.de"
    password = "Test123!"
    step_id = None
    user_id = None
    try:
        created_step = requests.post(
            f"{API}/admin/steps",
            headers=headers,
            json={
                "survey_id": admin_state["pflege_survey_id"],
                "title": f"Form Builder Ausgabe {suffix}",
                "description": "Temporärer E2E-Schritt für die Nutzeransicht.",
                "order": -50,
                "step_type": "form",
                "fields": [
                    {"name": "intro", "field_type": "html", "label": "Einleitung", "content": "<h3>Ihre Angaben</h3><p>Bitte sorgfältig ausfüllen.</p><script>window.evil=true</script>"},
                    {"name": "logo", "field_type": "image", "label": "GerDoctor Logo", "image_url": "/assets/gerdoctor-logo.svg", "alt_text": "GerDoctor", "width": "half"},
                    {"name": "notizen", "field_type": "textarea", "label": "Notizen", "help_text": "Mindestens eine kurze Angabe", "rows": 6, "required": True, "width": "half"},
                    {"name": "regionen", "field_type": "multiselect", "label": "Regionen", "options": ["Berlin", "Hamburg"], "required": True},
                    {"name": "nachweis", "field_type": "file", "label": "Optionaler Nachweis", "accept": ".pdf,.png", "multiple": True},
                ],
            },
            timeout=15,
        )
        created_step.raise_for_status()
        step_id = created_step.json()["id"]
        created_user = requests.post(
            f"{API}/admin/users",
            headers=headers,
            json={"email": email, "password": password, "name": "Form Builder E2E", "role": "user", "survey_id": admin_state["pflege_survey_id"]},
            timeout=15,
        )
        created_user.raise_for_status()
        user_id = created_user.json()["id"]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--host-resolver-rules=MAP localhost host.docker.internal"])
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            install_api_proxy(page.context, BACKEND)
            page.goto(f"{FRONTEND}/login", wait_until="networkidle")
            page.locator('[data-testid="login-email-input"]').fill(email)
            page.locator('[data-testid="login-password-input"]').fill(password)
            page.locator('[data-testid="login-submit-btn"]').click()
            page.wait_for_url("**/dashboard**", timeout=15000)

            expect(page.get_by_role("heading", name="Ihre Angaben")).to_be_visible(timeout=30000)
            expect(page.get_by_text("Bitte sorgfältig ausfüllen.").last).to_be_visible()
            assert page.locator("script").filter(has_text="window.evil").count() == 0
            expect(page.locator('img[alt="GerDoctor"]' ).last).to_be_visible()
            expect(page.locator('[data-testid="form-field-notizen"]').last).to_have_attribute("rows", "6")
            expect(page.get_by_text("Mindestens eine kurze Angabe").last).to_be_visible()
            file_input = page.locator('[data-testid="form-field-nachweis"]').last
            expect(file_input).to_have_attribute("accept", ".pdf,.png")
            expect(file_input).to_have_attribute("multiple", "")
            capture_page(page, "form-builder", "04-builder-felder-in-nutzeransicht")

            page.locator('[data-testid="complete-step-btn"]').last.click()
            expect(page.locator('[data-testid="validation-errors"]').last).to_contain_text("Notizen ist ein Pflichtfeld")
            expect(page.locator('[data-testid="validation-errors"]').last).to_contain_text("Regionen ist ein Pflichtfeld")
            page.locator('[data-testid="form-field-notizen"]').last.fill("Vollständige Angaben")
            page.locator('[data-testid="form-field-regionen"] input[value="Berlin"]').last.check()
            capture_page(page, "form-builder", "05-mehrfachauswahl-und-validierung")

            page.context.unroute_all(behavior="ignoreErrors")
            browser.close()
    finally:
        if user_id:
            requests.delete(f"{API}/admin/users/{user_id}", headers=headers, timeout=15)
        if step_id:
            requests.delete(f"{API}/admin/steps/{step_id}", headers=headers, timeout=15)


def test_admin_create_user_assigns_selected_survey():
    token = _admin_token()
    surveys = requests.get(f"{API}/admin/surveys", headers=_auth(token), timeout=15).json()
    pflege = next(survey for survey in surveys if survey["slug"] == "pflege")
    email = f"admin-ui-survey-{uuid.uuid4().hex[:10]}@test.de"
    user_id = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--host-resolver-rules=MAP localhost host.docker.internal",
                ],
            )
            page = browser.new_page()
            install_api_proxy(page.context, BACKEND)
            _login_admin(page)
            page.goto(f"{FRONTEND}/admin?tab=users", wait_until="domcontentloaded")
            expect(page.locator('[data-testid="create-user-btn"]')).to_be_visible(timeout=30000)

            page.locator('[data-testid="create-user-btn"]').click()
            expect(page.locator('[data-testid="create-user-survey"]')).to_be_visible(timeout=10000)
            _choose_select_option(page, "create-user-survey", "FSP Pflege /s/pflege")
            expect(page.locator('[data-testid="create-user-survey"]')).to_contain_text("FSP Pflege")
            capture_page(page, "admin-survey-steps", "06-benutzer-anlegen-dialog")

            page.locator('[data-testid="create-user-name"]').fill("Admin UI Survey Test")
            page.locator('[data-testid="create-user-email"]').fill(email)
            page.locator('[data-testid="create-user-password"]').fill("Test123!")
            page.locator('[data-testid="submit-create-user"]').click()
            expect(page.get_by_text("User erstellt")).to_be_visible(timeout=15000)
            capture_page(page, "admin-survey-steps", "07-benutzer-erstellt")

            users = requests.get(f"{API}/admin/users", headers=_auth(token), timeout=15).json()
            created = next(user for user in users if user["email"] == email)
            user_id = created["id"]
            assert created["survey_id"] == pflege["id"]
            assert created["survey_slug"] == "pflege"

            detail = requests.get(
                f"{API}/admin/users/{user_id}", headers=_auth(token), timeout=15
            ).json()
            assert detail["survey_id"] == pflege["id"]
            assert detail["survey_slug"] == "pflege"
            pflege_steps = requests.get(
                f"{API}/admin/steps?survey_id={pflege['id']}", headers=_auth(token), timeout=15
            ).json()
            assert len(detail["progress"]) == len(pflege_steps)
            assert {row["step_id"] for row in detail["progress"]} == {step["id"] for step in pflege_steps}
            assert all(row["survey_id"] == pflege["id"] for row in detail["progress"])
            browser.close()
    finally:
        if user_id:
            requests.delete(f"{API}/admin/users/{user_id}", headers=_auth(token), timeout=15)


def test_admin_survey_switch_loads_list_and_flow_views(admin_state):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        install_api_proxy(page.context, BACKEND)
        _login_admin(page)

        _goto_admin_steps(page, "aerzte")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("Ärzte Anerkennung", timeout=30000)
        expect(page.locator('[data-testid="step-row-order-1"]').first).to_contain_text("Persönliche Daten", timeout=30000)

        page.locator('[data-testid="steps-view-flow"]').click()
        expect(page.locator('[data-testid="steps-flow-builder"]')).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid^="flow-node-"]').filter(has_text="Persönliche Daten").first).to_be_visible(timeout=15000)
        capture_page(page, "admin-survey-steps", "08-aerzte-flow-ansicht")

        _choose_select_option(page, "admin-survey-select", "FSP Pflege /s/pflege")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("FSP Pflege", timeout=15000)
        _show_all_steps(page)
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid="steps-list-empty-state"]')).to_have_count(0)
        expect(page.get_by_text("Persönliche Daten")).to_have_count(0)

        page.locator('[data-testid="steps-view-flow"]').click()
        expect(page.locator('[data-testid="steps-flow-builder"]')).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid="flow-empty-state"]')).to_have_count(0)
        expect(page.locator('[data-testid^="flow-node-"]').filter(has_text=admin_state["pflege_title"]).first).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid^="flow-node-"]').filter(has_text=admin_state["pflege_second_title"]).first).to_be_visible(timeout=15000)
        capture_page(page, "admin-survey-steps", "09-pflege-flow-ansicht")

        page.locator('[data-testid="steps-view-list"]').click()
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.get_by_text(admin_state["pflege_second_title"])).to_be_visible(timeout=15000)
        capture_page(page, "admin-survey-steps", "10-pflege-listenansicht")

        browser.close()
