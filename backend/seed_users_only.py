"""
User-only re-seed for IHCA.

WHAT IT DOES:
  1. DELETES all users with role == 'user' (plus their progress, progress history,
     partner submissions, uploads and audit-log entries).
  2. RECREATES 13 demo doctors with varied progress levels (fresh → almost done).
     Password: Demo123!.
  3. Ensures every partner organization in the `partners` collection has at least
     one linked partner-role user. Missing ones are auto-created (Partner123!)
     with email `partner@<slug(partner-name)>.de` and linked back via
     `users.partner_id` + `partners.linked_user_ids` (idempotent).
  4. Creates fresh user_progress for every demo user (all 24 steps pending) and
     replays the demo "completed_up_to_order" plan so the Admin/Partner dashboards
     look alive — demo users also pick REAL partner IDs for partner_selection
     steps so the match-score/partner dashboards show live submissions.
  5. Preserves: admins, existing partner users, partners, steps, CMS content,
     templates, audit logs.

Run with: cd /app/backend && python seed_users_only.py
"""
import asyncio
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import bcrypt

# Load env vars from backend/.env (same pattern as seed_survey_v2 when run via app)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def slugify(name: str) -> str:
    """ASCII lower-case, dashes instead of spaces — used for auto partner emails."""
    # Decompose unicode (e.g. ü → u) and drop non-ascii
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    norm = re.sub(r"[^a-zA-Z0-9]+", "-", norm).strip("-").lower()
    return norm or "partner"

# Load env vars from backend/.env (same pattern as seed_survey_v2 when run via app)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


# --- password helper (mirrors auth.hash_password to avoid app import issues) ---
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---- Canonical demo doctors (role=user) ----
# `partner_picks` maps decision step order → partner-org name that the user chose.
# Names must match partners.name exactly — falls back to "Demo Partner" if absent.
DEMO_USERS = [
    {
        "email": "dr.schmidt@ihca.de",
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
        "partner_picks": {8: "IQB Prüfungszentrum"},
        "completed_up_to_order": 9,
    },
    {
        "email": "dr.yilmaz@ihca.de",
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
        "partner_picks": {4: "ILS"},
        "completed_up_to_order": 5,
    },
    {
        "email": "dr.chen@ihca.de",
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
        "partner_picks": {12: "FIA Academy"},
        "completed_up_to_order": 13,
    },
    {
        "email": "dr.kumar@ihca.de",
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
        "partner_picks": {},
        "completed_up_to_order": 1,
    },
    {
        "email": "dr.silva@ihca.de",
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
        "partner_picks": {4: "digiFORT Experts", 8: "MedAkademie Berlin"},
        "completed_up_to_order": 8,
    },
    {
        "email": "dr.ahmed@ihca.de",
        "name": "Dr. Omar Ahmed",
        "stammdaten": {},
        "decisions": {},
        "partner_picks": {},
        "completed_up_to_order": 0,
    },
    {
        "email": "dr.petrov@ihca.de",
        "name": "Dr. Anna Petrov",
        "stammdaten": {},
        "decisions": {},
        "partner_picks": {},
        "completed_up_to_order": 0,
    },
    {
        "email": "dr.tanaka@ihca.de",
        "name": "Dr. Hiro Tanaka",
        "stammdaten": {},
        "decisions": {},
        "partner_picks": {},
        "completed_up_to_order": 0,
    },
    # ---- NEW diverse demo doctors ----
    {
        "email": "dr.nguyen@ihca.de",
        "name": "Dr. Linh Nguyen",
        "stammdaten": {
            "first_name": "Linh", "name": "Nguyen",
            "date_of_birth": "1991-03-18", "phone": "+49 175 6789012",
            "address": "Alexanderplatz 2, Berlin",
            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
            "anerkennungsverfahren_bundesland": "Berlin",
            "fachrichtung_praktiziert": "Radiologie",
            "fachrichtung_gewuenscht": "Neuroradiologie",
            "field_of_study": "Radiologie",
        },
        "decisions": {2: "partner"},
        "partner_picks": {4: "HABS e.V."},
        "completed_up_to_order": 5,
    },
    {
        "email": "dr.rossi@ihca.de",
        "name": "Dr. Giulia Rossi",
        "stammdaten": {
            "first_name": "Giulia", "name": "Rossi",
            "date_of_birth": "1989-07-03", "phone": "+49 176 7890123",
            "address": "Viale 14, Stuttgart",
            "anerkennungsstatus": "Ich habe die Berufserlaubnis beantragt",
            "anerkennungsverfahren_bundesland": "Baden-Württemberg",
            "fachrichtung_praktiziert": "HNO",
            "fachrichtung_gewuenscht": "HNO",
            "field_of_study": "HNO",
        },
        "decisions": {2: "upload", 6: "partner", 10: "upload"},
        "partner_picks": {8: "FaMed"},
        "completed_up_to_order": 13,
    },
    {
        "email": "dr.kowalski@ihca.de",
        "name": "Dr. Felix Kowalski",
        "stammdaten": {
            "first_name": "Felix", "name": "Kowalski",
            "date_of_birth": "1984-12-09", "phone": "+49 177 8901234",
            "address": "Königsallee 22, Düsseldorf",
            "anerkennungsstatus": "Ich habe die Fachsprachenprüfung Medizin bestanden",
            "anerkennungsverfahren_bundesland": "Nordrhein-Westfalen",
            "fachrichtung_praktiziert": "Anästhesiologie",
            "fachrichtung_gewuenscht": "Intensivmedizin",
            "field_of_study": "Anästhesiologie",
        },
        "decisions": {2: "upload", 6: "partner", 10: "upload", 14: "partner", 18: "partner"},
        "partner_picks": {8: "IQB Prüfungszentrum", 12: "ILS2", 16: "Lingoda",
                          19: ["MedJob24", "InterPers Jobs"]},
        "completed_up_to_order": 20,
    },
    {
        "email": "dr.okafor@ihca.de",
        "name": "Dr. Kemi Okafor",
        "stammdaten": {
            "first_name": "Kemi", "name": "Okafor",
            "date_of_birth": "1993-05-20", "phone": "+49 178 9012345",
            "address": "Schlossplatz 4, Mainz",
            "anerkennungsstatus": "Ich habe die Kenntnisprüfung bestanden",
            "anerkennungsverfahren_bundesland": "Rheinland-Pfalz",
            "fachrichtung_praktiziert": "Psychiatrie",
            "fachrichtung_gewuenscht": "Kinder- und Jugendpsychiatrie",
            "field_of_study": "Psychiatrie",
        },
        "decisions": {2: "upload", 6: "upload", 10: "upload", 14: "upload", 18: "selbst"},
        "partner_picks": {},
        "completed_up_to_order": 18,
    },
    {
        "email": "dr.popov@ihca.de",
        "name": "Dr. Nadia Popov",
        "stammdaten": {
            "first_name": "Nadia", "name": "Popov",
            "date_of_birth": "1995-08-08", "phone": "+49 179 0123456",
            "address": "Hauptbahnhof 1, Leipzig",
            "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
            "anerkennungsverfahren_bundesland": "Sachsen",
            "fachrichtung_praktiziert": "Urologie",
            "fachrichtung_gewuenscht": "Urologie",
            "field_of_study": "Urologie",
        },
        "decisions": {},
        "partner_picks": {},
        "completed_up_to_order": 1,
    },
]


