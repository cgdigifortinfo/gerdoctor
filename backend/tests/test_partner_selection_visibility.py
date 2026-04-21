"""
Regression test: User picks a partner at a partner_selection step → that partner
sees the user in /partner/submissions ("My Users" tab on the PartnerDashboard).

Historical bug: duplicate IQB partners (umlaut vs no-umlaut) caused the partner
selected at step 12 (filter_tag=Gleichwertigkeitsprüfung with umlaut) to be the
umlaut variant, while the admin/tester logged in as the non-umlaut partner user
and saw nobody. `merge_duplicate_iqb_partners.py` fixed the data, and this test
locks down the happy-path so future regressions fail loudly.

Run: cd /app && python3 backend/tests/test_partner_selection_visibility.py
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"

ADMIN = ("admin@example.com", "Admin123!")


def login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def headers(tok):
    return {"Authorization": f"Bearer {tok}"}


def register(email, name, pw):
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "name": name, "password": pw, "role": "user"},
                      timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    failures = []

    # ---- 1. Create a fresh throw-away user ----
    stamp = int(time.time())
    email = f"e2e-partner-visibility-{stamp}@gerdoctor.example.com"
    name = f"E2E PartnerVis {stamp}"
    try:
        utok = register(email, name, "Pass12345!")
    except requests.HTTPError as e:
        print(f"!! cannot register throwaway user: {e} {e.response.text}")
        return 1

    # Get admin token for cleanup later
    atok = login(*ADMIN)

    try:
        # ---- 2. Walk the user through the journey up to step 12 (Gleichwertigkeit) ----
        steps = requests.get(f"{API}/steps", headers=headers(utok), timeout=15).json()
        by_order = {s["order"]: s for s in steps}

        # Step 1: Stammdaten (required for forecast + filters)
        stammdaten = {
            "first_name": "E2E", "name": "Partnervis",
            "date_of_birth": "1990-01-01", "phone": "+49 100 0000000",
            "address": "Teststr. 1, Berlin",
            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
            "anerkennungsverfahren_bundesland": "Berlin",
            "fachrichtung_praktiziert": "HNO",
            "fachrichtung_gewuenscht": "HNO",
            "field_of_study": "HNO",
        }
        requests.put(f"{API}/steps/progress", headers={**headers(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[1]["id"], "status": "completed", "data": stammdaten}, timeout=15).raise_for_status()

        # Steps 2-11: take upload paths with real files / decisions
        real_doc = [{"file_id": "e2e-doc", "document_type": "Diplom", "filename": "diplom.pdf"}]
        for order in range(2, 12):
            step = by_order[order]
            stype = step.get("step_type")
            if stype == "decision":
                requests.put(f"{API}/steps/progress", headers={**headers(utok), "Content-Type": "application/json"},
                             json={"step_id": step["id"], "status": "completed", "data": {"decision": "upload"}}, timeout=15).raise_for_status()
            elif stype == "form":
                requests.put(f"{API}/steps/progress", headers={**headers(utok), "Content-Type": "application/json"},
                             json={"step_id": step["id"], "status": "completed", "data": {"documents": real_doc}}, timeout=15).raise_for_status()

        # ---- 3. Flip decision at step 10 to "partner" so step 12 becomes visible ----
        requests.put(f"{API}/steps/progress", headers={**headers(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[10]["id"], "status": "completed", "data": {"decision": "partner"}}, timeout=15).raise_for_status()

        # ---- 4. List partners available at step 12 ----
        partners_r = requests.get(f"{API}/partners", headers=headers(utok), timeout=15)
        partners_r.raise_for_status()
        partners = partners_r.json()
        step12_tag = by_order[12].get("filter_tag") or "Gleichwertigkeitsprüfung"
        candidates = [p for p in partners if step12_tag in (p.get("tags") or [])]
        if not candidates:
            failures.append(f"no partner matches filter_tag '{step12_tag}'")
            print("!! no candidates — bailing")
            return 1
        picked = candidates[0]
        picked_id = picked["id"]
        picked_name = picked["name"]
        print(f"  picked partner: {picked_name}  (id={picked_id[-8:]})")

        # ---- 5. User SUBMITS to partner (mirrors frontend handlePartnerSubmission) ----
        sub_r = requests.post(f"{API}/partners/submit",
                              headers={**headers(utok), "Content-Type": "application/json"},
                              json={"partner_id": picked_id,
                                    "data": {"selected_partner_id": picked_id,
                                             "selected_partner_name": picked_name,
                                             "step_order": 12, **stammdaten}},
                              timeout=15)
        sub_r.raise_for_status()
        # Mark step 12 completed
        requests.put(f"{API}/steps/progress", headers={**headers(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[12]["id"], "status": "completed",
                           "data": {"selected_partner_id": picked_id, "selected_partner_name": picked_name}}, timeout=15).raise_for_status()

        # ---- 6. Find the partner-role user linked to the picked partner and log in ----
        all_users = requests.get(f"{API}/admin/users", headers=headers(atok), timeout=15).json()
        partner_users = [u for u in all_users
                         if u.get("role") == "partner" and picked_name in (u.get("partner_names") or [])]
        if not partner_users:
            failures.append(f"no partner-role user found linked to '{picked_name}'")
            return 1
        partner_email = partner_users[0]["email"]
        print(f"  partner-role user for '{picked_name}': {partner_email}")

        # Try Partner123! (seed default). If it fails, skip the last step with a hint.
        try:
            ptok = login(partner_email, "Partner123!")
        except requests.HTTPError:
            print(f"  ! could not log in as {partner_email} with seed password — skipping final check")
            failures.append(f"cannot authenticate as partner user {partner_email} (non-seed password)")
            return 1

        # ---- 7. Fetch /partner/submissions and assert the fresh user shows up ----
        subs = requests.get(f"{API}/partner/submissions", headers=headers(ptok), timeout=15).json()
        seen_emails = [s.get("user_email") for s in subs]
        if email not in seen_emails:
            failures.append(
                f"fresh user '{email}' NOT visible in /partner/submissions of '{picked_name}'. "
                f"Got: {seen_emails}"
            )
        else:
            entry = next(s for s in subs if s.get("user_email") == email)
            print(f"  ✓ partner '{picked_name}' sees fresh user '{email}' "
                  f"(status={entry.get('status')}, match-score/field={entry.get('field_of_study')})")

    finally:
        # ---- Cleanup: remove throwaway user completely ----
        # Find throwaway user id
        throwaway = next((u for u in requests.get(f"{API}/admin/users", headers=headers(atok), timeout=15).json()
                          if u["email"] == email), None)
        if throwaway:
            requests.delete(f"{API}/admin/users/{throwaway['id']}", headers=headers(atok), timeout=15)
            print(f"  • cleanup: deleted throwaway user {email}")

    # ---- Summary ----
    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
