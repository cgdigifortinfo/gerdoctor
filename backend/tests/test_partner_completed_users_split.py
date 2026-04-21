"""
Regression test: Partner Dashboard — My Users vs Completed Users split.

Flow:
 1. Register a throwaway user and walk through 12 steps, picking a partner at
    step 12 (Gleichwertigkeitsprüfung).
 2. Log in as that partner → user appears in /partner/submissions with
    `partner_work_completed: false` ("My Users").
 3. Partner marks the subsequent milestone (step 13) as completed for the user.
 4. Re-fetch /partner/submissions → user now has
    `partner_work_completed: true` ("Completed Users").
 5. Revert + cleanup.

Run: cd /app && python3 backend/tests/test_partner_completed_users_split.py
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


def main() -> int:
    failures = []
    stamp = int(time.time())
    email = f"e2e-completed-split-{stamp}@gerdoctor.example.com"

    # Register throwaway user
    r = requests.post(f"{API}/auth/register", timeout=15, json={
        "email": email, "name": f"E2E Split {stamp}",
        "password": "Pass12345!", "role": "user",
    })
    r.raise_for_status()
    utok = r.json()["access_token"]
    atok = login(*ADMIN)

    try:
        # Walk to step 12 picking partner path at step 10 (Gleichwertigkeit)
        steps = requests.get(f"{API}/steps", headers=h(utok), timeout=15).json()
        by_order = {s["order"]: s for s in steps}

        stammdaten = {
            "first_name": "E2E", "name": "Split",
            "date_of_birth": "1990-01-01", "phone": "+49 100 0000000",
            "address": "Teststr. 1, Berlin",
            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
            "anerkennungsverfahren_bundesland": "Berlin",
            "fachrichtung_praktiziert": "HNO",
            "fachrichtung_gewuenscht": "HNO",
            "field_of_study": "HNO",
        }
        requests.put(f"{API}/steps/progress",
                     headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[1]["id"], "status": "completed", "data": stammdaten},
                     timeout=15).raise_for_status()

        real_doc = [{"file_id": "e2e-doc", "document_type": "Diplom", "filename": "diplom.pdf"}]
        for order in range(2, 12):
            step = by_order[order]
            stype = step.get("step_type")
            if stype == "decision":
                requests.put(f"{API}/steps/progress",
                             headers={**h(utok), "Content-Type": "application/json"},
                             json={"step_id": step["id"], "status": "completed",
                                   "data": {"decision": "upload"}}, timeout=15).raise_for_status()
            elif stype == "form":
                requests.put(f"{API}/steps/progress",
                             headers={**h(utok), "Content-Type": "application/json"},
                             json={"step_id": step["id"], "status": "completed",
                                   "data": {"documents": real_doc}}, timeout=15).raise_for_status()

        # Step 10 decision → partner (so step 12 becomes the active partner_selection).
        # Before flipping, clear step 11's upload so the milestone #13 isn't auto-completed
        # from our eager walk-through.
        requests.put(f"{API}/steps/progress",
                     headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[11]["id"], "status": "pending", "data": {}},
                     timeout=15).raise_for_status()
        requests.put(f"{API}/steps/progress",
                     headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[10]["id"], "status": "completed",
                           "data": {"decision": "partner"}}, timeout=15).raise_for_status()
        # Explicitly reset the milestone in case it was auto-set earlier
        requests.put(f"{API}/steps/progress",
                     headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[13]["id"], "status": "pending", "data": {}},
                     timeout=15).raise_for_status()

        # Pick first matching partner
        partners = requests.get(f"{API}/partners", headers=h(utok), timeout=15).json()
        step12_tag = by_order[12].get("filter_tag") or "Gleichwertigkeitsprüfung"
        candidates = [p for p in partners if step12_tag in (p.get("tags") or [])]
        if not candidates:
            failures.append(f"no partner matches filter_tag '{step12_tag}'")
            return 1
        picked = candidates[0]
        requests.post(f"{API}/partners/submit",
                      headers={**h(utok), "Content-Type": "application/json"},
                      json={"partner_id": picked["id"],
                            "data": {"selected_partner_id": picked["id"],
                                     "selected_partner_name": picked["name"],
                                     "step_order": 12, **stammdaten}},
                      timeout=15).raise_for_status()
        requests.put(f"{API}/steps/progress",
                     headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": by_order[12]["id"], "status": "completed",
                           "data": {"selected_partner_id": picked["id"],
                                    "selected_partner_name": picked["name"]}},
                     timeout=15).raise_for_status()

        # Find partner-role user
        all_users = requests.get(f"{API}/admin/users", headers=h(atok), timeout=15).json()
        partner_user = next(
            (u for u in all_users
             if u.get("role") == "partner" and picked["name"] in (u.get("partner_names") or [])),
            None,
        )
        if not partner_user:
            failures.append(f"no partner user for '{picked['name']}'")
            return 1

        try:
            ptok = login(partner_user["email"], "Partner123!")
        except requests.HTTPError:
            print(f"  ! cannot log in as {partner_user['email']}")
            failures.append(f"partner login failed: {partner_user['email']}")
            return 1

        # ---- Check #1: user visible in 'My Users' (partner_work_completed=False) ----
        subs = requests.get(f"{API}/partner/submissions", headers=h(ptok), timeout=15).json()
        mine = next((s for s in subs if s.get("user_email") == email), None)
        if not mine:
            failures.append(f"user not in /partner/submissions of {picked['name']}")
            return 1
        if mine.get("partner_work_completed"):
            failures.append(f"expected partner_work_completed=False (milestone not closed), "
                            f"got {mine.get('partner_work_completed')}")
        else:
            print(f"  ✓ Step #1: user in 'My Users' (partner_work_completed=False)")

        # ---- Check #2: partner completes milestone (step 13) → user moves to 'Completed' ----
        user_id = mine["user_id"]
        detail = requests.get(f"{API}/partner/users/{user_id}",
                              headers=h(ptok), timeout=15).json()
        managed = detail.get("partner_managed_step_ids") or []
        steps_by_id = {s["id"]: s for s in detail["steps"]}
        milestone_id = next((sid for sid in managed
                             if steps_by_id.get(sid, {}).get("step_type") == "milestone"), None)
        if not milestone_id:
            failures.append("no managed milestone step found for partner")
            return 1

        requests.put(f"{API}/partner/users/{user_id}/progress",
                     headers={**h(ptok), "Content-Type": "application/json"},
                     json={"step_id": milestone_id, "status": "completed",
                           "data": {"partner_uploads": [{
                               "file_id": "e2e-partner-nachweis",
                               "filename": "nachweis.txt",
                               "document_type": "Partner-Nachweis"}]}},
                     timeout=15).raise_for_status()

        subs_after = requests.get(f"{API}/partner/submissions", headers=h(ptok), timeout=15).json()
        after = next((s for s in subs_after if s.get("user_email") == email), None)
        if not after:
            failures.append("user vanished from /partner/submissions after milestone close")
        elif not after.get("partner_work_completed"):
            failures.append(f"expected partner_work_completed=True after milestone close, "
                            f"got {after.get('partner_work_completed')}")
        else:
            print(f"  ✓ Step #2: after milestone close → 'Completed Users' "
                  f"(partner_work_completed=True)")

    finally:
        # Cleanup throwaway user completely
        throwaway = next(
            (u for u in requests.get(f"{API}/admin/users", headers=h(atok), timeout=15).json()
             if u["email"] == email),
            None,
        )
        if throwaway:
            requests.delete(f"{API}/admin/users/{throwaway['id']}",
                            headers=h(atok), timeout=15)
            print(f"  • cleanup: deleted throwaway user {email}")

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
