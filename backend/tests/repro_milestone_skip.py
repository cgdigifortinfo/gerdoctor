"""Reproduce: User chooses 'partner' in decision step → picks a partner → milestone gets skipped?

Expected behaviour:
  - Milestone auto_completes ONLY when decision='upload' AND (later we also want: at least one document uploaded).
  - For decision='partner' path, milestone stays 'pending' until the partner explicitly releases it.
"""
import requests, os, sys
from dotenv import load_dotenv
load_dotenv("/app/backend/.env"); load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"


def login(email, pw="Demo123!"):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw})
    r.raise_for_status()
    return r.json()["access_token"]


def get_steps(token):
    return requests.get(f"{API}/steps", headers={"Authorization": f"Bearer {token}"}).json()


def get_progress(token):
    return requests.get(f"{API}/steps/progress", headers={"Authorization": f"Bearer {token}"}).json()


def set_prog(token, step_id, status, data=None):
    r = requests.put(f"{API}/steps/progress",
                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                     json={"step_id": step_id, "status": status, "data": data or {}})
    r.raise_for_status()


def reset(email):
    atok = login("admin@example.com", "Admin123!")
    r = requests.get(f"{API}/admin/users", headers={"Authorization": f"Bearer {atok}"}).json()
    uid = next(u["id"] for u in r if u["email"] == email)
    for s in get_steps(login(email)):
        requests.put(f"{API}/admin/users/{uid}/progress",
                     headers={"Authorization": f"Bearer {atok}", "Content-Type": "application/json"},
                     json={"step_id": s["id"], "status": "pending", "data": {}})


def get_partners(token, tag):
    return requests.get(f"{API}/partners?tag={tag}", headers={"Authorization": f"Bearer {token}"}).json()


def submit_partner(token, partner_id, data):
    r = requests.post(f"{API}/partners/submit",
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      json={"partner_id": partner_id, "data": data})
    r.raise_for_status()


def run():
    email = "dr.petrov@gerdoctor.de"
    reset(email)
    t = login(email)
    steps = get_steps(t)
    by_order = {s["order"]: s for s in steps}
    stammdaten = by_order[1]
    decision = by_order[2]   # Antragstellung Approbation decision
    upload = by_order[3]     # Dokumente (hidden when decision=partner)
    partner_step = by_order[4]  # Service Antragstellung (hidden when decision=upload)
    milestone = by_order[5]  # Übersicht Antragstellung

    # Step 1: complete Stammdaten
    set_prog(t, stammdaten["id"], "completed", {
        "first_name": "Test", "name": "Petrov",
        "date_of_birth": "1990-01-01",
        "phone": "+49", "address": "X",
        "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
        "anerkennungsverfahren_bundesland": "Berlin",
        "fachrichtung_praktiziert": "Innere Medizin",
        "fachrichtung_gewuenscht": "Innere Medizin",
    })

    print("=" * 65)
    print("SCENARIO: decision = 'partner' (No, I want a partner to help)")
    print("=" * 65)
    set_prog(t, decision["id"], "completed", {"decision": "partner"})
    p = {x["step_id"]: x for x in get_progress(t)}
    print(f"  After decision=partner  → milestone(5) status = {p[milestone['id']]['status']}")
    assert p[milestone['id']]["status"] != "completed", \
        "BUG: milestone auto-completed after just decision=partner"

    # Pick a partner for Antragstellung Approbation
    parts = get_partners(t, partner_step.get("filter_tag", "Antragstellung Approbation"))
    if parts:
        pid = parts[0]["id"]
        submit_partner(t, pid, {"note": "Bitte hilf mir"})
        set_prog(t, partner_step["id"], "completed",
                 {"selected_partner_id": pid, "selected_partner_name": parts[0]["name"]})
    p = {x["step_id"]: x for x in get_progress(t)}
    ms_status = p[milestone["id"]]["status"]
    print(f"  After partner selected → milestone(5) status = {ms_status}")
    if ms_status == "completed":
        print("  ✗ BUG CONFIRMED: milestone auto-completed after partner selection, "
               "but it should stay pending until partner releases it")
        return 1
    print("  ✓ milestone stays pending ✓")

    # Also check: decision=upload WITHOUT any uploaded docs should NOT auto-complete milestone
    print()
    print("=" * 65)
    print("SCENARIO: decision = 'upload' but NO docs uploaded yet")
    print("=" * 65)
    reset(email)
    t = login(email)
    set_prog(t, stammdaten["id"], "completed", {
        "first_name": "Test", "name": "Petrov", "date_of_birth": "1990-01-01",
        "phone": "+49", "address": "X",
        "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
        "anerkennungsverfahren_bundesland": "Berlin",
        "fachrichtung_praktiziert": "Innere Medizin",
        "fachrichtung_gewuenscht": "Innere Medizin",
    })
    set_prog(t, decision["id"], "completed", {"decision": "upload"})
    p = {x["step_id"]: x for x in get_progress(t)}
    ms_status = p[milestone["id"]]["status"]
    print(f"  After decision=upload (no docs) → milestone(5) status = {ms_status}")
    if ms_status == "completed":
        print("  ✗ BUG: milestone auto-completed on mere decision=upload")
        print("       Expected: milestone should require docs to actually be uploaded first")
        return 2

    # Now submit upload step with documents
    set_prog(t, upload["id"], "completed", {
        "documents": [
            {"file_id": "f1", "document_type": "Diplom", "filename": "diplom.pdf"},
            {"file_id": "f2", "document_type": "Lebenslauf", "filename": "cv.pdf"},
        ]
    })
    p = {x["step_id"]: x for x in get_progress(t)}
    ms_status = p[milestone["id"]]["status"]
    print(f"  After upload with docs → milestone(5) status = {ms_status}")
    if ms_status != "completed":
        print("  ✗ BUG: milestone should auto-complete when docs are uploaded")
        return 3
    print("  ✓ milestone auto-completed after actual upload")

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(run())