async def ensure_partner_users(db) -> tuple:
    """Idempotently create a partner-role user for every partner org that lacks one.

    Returns (created, existing). Never deletes anything. Emails: partner@<slug>.de
    with password Partner123!. Also updates partners.linked_user_ids so the
    partner dashboard recognizes the new user.
    """
    created = []
    existing = []
    pw_hash = hash_password("Partner123!")

    partners = await db.partners.find({}).to_list(1000)
    # Build lookup: partner_id → list[user_email]
    linked = {}
    async for u in db.users.find({"role": "partner"}):
        pid = u.get("partner_id")
        if pid:
            linked.setdefault(pid, []).append(u["email"])

    for p in partners:
        pid = str(p["_id"])
        if linked.get(pid):
            existing.append({"partner": p["name"], "users": linked[pid]})
            continue

        # Build deterministic email from the partner name
        slug = slugify(p["name"])
        email = f"partner@{slug}.de"
        # Avoid collisions (e.g. partner appearing twice with near-identical names)
        suffix = 2
        while await db.users.find_one({"email": email}):
            email = f"partner+{suffix}@{slug}.de"
            suffix += 1

        name = f"Partner: {p['name']}"
        user_doc = {
            "email": email,
            "name": name,
            "role": "partner",
            "password_hash": pw_hash,
            "partner_id": pid,
            "created_at": now_iso(),
            "is_active": True,
            "notification_prefs": {"email": True, "in_app": True},
        }
        res = await db.users.insert_one(user_doc)
        uid = str(res.inserted_id)

        # Add to partners.linked_user_ids (create the array if needed)
        await db.partners.update_one(
            {"_id": ObjectId(pid)},
            {"$addToSet": {"linked_user_ids": uid}},
        )
        created.append({"partner": p["name"], "email": email})

    return created, existing


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


