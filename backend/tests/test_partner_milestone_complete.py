"""
Regression test: Partner can complete & upload files on milestone steps.

Covers:
  1. /api/admin/users returns partner_names per user
  2. /api/partner/users/{id} returns partner_managed_step_ids (including the
     next milestone after a picked partner_selection)
  3. Partner can upload a file and complete the milestone in one request
     (stored under data.partner_uploads)
  4. Cleanup resets milestone state

Run: cd /app && python3 backend/tests/test_partner_milestone_complete.py
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"

ADMIN = ("admin@example.com", "Admin123!")
PARTNER = ("partner@digifort-experts.de", "Partner123!")
TARGET_USER_EMAIL = "dr.silva@gerdoctor.de"


def login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def headers(tok):
    return {"Authorization": f"Bearer {tok}"}


def main() -> int:
    failures = []

    # --- Setup tokens & target user id ---
    atoken = login(*ADMIN)
    ptoken = login(*PARTNER)
    users = requests.get(f"{API}/admin/users", headers=headers(atoken), timeout=15).json()
    peter = next((u for u in users if u["email"] == TARGET_USER_EMAIL), None)
    if not peter:
        print(f"!! target user {TARGET_USER_EMAIL} not found — skipping")
        return 0  # don't fail CI if fixture is missing
    peter_id = peter["id"]

    # --- 1. Admin user list includes partner_names ---
    partner_users = [u for u in users if u.get("role") == "partner" and u.get("partner_names")]
    if not partner_users:
        failures.append("no partner-role users show partner_names in /admin/users")
    else:
        print(f"  ✓ {len(partner_users)} partner-role users carry partner_names")

    peter_partners = peter.get("partner_names", [])
    if "digiFORT Experts" not in peter_partners:
        failures.append(f"expected 'digiFORT Experts' in silva partner_names, got {peter_partners}")
    else:
        print(f"  ✓ silva.partner_names = {peter_partners}")

    # --- 2. Partner user-detail returns partner_managed_step_ids ---
    detail = requests.get(f"{API}/partner/users/{peter_id}", headers=headers(ptoken), timeout=15).json()
    managed = detail.get("partner_managed_step_ids", [])
    steps_by_id = {s["id"]: s for s in detail["steps"]}
    if not managed:
        failures.append("partner_managed_step_ids is empty")
    # Expect at least one partner_selection + one milestone
    types = [steps_by_id[sid]["step_type"] for sid in managed if sid in steps_by_id]
    if "partner_selection" not in types and "partner_multiselection" not in types:
        failures.append(f"no partner_selection step in managed list: {types}")
    if "milestone" not in types:
        failures.append(f"no milestone step in managed list: {types}")
    if not failures:
        print(f"  ✓ partner_managed_step_ids covers {len(managed)} steps ({types})")

    # --- 3. Partner completes milestone with file upload ---
    milestone_id = next(
        (sid for sid in managed if steps_by_id[sid]["step_type"] == "milestone"),
        None,
    )
    if not milestone_id:
        print("  ! no milestone found — skipping upload flow")
        return 1 if failures else 0

    # Snapshot original state so we can restore it
    orig_prog = next((p for p in detail["progress"] if p["step_id"] == milestone_id), None)
    orig_status = (orig_prog or {}).get("status", "pending")
    orig_data = (orig_prog or {}).get("data", {}) or {}

    try:
        # Upload a file as the partner
        with open("/tmp/_test_partner_nachweis.txt", "w") as f:
            f.write("partner milestone test content")
        with open("/tmp/_test_partner_nachweis.txt", "rb") as f:
            up = requests.post(
                f"{API}/files/upload",
                headers=headers(ptoken),
                files={"file": ("nachweis.txt", f, "text/plain")},
                timeout=20,
            )
        up.raise_for_status()
        file_id = up.json()["id"]

        # Complete milestone with partner_uploads payload
        payload = {
            "step_id": milestone_id,
            "status": "completed",
            "data": {
                "partner_uploads": [{
                    "file_id": file_id,
                    "filename": "nachweis.txt",
                    "document_type": "Partner-Nachweis",
                }],
            },
        }
        r = requests.put(
            f"{API}/partner/users/{peter_id}/progress",
            headers={**headers(ptoken), "Content-Type": "application/json"},
            json=payload, timeout=15,
        )
        r.raise_for_status()

        # Verify
        after = requests.get(f"{API}/partner/users/{peter_id}", headers=headers(ptoken), timeout=15).json()
        ms_prog = next((p for p in after["progress"] if p["step_id"] == milestone_id), None)
        if not ms_prog or ms_prog.get("status") != "completed":
            failures.append(f"milestone not completed after partner PUT (got {ms_prog})")
        else:
            uploads = (ms_prog.get("data") or {}).get("partner_uploads") or []
            if not any(u.get("file_id") == file_id for u in uploads):
                failures.append(f"partner_uploads not persisted (got {uploads})")
            else:
                print(f"  ✓ milestone completed + file persisted ({len(uploads)} upload[s])")

    finally:
        # --- 4. Cleanup: restore original state ---
        requests.put(
            f"{API}/partner/users/{peter_id}/progress",
            headers={**headers(ptoken), "Content-Type": "application/json"},
            json={
                "step_id": milestone_id,
                "status": orig_status,
                "data": orig_data,
            }, timeout=15,
        )
        try:
            os.remove("/tmp/_test_partner_nachweis.txt")
        except OSError:
            pass
        print(f"  • restored milestone to status={orig_status}")

    # --- Summary ---
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
