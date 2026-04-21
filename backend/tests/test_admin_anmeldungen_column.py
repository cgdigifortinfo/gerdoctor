"""
Regression test: /api/admin/users returns `pending_registrations` for partner
role users, counting users whose `partner_work_completed` is False for the
partner's org. Mirrors the Admin User-Liste "Anmeldungen"-Spalte.

Flow:
 1. Register throwaway user, walk to step 12, pick a partner in Gleichwertigkeit.
 2. Look up that partner's partner-role user in /admin/users and assert
    pending_registrations >= 1 (the throwaway user is pending milestone closure).
 3. Partner closes the milestone → re-check /admin/users: pending drops by 1.
 4. Cleanup throwaway user.

Run: cd /app && python3 backend/tests/test_admin_anmeldungen_column.py
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


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


def admin_users_snapshot(atok):
    return requests.get(f"{API}/admin/users", headers=h(atok), timeout=15).json()


def pending_for_partner_user(snapshot, partner_name):
    """Return the first pending_registrations value for a partner-role user
    linked to the given partner org name (there can be several partner users
    per org — we assume the count is identical for all)."""
    for u in snapshot:
        if u.get("role") != "partner":
            continue
        if partner_name in (u.get("partner_names") or []):
            return u.get("pending_registrations")
    return None


def main() -> int:
    failures = []
    stamp = int(time.time())
    email = f"e2e-anmeldungen-{stamp}@gerdoctor.example.com"

    r = requests.post(f"{API}/auth/register", timeout=15, json={
        "email": email, "name": f"E2E Anmeldungen {stamp}",
        "password": "Pass12345!", "role": "user",
    })
    r.raise_for_status()
    utok = r.json()["access_token"]
    atok = login(*ADMIN)

    # ---- sanity: `pending_registrations` field exists on partner rows ----
    before = admin_users_snapshot(atok)
    partner_rows = [u for u in before if u.get("role") == "partner"]
    if not any("pending_registrations" in u for u in partner_rows):
        failures.append("pending_registrations field missing on partner-role users")

    non_partner = [u for u in before if u.get("role") != "partner"]
    for u in non_partner:
        if u.get("pending_registrations") is not None:
            failures.append(f"non-partner user has pending_registrations={u['pending_registrations']} "
                            f"(expected None) — {u['email']}")
            break

    try:
        # Walk to step 12, decision=partner, pick a Gleichwertigkeit partner
        steps = requests.get(f"{API}/steps", headers=h(utok), timeout=15).json()
        by_order = {s["order"]: s for s in steps}
        stammdaten = {
            "first_name": "E2E", "name": "Anmeld",
            "date_of_birth": "1990-01-01", "phone": "+49 100 0000000",
            "address": "Teststr. 1, Berlin",
            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
            "anerkennungsverfahren_bundesland": "Berlin",
            "fachrichtung_praktiziert": "HNO",
            "fachrichtung_gewuenscht": "HNO",
            "field_of_study": "HNO",
        }
        requests.put(f"{API}/steps/progress", headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[1]["id"], "status": "completed", "data": stammdaten},
                     timeout=15).raise_for_status()
        real_doc = [{"file_id": "e2e-doc", "document_type": "Diplom", "filename": "diplom.pdf"}]
        for order in range(2, 10):
            step = by_order[order]
            if step["step_type"] == "decision":
                requests.put(f"{API}/steps/progress", headers={**h(utok), "Content-Type": "application/json"},
                             json={"step_id": step["id"], "status": "completed",
                                   "data": {"decision": "upload"}}, timeout=15).raise_for_status()
            elif step["step_type"] == "form":
                requests.put(f"{API}/steps/progress", headers={**h(utok), "Content-Type": "application/json"},
                             json={"step_id": step["id"], "status": "completed",
                                   "data": {"documents": real_doc}}, timeout=15).raise_for_status()
        requests.put(f"{API}/steps/progress", headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[10]["id"], "status": "completed",
                           "data": {"decision": "partner"}}, timeout=15).raise_for_status()
        # Reset #13 milestone in case it auto-set
        requests.put(f"{API}/steps/progress", headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[13]["id"], "status": "pending", "data": {}},
                     timeout=15).raise_for_status()
        partners = requests.get(f"{API}/partners", headers=h(utok), timeout=15).json()
        tag = by_order[12].get("filter_tag") or "Gleichwertigkeitsprüfung"
        picked = next((p for p in partners if tag in (p.get("tags") or [])), None)
        if not picked:
            failures.append(f"no partner matches filter_tag '{tag}'")
            return 1

        # Snapshot pending BEFORE submit
        before_submit = admin_users_snapshot(atok)
        pending_before = pending_for_partner_user(before_submit, picked["name"]) or 0

        # Submit to partner
        requests.post(f"{API}/partners/submit", headers={**h(utok), "Content-Type": "application/json"},
                      json={"partner_id": picked["id"],
                            "data": {"selected_partner_id": picked["id"],
                                     "selected_partner_name": picked["name"],
                                     "step_order": 12, **stammdaten}},
                      timeout=15).raise_for_status()
        requests.put(f"{API}/steps/progress", headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[12]["id"], "status": "completed",
                           "data": {"selected_partner_id": picked["id"],
                                    "selected_partner_name": picked["name"]}},
                     timeout=15).raise_for_status()

        # ---- Check #1: pending count goes up by 1 ----
        after_submit = admin_users_snapshot(atok)
        pending_after = pending_for_partner_user(after_submit, picked["name"]) or 0
        if pending_after != pending_before + 1:
            failures.append(
                f"expected pending_registrations {pending_before}→{pending_before + 1} for "
                f"'{picked['name']}', got {pending_before}→{pending_after}"
            )
        else:
            print(f"  ✓ Check #1: pending_registrations {pending_before}→{pending_after} for '{picked['name']}'")

        # ---- Check #2: close milestone → pending drops by 1 ----
        partner_user = next((u for u in after_submit
                             if u.get("role") == "partner"
                             and picked["name"] in (u.get("partner_names") or [])), None)
        if not partner_user:
            failures.append(f"no partner-role user for '{picked['name']}'")
            return 1
        try:
            ptok = login(partner_user["email"], "Partner123!")
        except requests.HTTPError:
            failures.append(f"cannot log in as partner {partner_user['email']}")
            return 1
        # Find this user's id + managed milestone
        subs = requests.get(f"{API}/partner/submissions", headers=h(ptok), timeout=15).json()
        mine = next((s for s in subs if s.get("user_email") == email), None)
        if not mine:
            failures.append("fresh user not visible in partner submissions")
            return 1
        detail = requests.get(f"{API}/partner/users/{mine['user_id']}",
                              headers=h(ptok), timeout=15).json()
        steps_by_id = {s["id"]: s for s in detail["steps"]}
        milestone_id = next((sid for sid in detail.get("partner_managed_step_ids", [])
                             if steps_by_id.get(sid, {}).get("step_type") == "milestone"), None)
        if not milestone_id:
            failures.append("no managed milestone found")
            return 1
        requests.put(f"{API}/partner/users/{mine['user_id']}/progress",
                     headers={**h(ptok), "Content-Type": "application/json"},
                     json={"step_id": milestone_id, "status": "completed",
                           "data": {"partner_uploads": [{
                               "file_id": "e2e-nachweis", "filename": "nachweis.txt",
                               "document_type": "Partner-Nachweis"}]}},
                     timeout=15).raise_for_status()
        after_close = admin_users_snapshot(atok)
        pending_close = pending_for_partner_user(after_close, picked["name"]) or 0
        if pending_close != pending_before:
            failures.append(
                f"expected pending_registrations to return to {pending_before} after "
                f"milestone close, got {pending_close}"
            )
        else:
            print(f"  ✓ Check #2: pending_registrations {pending_after}→{pending_close} after milestone close")

    finally:
        throwaway = next((u for u in admin_users_snapshot(atok) if u["email"] == email), None)
        if throwaway:
            requests.delete(f"{API}/admin/users/{throwaway['id']}", headers=h(atok), timeout=15)
            print(f"  • cleanup: deleted {email}")

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
