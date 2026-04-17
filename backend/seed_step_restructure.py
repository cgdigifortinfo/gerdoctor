"""
Step restructuring: Rename steps, add Gleichwertigkeitspruefung steps, create partners, add FaMed link.
"""
import asyncio, os, uuid
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone
import bcrypt

LOGO_MEDICAL = 'https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/6cecee740efb45c2d26aff2bfd6a5b584d1ce68a3f00e1ba82f41fa1f355c8b3.png'
LOGO_HABS = 'https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/59c730dae718e5a79fb55651ef6b1ed654b341268c44838ee9e01774876a4d13.png'

def now():
    return datetime.now(timezone.utc).isoformat()

def hp(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

async def run():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]

    # ========== 1. RENAME STEPS ==========
    print("=== Renaming steps ===")

    r = await db.steps.update_one(
        {"title": "Service Antragstellung"},
        {"$set": {"title": "Antragstellung Approbation"}}
    )
    print(f'  "Service Antragstellung" -> "Antragstellung Approbation": modified={r.modified_count}')

    r = await db.steps.update_one(
        {"title": "Meilenstein Antragstellung"},
        {"$set": {"title": "Uebersicht Antragstellung Approbation"}}
    )
    print(f'  "Meilenstein Antragstellung" -> "Uebersicht Antragstellung Approbation": modified={r.modified_count}')

    # ========== 2. ADD FaMed LINK ==========
    print("\n=== Adding FaMed link ===")
    famed = await db.steps.find_one({"title": "FaMed"})
    if famed:
        await db.steps.update_one(
            {"_id": famed["_id"]},
            {"$set": {
                "description": "Informationen zur Fachsprachenpruefung Medizin (FaMed). Weitere Details unter: https://famed-test.de/",
                "content": "<p>Die Fachsprachenpruefung Medizin (FaMed) ist ein wichtiger Schritt auf Ihrem Weg zur Approbation.</p><p><a href=\"https://famed-test.de/\" target=\"_blank\" rel=\"noopener noreferrer\">Weitere Informationen auf famed-test.de</a></p>",
                "link_url": "https://famed-test.de/",
                "link_label": "famed-test.de besuchen"
            }}
        )
        print(f'  FaMed updated with link to famed-test.de')
    else:
        print('  FaMed step not found!')

    # ========== 3. ADD GLEICHWERTIGKEITSPRUEFUNG STEPS ==========
    print("\n=== Adding Gleichwertigkeitspruefung steps ===")

    # Get current steps to find the right insertion point
    all_steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    step_orders = {s["title"]: s["order"] for s in all_steps}

    # Find FaMed order (should be 4) and Service Kenntnisprüfung order (should be 5)
    famed_order = step_orders.get("FaMed", 4)
    kp_order = step_orders.get("Service Kenntnisprüfung")
    if kp_order is None:
        print("  ERROR: Service Kenntnisprüfung not found")
    else:
        print(f'  FaMed at order={famed_order}, Kenntnisprüfung at order={kp_order}')

    # We need to insert 2 new steps between FaMed and Service Kenntnisprüfung
    # Shift all steps from Service Kenntnisprüfung onwards by +2
    shift_from = kp_order
    steps_to_shift = [s for s in all_steps if s["order"] >= shift_from]
    for s in sorted(steps_to_shift, key=lambda x: -x["order"]):  # shift from highest first
        new_order = s["order"] + 2
        await db.steps.update_one({"_id": s["_id"]}, {"$set": {"order": new_order}})
        print(f'  Shifted "{s["title"]}" from order {s["order"]} to {new_order}')

    # Copy Kenntnisprüfung step structure for Gleichwertigkeitspruefung
    kp_step = await db.steps.find_one({"title": "Service Kenntnisprüfung"})
    kp_milestone = None
    for s in all_steps:
        if s["title"] == "Meilenstein Kenntnisprüfung":
            kp_milestone = s
            break

    # Insert "Gleichwertigkeitspruefung" (partner_selection) at famed_order + 1
    gp_order = famed_order + 1
    existing_gp = await db.steps.find_one({"title": "Gleichwertigkeitspruefung"})
    if not existing_gp:
        gp_doc = {
            "title": "Gleichwertigkeitspruefung",
            "description": "Waehlen Sie Ihren Partner fuer die Gleichwertigkeitspruefung.",
            "step_type": "partner_selection",
            "order": gp_order,
            "filter_tag": "Gleichwertigkeitspruefung",
            "fields": kp_step.get("fields", []) if kp_step else [],
            "conditions": [],
            "is_active": True,
            "skippable": True,
            "skip_label": "Ueberspringen",
            "created_at": now()
        }
        r = await db.steps.insert_one(gp_doc)
        print(f'  Created "Gleichwertigkeitspruefung" at order {gp_order} (id={r.inserted_id})')
    else:
        print(f'  "Gleichwertigkeitspruefung" already exists')

    # Insert "Uebersicht Gleichwertigkeitspruefung" (milestone) at famed_order + 2
    gp_ms_order = famed_order + 2
    existing_gp_ms = await db.steps.find_one({"title": "Uebersicht Gleichwertigkeitspruefung"})
    if not existing_gp_ms:
        gp_ms_doc = {
            "title": "Uebersicht Gleichwertigkeitspruefung",
            "description": "Uebersicht und Status Ihrer Gleichwertigkeitspruefung.",
            "step_type": "milestone",
            "order": gp_ms_order,
            "fields": [],
            "conditions": [],
            "duration_value": kp_milestone.get("duration_value", 3) if kp_milestone else 3,
            "duration_unit": kp_milestone.get("duration_unit", "months") if kp_milestone else "months",
            "is_active": True,
            "email_on_leave": True,
            "created_at": now()
        }
        r = await db.steps.insert_one(gp_ms_doc)
        print(f'  Created "Uebersicht Gleichwertigkeitspruefung" at order {gp_ms_order} (id={r.inserted_id})')
    else:
        print(f'  "Uebersicht Gleichwertigkeitspruefung" already exists')

    # ========== 4. CREATE GLEICHWERTIGKEITSPRUEFUNG PARTNERS ==========
    print("\n=== Creating Gleichwertigkeitspruefung partners ===")
    gp_partners = [
        {
            "name": "IQB Pruefungszentrum",
            "description": "Institut fuer Qualifizierung und Berufszulassung. Vorbereitung und Durchfuehrung der Gleichwertigkeitspruefung.",
            "category": "Gleichwertigkeitspruefung",
            "tags": ["Gleichwertigkeitspruefung"],
            "website": "https://iqb-pruefung.de",
            "contact_email": "info@iqb-pruefung.de",
            "logo_url": LOGO_HABS,
            "is_active": True,
        },
        {
            "name": "MedAkademie Berlin",
            "description": "Medizinische Akademie fuer internationale Aerzte. Intensive Vorbereitung auf die Gleichwertigkeitspruefung.",
            "category": "Gleichwertigkeitspruefung",
            "tags": ["Gleichwertigkeitspruefung"],
            "website": "https://medakademie-berlin.de",
            "contact_email": "info@medakademie-berlin.de",
            "logo_url": LOGO_MEDICAL,
            "is_active": True,
        },
    ]
    for p in gp_partners:
        existing = await db.partners.find_one({"name": p["name"]})
        if existing:
            print(f'  "{p["name"]}" already exists')
            continue
        r = await db.partners.insert_one({**p, "created_at": now()})
        pid = str(r.inserted_id)
        print(f'  Created "{p["name"]}" (id={pid})')

    # ========== 5. CREATE PROGRESS RECORDS FOR NEW STEPS ==========
    print("\n=== Creating progress records for new steps ===")
    new_steps = await db.steps.find({"title": {"$in": ["Gleichwertigkeitspruefung", "Uebersicht Gleichwertigkeitspruefung"]}}).to_list(10)
    all_users = await db.users.find({"role": "user"}).to_list(100)
    for u in all_users:
        uid = str(u["_id"])
        for ns in new_steps:
            nsid = str(ns["_id"])
            existing = await db.user_progress.find_one({"user_id": uid, "step_id": nsid})
            if not existing:
                await db.user_progress.insert_one({
                    "user_id": uid, "step_id": nsid,
                    "status": "pending", "data": {},
                    "created_at": now()
                })
        # print(f'  {u["email"]}: progress records created')

    # ========== SUMMARY ==========
    print("\n=== FINAL STEP ORDER ===")
    final_steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    for s in final_steps:
        dur = s.get("duration_value", 0)
        print(f'  {s["order"]:2d}. {s["title"]:50s} | type={s.get("step_type",""):25s} | tag={s.get("filter_tag",""):25s} | dur={dur}')

    partners_count = await db.partners.count_documents({})
    print(f'\nTotal partners: {partners_count}')

    client.close()

asyncio.run(run())