async def create_demo_users(db, steps_by_order, partner_name_to_id) -> tuple:
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

        # Apply demo completion plan.
        # We track the last decision so upload/partner/selbst paths are seeded correctly:
        #  - "upload" path: form steps are completed with demo docs → milestone auto-completes
        #  - "partner" path: partner_selection gets a real partner_id → milestone STAYS PENDING
        #    (partner has real work to do in the dashboard)
        #  - "selbst" path (Jobangebote only): milestone auto-completes via decision=selbst
        upto = plan["completed_up_to_order"]
        decisions = plan["decisions"]
        partner_picks = plan.get("partner_picks") or {}
        if upto >= 1 and plan["stammdaten"]:
            await _set_prog(db, uid, steps_by_order, 1, "completed", plan["stammdaten"])

        last_decision = None
        for order in range(2, upto + 1):
            s = steps_by_order.get(order)
            if not s:
                continue
            stype = s.get("step_type")
            if stype == "decision":
                dec = decisions.get(order)
                if dec:
                    last_decision = dec
                    await _set_prog(db, uid, steps_by_order, order, "completed",
                                    {"decision": dec})
            elif stype == "form":
                # Only seed upload documents when the user is on the upload path
                if last_decision == "upload":
                    await _set_prog(db, uid, steps_by_order, order, "completed", {
                        "documents": [
                            {"file_id": "demo-file", "document_type": "Diplom",
                             "filename": "diplom.pdf"},
                            {"file_id": "demo-file-2", "document_type": "Lebenslauf",
                             "filename": "cv.pdf"},
                        ]
                    })
                # partner/selbst path → form step stays pending (it's hidden for them anyway)
            elif stype in ("partner_selection", "partner_multiselection"):
                if last_decision != "partner":
                    continue  # not on partner path → hidden / skip
                raw_pick = partner_picks.get(order)
                # `raw_pick` may be a str (single) or list[str] (multi for partner_multiselection)
                pick_names = raw_pick if isinstance(raw_pick, list) else ([raw_pick] if raw_pick else [])
                resolved_ids = [partner_name_to_id[n] for n in pick_names if n in partner_name_to_id]
                data: dict = {}
                if resolved_ids:
                    # Canonical single-pick fields (keep for backward compat with all UIs/endpoints)
                    first = resolved_ids[0]
                    first_name = next((n for n in pick_names if partner_name_to_id.get(n) == first), "")
                    data = {
                        "selected_partner_id": first,
                        "selected_partner_name": first_name,
                    }
                    if stype == "partner_multiselection":
                        data["selected_partner_ids"] = resolved_ids
                    # Create a partner_submissions row PER picked partner
                    for pid in resolved_ids:
                        sub = {
                            "id": f"seed-{uid}-{pid}-{order}",
                            "user_id": uid,
                            "user_email": plan["email"],
                            "user_name": plan["name"],
                            "partner_id": pid,
                            "data": {"step_order": order, **plan.get("stammdaten", {})},
                            "status": "submitted",
                            "created_at": now_iso(),
                        }
                        await db.partner_submissions.update_one(
                            {"user_id": uid, "partner_id": pid},
                            {"$set": sub}, upsert=True,
                        )
                else:
                    data = {"selected_partner_name": "Demo Partner"}
                await _set_prog(db, uid, steps_by_order, order, "completed", data)
            elif stype == "milestone":
                # Upload path: seed force-completes the milestone (mimics what
                # apply_auto_completes would do after a real upload submission).
                # Selbst path (Jobangebote): auto-completed via decision=selbst.
                # Partner path: STAYS PENDING → real backlog for partner dashboards.
                if last_decision in ("upload", "selbst"):
                    await _set_prog(db, uid, steps_by_order, order, "completed", {})
                # else: partner path → leave pending

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

    # ---- ensure every partner org has a partner-role user (idempotent) ----
    print("\n=== ENSURING PARTNER USERS ===")
    new_partners, existing_partners = await ensure_partner_users(db)
    for p in existing_partners:
        print(f"  ✓ {p['partner']:45s} already linked → {p['users']}")
    for p in new_partners:
        print(f"  ➕ {p['partner']:45s} CREATED user → {p['email']} (pw: Partner123!)")
    if not new_partners:
        print("  (all partners already have linked users)")

    # Rebuild partner counts + name→id lookup for demo users
    partner_users_after = await db.users.count_documents({"role": "partner"})
    partner_name_to_id = {}
    async for p in db.partners.find({}, {"name": 1}):
        partner_name_to_id[p["name"]] = str(p["_id"])

    # ---- wipe user-role users ----
    print("\n=== DELETING role='user' USERS ===")
    n = await delete_existing_users(db)
    print(f"  • Deleted {n} user accounts and their owned data")

    # ---- recreate demo users ----
    print("\n=== CREATING DEMO DOCTORS ===")
    created, skipped = await create_demo_users(db, steps_by_order, partner_name_to_id)
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
    print(f"  users (role=partner): {after_partner_users}  (was: {partner_count}, now includes +{len(new_partners)} auto-created)")
    print(f"  partner orgs:      {after_partners}  (unchanged: {partners_count})")
    print(f"  steps:             {after_steps}  (unchanged: {step_count})")
    print(f"  user_progress:     {after_progress}")

    client.close()
    ok = (
        after_users == (len(DEMO_USERS) - len(skipped))
        and after_admin == admin_count
        and after_partner_users == partner_users_after
        and after_partners == partners_count
        and after_steps == step_count
    )
    print("\n✓ Done." if ok else "\n!! Verification failed.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(run())
