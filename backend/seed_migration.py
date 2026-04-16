"""
Seed migration script: Clean old data, seed new partners and users with realistic progress.
Keeps: admin@example.com, partner@example.com, cg@digifort.info, doc1@chrizz1001.de, praxis_am_hang@chrizz1001.de
"""
import asyncio, os, bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

KEEP_EMAILS = {"admin@example.com", "partner@example.com", "cg@digifort.info", "doc1@chrizz1001.de", "praxis_am_hang@chrizz1001.de"}

def hp(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def now(): return datetime.now(timezone.utc).isoformat()
def ago(days): return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

async def run():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # ========== CLEAN OLD DATA ==========
    # Delete users not in keep list
    old_users = await db.users.find({"email": {"$nin": list(KEEP_EMAILS)}}).to_list(1000)
    old_uids = [str(u["_id"]) for u in old_users]
    if old_uids:
        await db.users.delete_many({"_id": {"$in": [u["_id"] for u in old_users]}})
        await db.user_progress.delete_many({"user_id": {"$in": old_uids}})
        await db.progress_history.delete_many({"user_id": {"$in": old_uids}})
        await db.partner_submissions.delete_many({"user_id": {"$in": old_uids}})
        print(f"Deleted {len(old_uids)} old users + their progress/submissions")

    # Delete old partners (keep ILS which partner@example.com is linked to)
    partner_user = await db.users.find_one({"email": "partner@example.com"})
    keep_partner_id = partner_user.get("partner_id") if partner_user else None
    if keep_partner_id:
        await db.partners.delete_many({"_id": {"$ne": ObjectId(keep_partner_id)}})
        print(f"Deleted old partners, kept ILS (id={keep_partner_id})")
    else:
        await db.partners.delete_many({})
        print("Deleted all partners (no partner_id found)")

    # Get steps
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    step_map = {s["order"]: str(s["_id"]) for s in steps}
    print(f"Steps: {[(s['order'], s['title']) for s in steps]}")

    # ========== SEED NEW PARTNERS ==========
    new_partners = [
        # Antragstellung partners
        {"name": "digiFORT Experts", "description": "Fachsprachenprüfungen und Antragsbearbeitung für internationale Ärzte in Deutschland.", "category": "Antragstellung", "tags": ["Antragstellung"],
         "website": "https://digifort-experts.de", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/digiFORT.png", "contact_email": "info@digifort-experts.de"},
        {"name": "HABS e.V.", "description": "Hessische Agentur für berufsqualifizierende Sprache. Sprachförderung und Prüfungsvorbereitung.", "category": "Antragstellung", "tags": ["Antragstellung"],
         "website": "https://habs-ev.de", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/habs.png", "contact_email": "info@habs-ev.de"},
        # Kenntnisprüfung partners
        {"name": "inmed Personal", "description": "Professionelle Personalvermittlung und Prüfungsvorbereitung für internationale Mediziner.", "category": "Kenntnisprüfung", "tags": ["Kenntnisprüfung"],
         "website": "https://inmed-personal.de", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/inmed.png", "contact_email": "info@inmed-personal.de"},
        {"name": "HC&S Personaldienstleistungen", "description": "Healthcare & Science Personalvermittlung. Vorbereitung auf die Kenntnisprüfung.", "category": "Kenntnisprüfung", "tags": ["Kenntnisprüfung"],
         "website": "https://hc-und-s.de", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/hc-und-s.png", "contact_email": "info@hc-und-s.de"},
        # Weiterbildung partners
        {"name": "Mission Leben", "description": "Akademie und Weiterbildungsstätte. Berufsbegleitende Weiterbildung für Ärzte.", "category": "Weiterbildung", "tags": ["Weiterbildung"],
         "website": "https://mission-leben.de", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/mission-leben.png", "contact_email": "akademie@mission-leben.de"},
        {"name": "Lingoda", "description": "Online Sprachschule. Deutschkurse für Mediziner – flexibel und ortsunabhängig.", "category": "Weiterbildung", "tags": ["Weiterbildung"],
         "website": "https://lingoda.com", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/03/Lingoda.png", "contact_email": "info@lingoda.com"},
        {"name": "InterPers", "description": "Interkulturelle Personalberatung und Weiterbildungsplanung für internationale Fachkräfte.", "category": "Weiterbildung", "tags": ["Weiterbildung"],
         "website": "https://interpers.de", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/interpers.png", "contact_email": "info@interpers.de"},
    ]

    partner_ids = {}
    # Update existing ILS partner
    if keep_partner_id:
        await db.partners.update_one({"_id": ObjectId(keep_partner_id)}, {"$set": {
            "name": "ILS Antragstellung", "description": "Ihr Partner für Visum- und Approbationsanträge. Vollständige Begleitung durch den Antragsprozess.",
            "category": "Antragstellung", "tags": ["Antragstellung"], "website": "https://www.ils.de",
            "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/alte.png", "contact_email": "info@ils.de"
        }})
        partner_ids["ILS Antragstellung"] = keep_partner_id
        print(f"Updated ILS partner")

    for p in new_partners:
        result = await db.partners.insert_one({**p, "is_active": True, "created_at": now()})
        partner_ids[p["name"]] = str(result.inserted_id)
    print(f"Created {len(new_partners)} new partners")

    # Helper: get partner ID by tag
    def get_partner_by_tag(tag):
        for p in new_partners:
            if tag in p.get("tags", []):
                return partner_ids[p["name"]]
        if "Antragstellung" == tag and "ILS Antragstellung" in partner_ids:
            return partner_ids["ILS Antragstellung"]
        return None

    # ========== SEED NEW USERS ==========
    new_users = [
        {"email": "dr.schmidt@gerdoctor.de", "name": "Dr. Anna Schmidt", "pw": "Demo123!",
         "form": {"name": "Schmidt", "first_name": "Anna", "phone": "+49 170 9876543", "address": "Hauptstr. 12, 80331 München", "field_of_study": "Allgemeinmedizin",
                  "documents": [{"document_type": "Visum", "file_id": "demo-visum-001", "filename": "Visum_Schmidt.pdf"}, {"document_type": "Antrag auf Approbation", "file_id": "demo-antrag-001", "filename": "Approbation_Schmidt.pdf"}]},
         "completed_steps": 8, "partner_antrag": "ILS Antragstellung", "partner_kp": "inmed Personal", "partner_wb": "Mission Leben"},

        {"email": "dr.yilmaz@gerdoctor.de", "name": "Dr. Emre Yilmaz", "pw": "Demo123!",
         "form": {"name": "Yilmaz", "first_name": "Emre", "phone": "+49 151 2345678", "address": "Berliner Allee 5, 40212 Düsseldorf", "field_of_study": "Innere Medizin",
                  "documents": [{"document_type": "Visum", "file_id": "demo-visum-002", "filename": "Visum_Yilmaz.pdf"}]},
         "completed_steps": 6, "partner_antrag": "digiFORT Experts", "partner_kp": "HC&S Personaldienstleistungen", "partner_wb": None},

        {"email": "dr.chen@gerdoctor.de", "name": "Dr. Wei Chen", "pw": "Demo123!",
         "form": {"name": "Chen", "first_name": "Wei", "phone": "+49 176 3456789", "address": "Königstr. 28, 70173 Stuttgart", "field_of_study": "Chirurgie",
                  "documents": [{"document_type": "Visum", "file_id": "demo-visum-003", "filename": "Visum_Chen.pdf"}, {"document_type": "Eingangsbescheinigung bei zuständiger Behörde", "file_id": "demo-eing-003", "filename": "Eingangsbescheinigung_Chen.pdf"}]},
         "completed_steps": 4, "partner_antrag": "HABS e.V.", "partner_kp": None, "partner_wb": None},

        {"email": "dr.kumar@gerdoctor.de", "name": "Dr. Priya Kumar", "pw": "Demo123!",
         "form": {"name": "Kumar", "first_name": "Priya", "phone": "+49 163 4567890", "address": "Zeil 42, 60313 Frankfurt", "field_of_study": "Pädiatrie",
                  "documents": [{"document_type": "Visum", "file_id": "demo-visum-004", "filename": "Visum_Kumar.pdf"}]},
         "completed_steps": 3, "partner_antrag": "ILS Antragstellung", "partner_kp": None, "partner_wb": None},

        {"email": "dr.silva@gerdoctor.de", "name": "Dr. Maria Silva", "pw": "Demo123!",
         "form": {"name": "Silva", "first_name": "Maria", "phone": "+49 157 5678901", "address": "Marienplatz 8, 80331 München", "field_of_study": "Dermatologie",
                  "documents": []},
         "completed_steps": 2, "partner_antrag": "digiFORT Experts", "partner_kp": None, "partner_wb": None},

        {"email": "dr.ahmed@gerdoctor.de", "name": "Dr. Fatima Ahmed", "pw": "Demo123!",
         "form": {"name": "Ahmed", "first_name": "Fatima", "phone": "+49 162 6789012", "address": "Friedrichstr. 15, 10117 Berlin", "field_of_study": "Neurologie"},
         "completed_steps": 1, "partner_antrag": None, "partner_kp": None, "partner_wb": None},

        {"email": "dr.petrov@gerdoctor.de", "name": "Dr. Ivan Petrov", "pw": "Demo123!",
         "form": {"name": "Petrov", "first_name": "Ivan", "phone": "+49 173 7890123", "address": "Rathausstr. 3, 20095 Hamburg", "field_of_study": "Orthopädie"},
         "completed_steps": 1, "partner_antrag": None, "partner_kp": None, "partner_wb": None},

        {"email": "dr.tanaka@gerdoctor.de", "name": "Dr. Yuki Tanaka", "pw": "Demo123!",
         "form": {"name": "Tanaka", "first_name": "Yuki", "phone": "+49 179 8901234", "address": "Schloßstr. 20, 01067 Dresden", "field_of_study": "Gynäkologie"},
         "completed_steps": 0, "partner_antrag": None, "partner_kp": None, "partner_wb": None},
    ]

    for u in new_users:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            continue
        result = await db.users.insert_one({
            "email": u["email"], "password_hash": hp(u["pw"]), "name": u["name"],
            "role": "user", "profile": {}, "created_at": ago(30)
        })
        uid = str(result.inserted_id)
        completed = u["completed_steps"]

        for s in steps:
            order = s["order"]
            sid = str(s["_id"])
            step_type = s["step_type"]

            if order <= completed:
                # Completed step
                data = {}
                if order == 1:
                    data = u.get("form", {})
                elif step_type in ("partner_selection", "partner_multiselection"):
                    tag = s.get("filter_tag", "")
                    pid = None
                    if tag == "Antragstellung" and u.get("partner_antrag"):
                        pid = partner_ids.get(u["partner_antrag"])
                    elif tag == "Kenntnisprüfung" and u.get("partner_kp"):
                        pid = partner_ids.get(u["partner_kp"])
                    elif tag == "Weiterbildung" and u.get("partner_wb"):
                        pid = partner_ids.get(u["partner_wb"])
                    if pid:
                        pname = [k for k, v in partner_ids.items() if v == pid]
                        data = {"selected_partner_id": pid, "selected_partner_name": pname[0] if pname else ""}
                        # Create partner submission
                        await db.partner_submissions.update_one(
                            {"user_id": uid, "partner_id": pid},
                            {"$set": {"user_email": u["email"], "user_name": u["name"], "data": data, "status": "submitted", "updated_at": now()}},
                            upsert=True
                        )
                        existing_sub = await db.partner_submissions.find_one({"user_id": uid, "partner_id": pid})
                        if existing_sub and "id" not in existing_sub:
                            import uuid
                            await db.partner_submissions.update_one({"_id": existing_sub["_id"]}, {"$set": {"id": str(uuid.uuid4()), "created_at": ago(25 - order)}})

                completed_at = ago(25 - order)
                await db.user_progress.insert_one({
                    "user_id": uid, "step_id": sid, "status": "completed", "data": data,
                    "started_at": ago(26 - order), "completed_at": completed_at,
                    "created_at": ago(26 - order)
                })
            elif order == completed + 1:
                # In progress (current step)
                await db.user_progress.insert_one({
                    "user_id": uid, "step_id": sid, "status": "in_progress", "data": {},
                    "started_at": ago(1), "created_at": ago(1)
                })
            else:
                # Pending
                await db.user_progress.insert_one({
                    "user_id": uid, "step_id": sid, "status": "pending", "data": {},
                    "created_at": now()
                })

        print(f"  Created {u['name']} ({u['email']}) - {completed}/{len(steps)} steps completed")

    # Clean stale submissions for kept users that reference deleted partners
    all_partner_ids = set(partner_ids.values())
    await db.partner_submissions.delete_many({"partner_id": {"$nin": list(all_partner_ids)}})

    print("\nDone! Summary:")
    user_count = await db.users.count_documents({})
    partner_count = await db.partners.count_documents({})
    progress_count = await db.user_progress.count_documents({})
    sub_count = await db.partner_submissions.count_documents({})
    print(f"  Users: {user_count}, Partners: {partner_count}, Progress: {progress_count}, Submissions: {sub_count}")

    client.close()

asyncio.run(run())
