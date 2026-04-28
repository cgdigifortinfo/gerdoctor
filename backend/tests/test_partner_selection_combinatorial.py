"""
Combinatorial regression test: exercise every partner_selection AND
partner_multiselection step in the survey to verify:

  1. /api/partner/submissions shows the fresh user in the partner's My Users tab
     (partner_work_completed=False).
  2. /api/admin/users.pending_registrations increases by +1 for:
       - every partner-role user linked to the picked partner org
       - the fresh user (user-role aggregation across partners)
  3. /api/admin/partners.pending_registrations increases by +1 for the picked
     partner org.

Covers step 4 (Antragstellung), step 8 (Gleichwertigkeit), step 12 (Kenntnis),
step 16 (Fachsprachen), step 19 partner_multiselection (Jobangebote),
step 23 (Weiterbildung) — whichever are present in the live survey.

Run: cd /app && python3 backend/tests/test_partner_selection_combinatorial.py
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


def walk_user_up_to(utok, by_order, target_order, stammdaten):
    """Complete steps 1..target_order-1. The decision step that guards the target
    block is flipped to 'partner'; all other decisions stay on 'upload'.
    Form steps in the target block are left pending so the subsequent milestone
    doesn't auto-complete after the partner pick."""
    requests.put(f"{API}/steps/progress",
                 headers={**h(utok), "Content-Type": "application/json"},
                 json={"step_id": by_order[1]["id"], "status": "completed", "data": stammdaten},
                 timeout=15).raise_for_status()

    # Find the decision step that immediately precedes target_order
    decision_order_for_target = None
    for o in range(target_order - 1, 0, -1):
        if by_order.get(o, {}).get("step_type") == "decision":
            decision_order_for_target = o
            break

    real_doc = [{"file_id": "e2e-doc", "document_type": "Diplom", "filename": "diplom.pdf"}]
    last_decision = None
    for order in range(2, target_order):
        step = by_order.get(order)
        if not step:
            continue
        stype = step.get("step_type")
        if stype == "decision":
            last_decision = "partner" if order == decision_order_for_target else "upload"
            requests.put(f"{API}/steps/progress",
                         headers={**h(utok), "Content-Type": "application/json"},
                         json={"step_id": step["id"], "status": "completed",
                               "data": {"decision": last_decision}}, timeout=15).raise_for_status()
        elif stype == "form":
            if last_decision == "upload":
                requests.put(f"{API}/steps/progress",
                             headers={**h(utok), "Content-Type": "application/json"},
                             json={"step_id": step["id"], "status": "completed",
                                   "data": {"documents": real_doc}}, timeout=15).raise_for_status()
            # partner-path form → leave pending


def pending_for_partner_user(snapshot, partner_name):
    for u in snapshot:
        if u.get("role") == "partner" and partner_name in (u.get("partner_names") or []):
            return u.get("pending_registrations") or 0
    return None


def pending_for_user(snapshot, email):
    for u in snapshot:
        if u.get("email") == email:
            return u.get("pending_registrations") or 0
    return None


def pending_for_partner_org(snapshot, partner_name):
    for p in snapshot:
        if p.get("name") == partner_name:
            return p.get("pending_registrations") or 0
    return None


