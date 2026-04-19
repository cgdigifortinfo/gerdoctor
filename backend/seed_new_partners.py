"""
Add new partners (FIA, InterPers update, FAMED, PraxisConnect, digiFORT keep) and clean DB.
"""
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

LOGO_FIA = "https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/440df7b005b6ca361bd196f3ae756d92de842abc4923305935c050e6299b4a29.png"
LOGO_FAMED = "https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/7959af96b6af0398f50abe6e25fbce99fd8823dd43831b7261e6979408a1e2ce.png"
LOGO_PRAXISCONNECT = "https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/e6bd4623c59c52bfb11cf8f8865cc891fea715536212d7be3e05f0c198255505.png"
LOGO_INTERPERS = "https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/e4f243fcb50a88e63599e19ddd9707e1465278f63d6fe2202466886e9576981a.png"
LOGO_DIGIFORT = "https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/35ecd1f2165a6eb9a9db9712feae6f405d0a0e21ea23eb3d8ec0e04cf70c3d7c.png"

def now():
    return datetime.now(timezone.utc).isoformat()

async def run():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]

    # ========== 1. ADD/UPDATE PARTNERS ==========
    new_partners = [
        {
            "name": "FIA Academy",
            "description": "Professionelle Vorbereitung auf Fachsprachenpruefung und Kenntnisspruefung. Kurse in Berlin, Essen, Frankfurt, Freiburg, Hannover, Heidelberg, Landshut, Mainz und online.",
            "category": "Kenntnisprüfung",
            "tags": ["Kenntnisprüfung", "Antragstellung"],
            "website": "https://www.fia-academy.de/de",
            "contact_email": "info@fia-academy.de",
            "logo_url": LOGO_FIA,
            "is_active": True,
        },
        {
            "name": "FaMed",
            "description": "Der schnellste und beste Weg zur Fachsprachenpruefung Medizin und Zahnmedizin. Unabhaengiges Pruefungszentrum in Mainz. Anerkannt in Rheinland-Pfalz, Bayern, Hessen und weiteren Bundeslaendern.",
            "category": "Antragstellung",
            "tags": ["Antragstellung"],
            "website": "https://famed-test.de/",
            "contact_email": "service@famed-test.de",
            "logo_url": LOGO_FAMED,
            "is_active": True,
        },
        {
            "name": "PraxisConnect",
            "description": "Dein professioneller Partner fuer die Jobsuche im deutschen Gesundheitswesen. Vermittlung von Aerztinnen und Aerzten an Kliniken und Praxen.",
            "category": "Weiterbildung",
            "tags": ["Praxis"],
            "website": "https://www.linkedin.com/company/93809321/",
            "contact_email": "info@praxisconnect.de",
            "logo_url": LOGO_PRAXISCONNECT,
            "is_active": True,
        },
    ]

    print("=== ADDING NEW PARTNERS ===")
    for p in new_partners:
        existing = await db.partners.find_one({"name": p["name"]})
        if existing:
            await db.partners.update_one({"_id": existing["_id"]}, {"$set": p})
            print(f'  Updated: {p["name"]}')
        else:
            await db.partners.insert_one({**p, "created_at": now()})
            print(f'  Created: {p["name"]}')

    # Update InterPers
    print("\n=== UPDATING INTERPERS ===")
    interpers = await db.partners.find_one({"name": "InterPers"})
    if interpers:
        await db.partners.update_one({"_id": interpers["_id"]}, {"$set": {
            "description": "Dein gepruefter Partner fuer Vorbereitung und Antragstellung Approbation. Interdisziplinaere, interkulturelle Personalvermittlung fuer internationale Fachkraefte im Gesundheitswesen.",
            "category": "Antragstellung",
            "tags": ["Antragstellung", "Weiterbildung"],
            "website": "https://interpers.de/",
            "contact_email": "info@interpers.de",
            "logo_url": LOGO_INTERPERS,
        }})
        print(f'  Updated: InterPers')

    # Update digiFORT Experts logo
    print("\n=== UPDATING DIGIFORT LOGO ===")
    digifort = await db.partners.find_one({"name": "digiFORT Experts"})
    if digifort:
        await db.partners.update_one({"_id": digifort["_id"]}, {"$set": {
            "description": "Innovative Loesungen fuer den Fachkraeftemangel im deutschen Gesundheitswesen. Fachsprachenpruefungen und Antragsbearbeitung fuer internationale Aerzte.",
            "logo_url": LOGO_DIGIFORT,
        }})
        print(f'  Updated: digiFORT Experts')

    # ========== 2. CLEAN DATABASE ==========
    print("\n=== CLEANING DATABASE ===")

    # Remove TEST_ users and their data
    test_users = await db.users.find({"email": {"$regex": "^test_", "$options": "i"}}).to_list(100)
    for u in test_users:
        uid = str(u["_id"])
        await db.user_progress.delete_many({"user_id": uid})
        await db.partner_submissions.delete_many({"user_id": uid})
        await db.progress_history.delete_many({"user_id": uid})
        await db.files.delete_many({"user_id": uid})
        await db.users.delete_one({"_id": u["_id"]})
        print(f'  Deleted TEST user: {u["email"]}')

    # Remove orphaned partner submissions (user_id no longer exists)
    all_subs = await db.partner_submissions.find().to_list(10000)
    user_ids = set()
    async for u in db.users.find({}, {"_id": 1}):
        user_ids.add(str(u["_id"]))
    orphaned_subs = 0
    for s in all_subs:
        if s.get("user_id") and s["user_id"] not in user_ids:
            await db.partner_submissions.delete_one({"_id": s["_id"]})
            orphaned_subs += 1
    if orphaned_subs:
        print(f'  Deleted {orphaned_subs} orphaned partner submissions')

    # Remove orphaned progress records (user_id no longer exists)
    all_progress = await db.user_progress.find().to_list(10000)
    orphaned_prog = 0
    for p in all_progress:
        if p.get("user_id") and p["user_id"] not in user_ids:
            await db.user_progress.delete_one({"_id": p["_id"]})
            orphaned_prog += 1
    if orphaned_prog:
        print(f'  Deleted {orphaned_prog} orphaned progress records')

    # Remove orphaned progress history
    all_hist = await db.progress_history.find().to_list(10000)
    orphaned_hist = 0
    for h in all_hist:
        if h.get("user_id") and h["user_id"] not in user_ids:
            await db.progress_history.delete_one({"_id": h["_id"]})
            orphaned_hist += 1
    if orphaned_hist:
        print(f'  Deleted {orphaned_hist} orphaned history records')

    # Remove progress records pointing to deleted/inactive steps
    active_step_ids = set()
    async for s in db.steps.find({"is_active": True}, {"_id": 1}):
        active_step_ids.add(str(s["_id"]))
    orphaned_step_prog = 0
    for p in await db.user_progress.find().to_list(10000):
        if p.get("step_id") and p["step_id"] not in active_step_ids:
            await db.user_progress.delete_one({"_id": p["_id"]})
            orphaned_step_prog += 1
    if orphaned_step_prog:
        print(f'  Deleted {orphaned_step_prog} progress records for inactive steps')

    # Remove partners with no relevant data (old test partners)
    old_test_partners = await db.partners.find({"name": {"$regex": "^TEST_", "$options": "i"}}).to_list(100)
    for p in old_test_partners:
        await db.partners.delete_one({"_id": p["_id"]})
        print(f'  Deleted TEST partner: {p["name"]}')

    # Remove login_attempts collection entries
    await db.login_attempts.delete_many({})
    print('  Cleared login_attempts')

    # ========== 3. SUMMARY ==========
    print("\n=== FINAL STATE ===")
    user_count = await db.users.count_documents({})
    partner_count = await db.partners.count_documents({})
    step_count = await db.steps.count_documents({"is_active": True})
    progress_count = await db.user_progress.count_documents({})
    sub_count = await db.partner_submissions.count_documents({})

    print(f'  Users: {user_count}')
    print(f'  Partners: {partner_count}')
    print(f'  Steps: {step_count}')
    print(f'  Progress records: {progress_count}')
    print(f'  Submissions: {sub_count}')

    print("\n=== ALL PARTNERS ===")
    partners = await db.partners.find().to_list(100)
    for p in sorted(partners, key=lambda x: x.get("name", "")):
        print(f'  {p["name"]:45s} | cat={p.get("category",""):25s} | tags={p.get("tags",[])}')

    print("\n=== ALL USERS ===")
    users = await db.users.find({}, {"email": 1, "role": 1, "name": 1}).to_list(100)
    for u in sorted(users, key=lambda x: (x.get("role",""), x.get("email",""))):
        print(f'  {u["email"]:45s} | {u.get("role",""):8s} | {u.get("name","")}')

    client.close()

asyncio.run(run())
