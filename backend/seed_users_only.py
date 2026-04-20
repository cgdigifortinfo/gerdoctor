"""
User-only re-seed for GERdoctor.

WHAT IT DOES:
  1. DELETES all users with role == 'user' (plus their progress, progress history,
     partner submissions, uploads and audit-log entries).
  2. RECREATES the 8 canonical demo doctors listed in /app/memory/test_credentials.md
     (password: Demo123!).
  3. Creates fresh user_progress for every demo user (all 24 steps pending) and
     replays the demo "completed_up_to_order" plan so the Admin/Partner dashboards
     look alive.
  4. Preserves: admins, partners, partner users, steps, CMS content, templates,
     audit logs of admins/partners, etc.

Run with: cd /app/backend && python seed_users_only.py
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt

# Load env vars from backend/.env (same pattern as seed_survey_v2 when run via app)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


# --- password helper (mirrors auth.hash_password to avoid app import issues) ---
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---- Canonical demo doctors (role=user) - mirrors seed_survey_v2.seed_demo_data ----
DEMO_USERS = [
    {
        "email": "dr.schmidt@gerdoctor.de",
        "name": "Dr. Jan Schmidt",
        "stammdaten": {
            "first_name": "Jan", "name": "Schmidt",
            "date_of_birth": "1988-04-12", "phone": "+49 170 1234567",
            "address": "Hauptstraße 10, Berlin",
            "anerkennungsstatus": "Ich habe die Berufserlaubnis beantragt",
            "anerkennungsverfahren_bundesland": "Berlin",
            "fachrichtung_praktiziert": "Innere Medizin",
            "fachrichtung_gewuenscht": "Kardiologie",
            "field_of_study": "Innere Medizin",
        },
        "decisions": {2: "upload", 6: "partner"},
        "completed_up_to_order": 9,
    },
    {
        "email": "dr.yilmaz@gerdoctor.de",
        "name": "Dr. Elif Yılmaz",
        "stammdaten": {
            "first_name": "Elif", "name": "Yılmaz",
            "date_of_birth": "1990-09-01", "phone": "+49 171 2345678",
            "address": "Bahnhofstr. 5, München",
            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
            "anerkennungsverfahren_bundesland": "Bayern",
            "fachrichtung_praktiziert": "Pädiatrie",
            "fachrichtung_gewuenscht": "Pädiatrie",
            "field_of_study": "Pädiatrie",
        },
        "decisions": {2: "partner"},
        "completed_up_to_order": 5,
    },
    {
        "email": "dr.chen@gerdoctor.de",
        "name": "Dr. Wei Chen",
        "stammdaten": {
            "first_name": "Wei", "name": "Chen",
            "date_of_birth": "1985-11-22", "phone": "+49 172 3456789",
            "address": "Marktplatz 3, Hamburg",
            "anerkennungsstatus": "Ich habe die Gleichwertigkeitsprüfung beantragt",
            "anerkennungsverfahren_bundesland": "Hamburg",
            "fachrichtung_praktiziert": "Chirurgie",
            "fachrichtung_gewuenscht": "Plastische Chirurgie",
            "field_of_study": "Chirurgie",
        },
        "decisions": {2: "upload", 6: "upload", 10: "partner"},
        "completed_up_to_order": 13,
    },
    {
        "email": "dr.kumar@gerdoctor.de",
        "name": "Dr. Rajesh Kumar",
        "stammdaten": {
            "first_name": "Rajesh", "name": "Kumar",
            "date_of_birth": "1992-01-15", "phone": "+49 173 4567890",
            "address": "Goethestr. 7, Frankfurt",
            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
            "anerkennungsverfahren_bundesland": "Hessen",
            "fachrichtung_praktiziert": "Allgemeinmedizin",
            "fachrichtung_gewuenscht": "Allgemeinmedizin",
            "field_of_study": "Allgemeinmedizin",
        },
        "decisions": {},
        "completed_up_to_order": 1,
    },
    {
        "email": "dr.silva@gerdoctor.de",
        "name": "Dr. Maria Silva",
        "stammdaten": {
            "first_name": "Maria", "name": "Silva",
            "date_of_birth": "1987-06-30", "phone": "+49 174 5678901",
            "address": "Rheinstr. 11, Köln",
            "anerkennungsstatus": "Die Berufserlaubnis wurde mir erteilt",
            "anerkennungsverfahren_bundesland": "Nordrhein-Westfalen",
            "fachrichtung_praktiziert": "Dermatologie",
            "fachrichtung_gewuenscht": "Ästhetische Medizin",
            "field_of_study": "Dermatologie",
        },
        "decisions": {2: "partner", 6: "partner"},
        "completed_up_to_order": 8,
    },
    {
        "email": "dr.ahmed@gerdoctor.de",
        "name": "Dr. Omar Ahmed",
        "stammdaten": {},
        "decisions": {},
        "completed_up_to_order": 0,
    },
    {
        "email": "dr.petrov@gerdoctor.de",
        "name": "Dr. Anna Petrov",
        "stammdaten": {},
        "decisions": {},
        "completed_up_to_order": 0,
    },
    {
        "email": "dr.tanaka@gerdoctor.de",
        "name": "Dr. Hiro Tanaka",
        "stammdaten": {},
        "decisions": {},
        "completed_up_to_order": 0,
    },
]


async def delete_existing_users(db) -> int:
    """Delete all users with role='user' and all their owned collections."""
    users = await db.users.find({"role": "user"}).to_list(10_000)
    user_ids = [str(u["_id"]) for u in users]
    count = len(user_ids)
    if not user_ids:
        return 0

    await db.user_progress.delete_many({"user_id": {"$in": user_ids}})
    await db.progress_history.delete_many({"user_id": {"$in": user_ids}})
    await db.partner_submissions.delete_many({"user_id": {"$in": user_ids}})
    # Optional collections — only delete if present
    for coll in ("uploads", "audit_log", "notifications"):
        try:
            if coll in await db.list_collection_names():
                await db[coll].delete_many({"user_id": {"$in": user_ids}})
        except Exception:
            pass

    await db.users.delete_many({"role": "user"})
    return count


async def create_demo_users(db, steps_by_order) -> tuple:
    """Insert the canonical demo users with fresh progress.
    Skips any demo email that is already occupied by a non-user role (admin/partner).
    Returns (created, skipped).
    """
    created = []
    skipped = []
    pw_hash = hash_password("Demo123!")
    step_docs = list(steps_by_order.values())

    for plan in DEMO_USERS:
        # Guard: another role (admin / partner) may own this email → preserve it
        conflict = await db.users.find_one({"email": plan["email"]})
        if conflict and conflict.get("role") != "user":
            skipped.append({"email": plan["email"], "role": conflict.get("role")})
            continue

        doc = {
            "email": plan["email"],
            "name": plan["name"],
            "role": "user",
            "password_hash": pw_hash,
            "created_at": now_iso(),
            "is_active": True,
            "notification_prefs": {"email": True, "in_app": True},
        }
        res = await db.users.insert_one(doc)
        uid = str(res.inserted_id)
        created.append({"id": uid, "email": plan["email"]})

        # Fresh pending progress for all 24 steps
        pending = [{
            "user_id": uid,
            "step_id": str(s["_id"]),
            "status": "pending",
            "data": {},
            "created_at": now_iso(),
        } for s in step_docs]
        if pending:
            await db.user_progress.insert_many(pending)

        # Apply demo completion plan
        upto = plan["completed_up_to_order"]
        decisions = plan["decisions"]
        if upto >= 1 and plan["stammdaten"]:
            await _set_prog(db, uid, steps_by_order, 1, "completed", plan["stammdaten"])

        for order in range(2, upto + 1):
            s = steps_by_order.get(order)
            if not s:
                continue
            stype = s.get("step_type")
            if stype == "decision":
                dec = decisions.get(order)
                if dec:
                    await _set_prog(db, uid, steps_by_order, order, "completed",
                                    {"decision": dec})
            elif stype == "form":
                await _set_prog(db, uid, steps_by_order, order, "completed", {
                    "documents": [
                        {"file_id": "demo-file", "document_type": "Diplom",
                         "filename": "diplom.pdf"},
                        {"file_id": "demo-file-2", "document_type": "Lebenslauf",
                         "filename": "cv.pdf"},
                    ]
                })
            elif stype in ("partner_selection", "partner_multiselection"):
                await _set_prog(db, uid, steps_by_order, order, "completed",
                                {"selected_partner_name": "Demo Partner"})
            elif stype == "milestone":
                await _set_prog(db, uid, steps_by_order, order, "completed", {})

    return created, skipped


async def _set_prog(db, uid, steps_by_order, order, status, data):
    step = steps_by_order.get(order)
    if not step:
        return
    now = now_iso()
    fields = {"status": status, "data": data or {}, "updated_at": now,
              "started_at": now}
    if status == "completed":
        fields["completed_at"] = now
    await db.user_progress.update_one(
        {"user_id": uid, "step_id": str(step["_id"])},
        {"$set": fields}, upsert=True,
    )


async def run():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # Pre-flight: verify steps are intact (we must not proceed if steps missing)
    step_count = await db.steps.count_documents({})
    if step_count == 0:
        print("!! No steps in DB — run seed_survey_v2.py first. Aborting.")
        client.close()
        sys.exit(2)

    steps = await db.steps.find({}).sort("order", 1).to_list(200)
    steps_by_order = {s["order"]: s for s in steps}
    print(f"Steps intact: {step_count} steps loaded (orders {min(steps_by_order)} … {max(steps_by_order)})")

    # Pre-flight: count preserved entities
    admin_count = await db.users.count_documents({"role": "admin"})
    partner_count = await db.users.count_documents({"role": "partner"})
    partners_count = await db.partners.count_documents({})
    print(f"Preserving: {admin_count} admins, {partner_count} partner users, {partners_count} partner orgs")

    # ---- wipe user-role users ----
    print("\n=== DELETING role='user' USERS ===")
    n = await delete_existing_users(db)
    print(f"  • Deleted {n} user accounts and their owned data")

    # ---- recreate demo users ----
    print("\n=== CREATING DEMO DOCTORS ===")
    created, skipped = await create_demo_users(db, steps_by_order)
    for u in created:
        print(f"  ✓ {u['email']} (id={u['id']})")
    for s in skipped:
        print(f"  ⚠ {s['email']} NOT created — email is owned by role='{s['role']}' (preserved as requested)")

    # ---- verify ----
    print("\n=== FINAL STATE ===")
    after_users = await db.users.count_documents({"role": "user"})
    after_admin = await db.users.count_documents({"role": "admin"})
    after_partner_users = await db.users.count_documents({"role": "partner"})
    after_partners = await db.partners.count_documents({})
    after_steps = await db.steps.count_documents({})
    after_progress = await db.user_progress.count_documents({})
    print(f"  users (role=user): {after_users}  (expected: {len(DEMO_USERS) - len(skipped)})")
    print(f"  users (role=admin): {after_admin}  (unchanged: {admin_count})")
    print(f"  users (role=partner): {after_partner_users}  (unchanged: {partner_count})")
    print(f"  partner orgs:      {after_partners}  (unchanged: {partners_count})")
    print(f"  steps:             {after_steps}  (unchanged: {step_count})")
    print(f"  user_progress:     {after_progress}")

    client.close()
    ok = (
        after_users == (len(DEMO_USERS) - len(skipped))
        and after_admin == admin_count
        and after_partner_users == partner_count
        and after_partners == partners_count
        and after_steps == step_count
    )
    print("\n✓ Done." if ok else "\n!! Verification failed.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(run())