def run_partner_step(stamp_prefix, target_order, multi=False):
    """Run the full flow for a single partner_selection (or multi) step order."""
    stamp = int(time.time() * 1000)
    email = f"e2e-combi-{stamp_prefix}-{stamp}@gerdoctor.example.com"
    name = f"E2E Combi {stamp_prefix} {stamp}"
    failures: list[str] = []
    atok = login(*ADMIN)

    # Register throwaway user
    r = requests.post(f"{API}/auth/register", timeout=15, json={
        "email": email, "name": name, "password": "Pass12345!", "role": "user",
    })
    r.raise_for_status()
    utok = r.json()["access_token"]

    try:
        # Validate the step exists and matches expectation
        steps = requests.get(f"{API}/steps", headers=h(utok), timeout=15).json()
        by_order = {s["order"]: s for s in steps}
        step = by_order.get(target_order)
        if not step:
            return [], f"SKIP (step {target_order} not present)"
        expected_type = "partner_multiselection" if multi else "partner_selection"
        if step.get("step_type") not in ("partner_selection", "partner_multiselection"):
            return [], f"SKIP (step {target_order} is type {step.get('step_type')})"
        # We just require "partner"-family — run the test regardless of exact variant
        stype = step.get("step_type")

        stammdaten = {
            "first_name": "E2E", "name": f"Combi{target_order}",
            "date_of_birth": "1990-01-01", "phone": "+49 100 0000000",
            "address": "Teststr. 1, Berlin",
            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
            "anerkennungsverfahren_bundesland": "Berlin",
            "fachrichtung_praktiziert": "HNO",
            "fachrichtung_gewuenscht": "HNO",
            "field_of_study": "HNO",
        }
        walk_user_up_to(utok, by_order, target_order, stammdaten)

        # Pick a partner matching this step's filter_tag
        partners = requests.get(f"{API}/partners", headers=h(utok), timeout=15).json()
        tag = step.get("filter_tag")
        candidates = [p for p in partners if tag in (p.get("tags") or [])] if tag else partners
        if not candidates:
            failures.append(f"step {target_order}: no partner for tag '{tag}'")
            return failures, f"FAIL (no partner for tag '{tag}')"
        picked = candidates[0]

        # Snapshot BEFORE
        admin_users_before = requests.get(f"{API}/admin/users", headers=h(atok), timeout=15).json()
        admin_partners_before = requests.get(f"{API}/admin/partners", headers=h(atok), timeout=15).json()
        pend_user_partner_before = pending_for_partner_user(admin_users_before, picked["name"]) or 0
        pend_partner_org_before = pending_for_partner_org(admin_partners_before, picked["name"]) or 0

        # Submit to partner (+ mark target step completed with selected_partner_id)
        if stype == "partner_multiselection":
            # multi: submit to 1 partner via submit endpoint (mirrors UI)
            requests.post(f"{API}/partners/submit",
                          headers={**h(utok), "Content-Type": "application/json"},
                          json={"partner_id": picked["id"],
                                "data": {"selected_partner_ids": [picked["id"]],
                                         "selected_partner_name": picked["name"],
                                         "step_order": target_order, **stammdaten}},
                          timeout=15).raise_for_status()
            step_data = {"selected_partner_id": picked["id"],
                         "selected_partner_ids": [picked["id"]],
                         "selected_partner_name": picked["name"]}
        else:
            requests.post(f"{API}/partners/submit",
                          headers={**h(utok), "Content-Type": "application/json"},
                          json={"partner_id": picked["id"],
                                "data": {"selected_partner_id": picked["id"],
                                         "selected_partner_name": picked["name"],
                                         "step_order": target_order, **stammdaten}},
                          timeout=15).raise_for_status()
            step_data = {"selected_partner_id": picked["id"],
                         "selected_partner_name": picked["name"]}
        requests.put(f"{API}/steps/progress",
                     headers={**h(utok), "Content-Type": "application/json"},
                     json={"step_id": step["id"], "status": "completed",
                           "data": step_data}, timeout=15).raise_for_status()

        # Assert: partner-user pending increments by 1
        admin_users_after = requests.get(f"{API}/admin/users", headers=h(atok), timeout=15).json()
        admin_partners_after = requests.get(f"{API}/admin/partners", headers=h(atok), timeout=15).json()
        pend_user_partner_after = pending_for_partner_user(admin_users_after, picked["name"]) or 0
        pend_partner_org_after = pending_for_partner_org(admin_partners_after, picked["name"]) or 0
        pend_user_row = pending_for_user(admin_users_after, email)

        if pend_user_partner_after != pend_user_partner_before + 1:
            failures.append(
                f"step {target_order} partner-user pending: expected "
                f"{pend_user_partner_before}→{pend_user_partner_before + 1}, got "
                f"{pend_user_partner_before}→{pend_user_partner_after}"
            )
        if pend_partner_org_after != pend_partner_org_before + 1:
            failures.append(
                f"step {target_order} partner-org pending: expected "
                f"{pend_partner_org_before}→{pend_partner_org_before + 1}, got "
                f"{pend_partner_org_before}→{pend_partner_org_after}"
            )
        if pend_user_row is None or pend_user_row < 1:
            failures.append(
                f"step {target_order} user-row aggregation missing "
                f"(expected ≥1, got {pend_user_row})"
            )

        # Assert: partner sees user in /partner/submissions (pwc=False)
        partner_user = next(
            (u for u in admin_users_after if u.get("role") == "partner"
             and picked["name"] in (u.get("partner_names") or [])), None,
        )
        if partner_user:
            try:
                ptok = login(partner_user["email"], "Partner123!")
                subs = requests.get(f"{API}/partner/submissions", headers=h(ptok), timeout=15).json()
                mine = next((s for s in subs if s.get("user_email") == email), None)
                if not mine:
                    failures.append(f"step {target_order}: partner cannot see user in submissions")
                elif mine.get("partner_work_completed"):
                    failures.append(f"step {target_order}: fresh submission has pwc=True (expected False)")
            except requests.HTTPError:
                # Non-seed partner passwords → just skip this check
                pass

        if not failures:
            return [], f"PASS (step {target_order} [{stype}] → {picked['name']})"
        return failures, f"FAIL (step {target_order}) — see above"

    finally:
        throwaway = next((u for u in requests.get(f"{API}/admin/users", headers=h(atok), timeout=15).json()
                          if u["email"] == email), None)
        if throwaway:
            requests.delete(f"{API}/admin/users/{throwaway['id']}", headers=h(atok), timeout=15)


def main() -> int:
    atok = login(*ADMIN)
    steps = requests.get(f"{API}/steps", headers=h(atok), timeout=15).json()
    partner_step_orders = sorted([
        s["order"] for s in steps
        if s.get("step_type") in ("partner_selection", "partner_multiselection")
    ])
    print(f"Found partner_selection/multi steps at orders: {partner_step_orders}")
    print()

    all_failures: list[str] = []
    for order in partner_step_orders:
        step = next(s for s in steps if s["order"] == order)
        multi = step["step_type"] == "partner_multiselection"
        tag = step.get("filter_tag", "?")
        prefix = f"o{order}"
        fails, summary = run_partner_step(prefix, order, multi=multi)
        marker = "✓" if not fails and summary.startswith("PASS") else \
                 "⚠" if summary.startswith("SKIP") else "✗"
        print(f"  {marker} step #{order} [{step['step_type']:22s}] tag={tag:35s} → {summary}")
        all_failures.extend(fails)

    print()
    if all_failures:
        print(f"FAILURES ({len(all_failures)}):")
        for f in all_failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
