"""
Seed migration script: Clean old data, seed new partners and users with realistic progress.
SAFE: Keeps all data for preserved users intact. Updates existing partners with logos only.
Keeps: admin@example.com, partner@example.com, cg@digifort.info, doc1@chrizz1001.de, praxis_am_hang@chrizz1001.de
"""
import asyncio, os, bcrypt, uuid
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

KEEP_EMAILS = {
    "admin@example.com", "partner@example.com", "cg@digifort.info",
    "doc1@chrizz1001.de", "praxis_am_hang@chrizz1001.de"
}

def hp(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def now():
    return datetime.now(timezone.utc).isoformat()

def ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def run():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # ========== STEP 1: Collect all partner IDs referenced by kept users ==========
    referenced_partner_ids = set()
    kept_user_ids = set()

    for email in KEEP_EMAILS:
        u = await db.users.find_one({"email": email})
        if not u:
            print(f"  WARN: {email} not found in DB, skipping")
            continue
        uid = str(u["_id"])
        kept_user_ids.add(uid)

        # partner_id on user doc (for partner-role users)
        if u.get("partner_id"):
            referenced_partner_ids.add(u["partner_id"])

        # partner IDs in progress data
        progs = await db.user_progress.find({"user_id": uid}).to_list(100)
        for p in progs:
            d = p.get("data", {})
            if d.get("selected_partner_id"):
                referenced_partner_ids.add(d["selected_partner_id"])
            for sp in d.get("selected_partners", []):
                if sp.get("partner_id"):
                    referenced_partner_ids.add(sp["partner_id"])

        # partner IDs in submissions
        subs = await db.partner_submissions.find({"user_id": uid}).to_list(100)
        for s in subs:
            if s.get("partner_id"):
                referenced_partner_ids.add(s["partner_id"])

    print(f"Kept users: {len(kept_user_ids)}, Referenced partner IDs: {referenced_partner_ids}")

    # ========== STEP 2: Delete NON-kept users and their data ==========
    old_users = await db.users.find({"email": {"$nin": list(KEEP_EMAILS)}}).to_list(1000)
    old_uids = [str(u["_id"]) for u in old_users]
    if old_uids:
        await db.users.delete_many({"_id": {"$in": [u["_id"] for u in old_users]}})
        await db.user_progress.delete_many({"user_id": {"$in": old_uids}})
        await db.progress_history.delete_many({"user_id": {"$in": old_uids}})
        await db.partner_submissions.delete_many({"user_id": {"$in": old_uids}})
        print(f"Deleted {len(old_uids)} old users + their progress/submissions")
    else:
        print("No old users to delete")

    # ========== STEP 3: Update existing referenced partners with logos ==========
    # Map existing partner names to logo URLs from digifort-experts.de
    partner_logo_updates = {
        "ILS": {
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/alte.png",
            "description": "Ihr Partner fuer Visum- und Approbationsantraege.",
            "website": "https://www.ils.de"
        },
        "ILS2": {
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/inmed.png",
            "description": "Professionelle Vorbereitung auf die Kenntnispruefung.",
            "website": "https://inmed-personal.de"
        },
        "ILS3": {
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/mission-leben.png",
            "description": "Berufsbegleitende Weiterbildung fuer Aerzte.",
            "website": "https://mission-leben.de"
        },
        "Praxis am Hang": {
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/dreieck.png",
            "description": "HNO-Praxis mit Schwerpunkt auf internationale Aerzte.",
            "website": "https://praxis-am-hang.de"
        },
    }

    existing_partners = await db.partners.find().to_list(100)
    existing_partner_ids = {}
    for p in existing_partners:
        pid = str(p["_id"])
        existing_partner_ids[p["name"]] = pid
        if p["name"] in partner_logo_updates:
            update_data = partner_logo_updates[p["name"]]
            await db.partners.update_one({"_id": p["_id"]}, {"$set": update_data})
            print(f"  Updated partner '{p['name']}' with logo + description")

    # Delete partners NOT referenced by kept users
    for p in existing_partners:
        pid = str(p["_id"])
        if pid not in referenced_partner_ids:
            await db.partners.delete_one({"_id": p["_id"]})
            print(f"  Deleted unreferenced partner: {p['name']} ({pid})")

    # ========== STEP 4: Seed NEW partners ==========
    new_partners = [
        {
            "name": "digiFORT Experts", "category": "Antragstellung", "tags": ["Antragstellung"],
            "description": "Fachsprachenpruefungen und Antragsbearbeitung fuer internationale Aerzte in Deutschland.",
            "website": "https://digifort-experts.de",
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/digiFORT.png",
            "contact_email": "info@digifort-experts.de",
        },
        {
            "name": "HABS e.V.", "category": "Antragstellung", "tags": ["Antragstellung"],
            "description": "Hessische Agentur fuer berufsqualifizierende Sprache. Sprachfoerderung und Pruefungsvorbereitung.",
            "website": "https://habs-ev.de",
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/habs.png",
            "contact_email": "info@habs-ev.de",
        },
        {
            "name": "HC&S Personaldienstleistungen", "category": "Kenntnisprüfung", "tags": ["Kenntnisprüfung"],
            "description": "Healthcare & Science Personalvermittlung. Vorbereitung auf die Kenntnispruefung.",
            "website": "https://hc-und-s.de",
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/hc-und-s.png",
            "contact_email": "info@hc-und-s.de",
        },
        {
            "name": "Lingoda", "category": "Weiterbildung", "tags": ["Weiterbildung"],
            "description": "Online Sprachschule. Deutschkurse fuer Mediziner - flexibel und ortsunabhaengig.",
            "website": "https://lingoda.com",
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/03/Lingoda.png",
            "contact_email": "info@lingoda.com",
        },
        {
            "name": "InterPers", "category": "Weiterbildung", "tags": ["Weiterbildung"],
            "description": "Interkulturelle Personalberatung und Weiterbildungsplanung fuer internationale Fachkraefte.",
            "website": "https://interpers.de",
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/interpers.png",
            "contact_email": "info@interpers.de",
        },
    ]

    new_partner_ids = {}
    for p in new_partners:
        # Check if already exists (idempotent)
        existing = await db.partners.find_one({"name": p["name"]})
        if existing:
            new_partner_ids[p["name"]] = str(existing["_id"])
            print(f"  Partner '{p['name']}' already exists, skipping")
            continue
        result = await db.partners.insert_one({**p, "is_active": True, "created_at": now()})
        new_partner_ids[p["name"]] = str(result.inserted_id)
        print(f"  Created partner: {p['name']}")

    # Build full partner lookup (existing + new)
    all_partners = await db.partners.find().to_list(100)
    partner_lookup = {}  # name -> id
    for p in all_partners:
        partner_lookup[p["name"]] = str(p["_id"])
    print(f"\nAll partners: {list(partner_lookup.keys())}")

    # ========== STEP 5: Get active steps ==========
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    print(f"Steps ({len(steps)}): {[(s['order'], s['title'], s.get('step_type')) for s in steps]}")

    # ========== STEP 6: Seed NEW users with varying progress ==========
    new_users = [
        {
            "email": "dr.schmidt@gerdoctor.de", "name": "Dr. Anna Schmidt", "pw": "Demo123!",
            "form_data": {
                "name": "Schmidt", "first_name": "Anna", "phone": "+49 170 9876543",
                "address": "Hauptstr. 12, 80331 Muenchen", "field_of_study": "Allgemeinmedizin",
            },
            "completed_steps": 8,
            "partner_choices": {
                "Antragstellung": "digiFORT Experts",
                "Kenntnisprüfung": "HC&S Personaldienstleistungen",
                "Weiterbildung": "Lingoda",
            },
        },
        {
            "email": "dr.yilmaz@gerdoctor.de", "name": "Dr. Emre Yilmaz", "pw": "Demo123!",
            "form_data": {
                "name": "Yilmaz", "first_name": "Emre", "phone": "+49 151 2345678",
                "address": "Berliner Allee 5, 40212 Duesseldorf", "field_of_study": "Innere Medizin",
            },
            "completed_steps": 6,
            "partner_choices": {
                "Antragstellung": "HABS e.V.",
                "Kenntnisprüfung": "HC&S Personaldienstleistungen",
                "Weiterbildung": None,
            },
        },
        {
            "email": "dr.chen@gerdoctor.de", "name": "Dr. Wei Chen", "pw": "Demo123!",
            "form_data": {
                "name": "Chen", "first_name": "Wei", "phone": "+49 176 3456789",
                "address": "Koenigstr. 28, 70173 Stuttgart", "field_of_study": "Chirurgie",
            },
            "completed_steps": 4,
            "partner_choices": {
                "Antragstellung": "digiFORT Experts",
                "Kenntnisprüfung": None,
                "Weiterbildung": None,
            },
        },
        {
            "email": "dr.kumar@gerdoctor.de", "name": "Dr. Priya Kumar", "pw": "Demo123!",
            "form_data": {
                "name": "Kumar", "first_name": "Priya", "phone": "+49 163 4567890",
                "address": "Zeil 42, 60313 Frankfurt", "field_of_study": "Paediatrie",
            },
            "completed_steps": 3,
            "partner_choices": {
                "Antragstellung": "HABS e.V.",
                "Kenntnisprüfung": None,
                "Weiterbildung": None,
            },
        },
        {
            "email": "dr.silva@gerdoctor.de", "name": "Dr. Maria Silva", "pw": "Demo123!",
            "form_data": {
                "name": "Silva", "first_name": "Maria", "phone": "+49 157 5678901",
                "address": "Marienplatz 8, 80331 Muenchen", "field_of_study": "Dermatologie",
            },
            "completed_steps": 2,
            "partner_choices": {
                "Antragstellung": "digiFORT Experts",
                "Kenntnisprüfung": None,
                "Weiterbildung": None,
            },
        },
        {
            "email": "dr.ahmed@gerdoctor.de", "name": "Dr. Fatima Ahmed", "pw": "Demo123!",
            "form_data": {
                "name": "Ahmed", "first_name": "Fatima", "phone": "+49 162 6789012",
                "address": "Friedrichstr. 15, 10117 Berlin", "field_of_study": "Neurologie",
            },
            "completed_steps": 1,
            "partner_choices": {
                "Antragstellung": None,
                "Kenntnisprüfung": None,
                "Weiterbildung": None,
            },
        },
        {
            "email": "dr.petrov@gerdoctor.de", "name": "Dr. Ivan Petrov", "pw": "Demo123!",
            "form_data": {
                "name": "Petrov", "first_name": "Ivan", "phone": "+49 173 7890123",
                "address": "Rathausstr. 3, 20095 Hamburg", "field_of_study": "Orthopaedie",
            },
            "completed_steps": 1,
            "partner_choices": {
                "Antragstellung": None,
                "Kenntnisprüfung": None,
                "Weiterbildung": None,
            },
        },
        {
            "email": "dr.tanaka@gerdoctor.de", "name": "Dr. Yuki Tanaka", "pw": "Demo123!",
            "form_data": {
                "name": "Tanaka", "first_name": "Yuki", "phone": "+49 179 8901234",
                "address": "Schlossstr. 20, 01067 Dresden", "field_of_study": "Gynaekologie",
            },
            "completed_steps": 0,
            "partner_choices": {
                "Antragstellung": None,
                "Kenntnisprüfung": None,
                "Weiterbildung": None,
            },
        },
    ]

    for u in new_users:
        # Skip if already exists
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            print(f"  User {u['email']} already exists, skipping")
            continue

        result = await db.users.insert_one({
            "email": u["email"],
            "password_hash": hp(u["pw"]),
            "name": u["name"],
            "role": "user",
            "profile": {},
            "created_at": ago(30),
        })
        uid = str(result.inserted_id)
        completed = u["completed_steps"]

        for s in steps:
            order = s["order"]
            sid = str(s["_id"])
            step_type = s.get("step_type", "")
            filter_tag = s.get("filter_tag", "")

            if order <= completed:
                # === COMPLETED step ===
                data = {}
                if order == 1:
                    # Form step - fill with personal data
                    data = u.get("form_data", {})
                elif step_type in ("partner_selection", "partner_multiselection") and filter_tag:
                    # Partner selection step - use partner_choices
                    chosen_name = u["partner_choices"].get(filter_tag)
                    if chosen_name and chosen_name in partner_lookup:
                        pid = partner_lookup[chosen_name]
                        data = {
                            "selected_partner_id": pid,
                            "selected_partner_name": chosen_name,
                        }
                        # Create partner submission
                        await db.partner_submissions.insert_one({
                            "id": str(uuid.uuid4()),
                            "user_id": uid,
                            "partner_id": pid,
                            "user_email": u["email"],
                            "user_name": u["name"],
                            "data": data,
                            "status": "submitted",
                            "created_at": ago(25 - order),
                            "updated_at": now(),
                        })
                # milestone / display steps: data stays {}

                await db.user_progress.insert_one({
                    "user_id": uid,
                    "step_id": sid,
                    "status": "completed",
                    "data": data,
                    "started_at": ago(26 - order),
                    "completed_at": ago(25 - order),
                    "created_at": ago(26 - order),
                })

            elif order == completed + 1:
                # === IN PROGRESS step (current) ===
                await db.user_progress.insert_one({
                    "user_id": uid,
                    "step_id": sid,
                    "status": "in_progress",
                    "data": {},
                    "started_at": ago(1),
                    "created_at": ago(1),
                })

            else:
                # === PENDING step ===
                await db.user_progress.insert_one({
                    "user_id": uid,
                    "step_id": sid,
                    "status": "pending",
                    "data": {},
                    "created_at": now(),
                })

        print(f"  Created {u['name']} ({u['email']}) - {completed}/{len(steps)} steps done")

    # ========== STEP 7: Final summary ==========
    print("\n========== MIGRATION COMPLETE ==========")
    user_count = await db.users.count_documents({})
    partner_count = await db.partners.count_documents({})
    progress_count = await db.user_progress.count_documents({})
    sub_count = await db.partner_submissions.count_documents({})
    print(f"  Users: {user_count}")
    print(f"  Partners: {partner_count}")
    print(f"  Progress entries: {progress_count}")
    print(f"  Partner submissions: {sub_count}")

    # Verify kept users data is intact
    print("\n========== KEPT USER VERIFICATION ==========")
    for email in KEEP_EMAILS:
        u = await db.users.find_one({"email": email})
        if not u:
            print(f"  ERROR: {email} missing!")
            continue
        uid = str(u["_id"])
        prog_count = await db.user_progress.count_documents({"user_id": uid})
        sub_count_u = await db.partner_submissions.count_documents({"user_id": uid})
        hist_count = await db.progress_history.count_documents({"user_id": uid})
        print(f"  OK: {email} (role={u.get('role')}) - progress={prog_count}, submissions={sub_count_u}, history={hist_count}")

    client.close()

asyncio.run(run())
