"""
Seed migration v2: Add Praxis partners for each Dr., partner-role users for all partners.
Additive - does NOT delete existing data.
"""
import asyncio, os, bcrypt, uuid
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()


def hp(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def now():
    return datetime.now(timezone.utc).isoformat()

def ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def run():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # Build lookup of existing partners and users
    all_partners = await db.partners.find().to_list(100)
    partner_by_name = {p["name"]: p for p in all_partners}
    all_users = await db.users.find().to_list(100)
    user_by_email = {u["email"]: u for u in all_users}

    # Dr. users and their practice assignments
    praxis_data = [
        {
            "dr_email": "dr.schmidt@chrizz1001.de",
            "praxis_name": "Hausarztpraxis am Marienplatz",
            "praxis_desc": "Allgemeinmedizinische Praxis mit Schwerpunkt hausaerztliche Versorgung und Praevention. Moderne Diagnostik in zentraler Lage.",
            "praxis_cat": "Allgemeinmedizin",
            "praxis_tags": ["Praxis"],
            "praxis_website": "https://hausarztpraxis-marienplatz.de",
            "praxis_address": "Marienplatz 4, 80331 Muenchen",
            "praxis_phone": "+49 89 12345678",
            "praxis_user_email": "empfang@hausarztpraxis-marienplatz.de",
            "praxis_user_name": "Susanne Berger",
        },
        {
            "dr_email": "dr.yilmaz@chrizz1001.de",
            "praxis_name": "Internistische Praxis Rheinblick",
            "praxis_desc": "Facharztpraxis fuer Innere Medizin. Kardiologie, Gastroenterologie und Diabetologie unter einem Dach.",
            "praxis_cat": "Innere Medizin",
            "praxis_tags": ["Praxis"],
            "praxis_website": "https://praxis-rheinblick.de",
            "praxis_address": "Rheinuferstr. 22, 40212 Duesseldorf",
            "praxis_phone": "+49 211 9876543",
            "praxis_user_email": "verwaltung@praxis-rheinblick.de",
            "praxis_user_name": "Monika Schaefer",
        },
        {
            "dr_email": "dr.chen@chrizz1001.de",
            "praxis_name": "Chirurgische Gemeinschaftspraxis Koenigstrasse",
            "praxis_desc": "Ueberregionale chirurgische Praxis. Schwerpunkte: Viszeralchirurgie, Unfallchirurgie und ambulantes Operieren.",
            "praxis_cat": "Chirurgie",
            "praxis_tags": ["Praxis"],
            "praxis_website": "https://chirurgie-koenigstrasse.de",
            "praxis_address": "Koenigstr. 28, 70173 Stuttgart",
            "praxis_phone": "+49 711 4567890",
            "praxis_user_email": "office@chirurgie-koenigstrasse.de",
            "praxis_user_name": "Petra Hoffmann",
        },
        {
            "dr_email": "dr.kumar@chrizz1001.de",
            "praxis_name": "Kinderarztpraxis Zeilnest",
            "praxis_desc": "Kinderaerztliche Gemeinschaftspraxis mit Schwerpunkt Vorsorge, Impfberatung und Entwicklungsdiagnostik.",
            "praxis_cat": "Paediatrie",
            "praxis_tags": ["Praxis"],
            "praxis_website": "https://kinderarzt-zeilnest.de",
            "praxis_address": "Zeil 55, 60313 Frankfurt am Main",
            "praxis_phone": "+49 69 3456789",
            "praxis_user_email": "anmeldung@kinderarzt-zeilnest.de",
            "praxis_user_name": "Claudia Weber",
        },
        {
            "dr_email": "dr.silva@chrizz1001.de",
            "praxis_name": "Hautarztpraxis am Englischen Garten",
            "praxis_desc": "Dermatologische Praxis mit Schwerpunkt aesthetische Dermatologie, Hautkrebsvorsorge und Allergologie.",
            "praxis_cat": "Dermatologie",
            "praxis_tags": ["Praxis"],
            "praxis_website": "https://hautarzt-englischer-garten.de",
            "praxis_address": "Leopoldstr. 77, 80802 Muenchen",
            "praxis_phone": "+49 89 2345678",
            "praxis_user_email": "rezeption@hautarzt-eg.de",
            "praxis_user_name": "Nicole Bauer",
        },
        {
            "dr_email": "dr.ahmed@chrizz1001.de",
            "praxis_name": "Neurologisches Zentrum Friedrichstrasse",
            "praxis_desc": "Facharztpraxis fuer Neurologie und Psychiatrie. Diagnostik und Therapie neurologischer Erkrankungen inkl. EEG und Nervenleitungsmessung.",
            "praxis_cat": "Neurologie",
            "praxis_tags": ["Praxis"],
            "praxis_website": "https://neurologie-friedrichstrasse.de",
            "praxis_address": "Friedrichstr. 15, 10117 Berlin",
            "praxis_phone": "+49 30 5678901",
            "praxis_user_email": "praxis@neurologie-friedrichstrasse.de",
            "praxis_user_name": "Kathrin Mueller",
        },
        {
            "dr_email": "dr.petrov@chrizz1001.de",
            "praxis_name": "Orthopaedische Praxis Elbblick",
            "praxis_desc": "Facharztpraxis fuer Orthopaedie und Sportmedizin. Konservative und operative Behandlung des Bewegungsapparates.",
            "praxis_cat": "Orthopaedie",
            "praxis_tags": ["Praxis"],
            "praxis_website": "https://orthopaedie-elbblick.de",
            "praxis_address": "Elbchaussee 12, 22765 Hamburg",
            "praxis_phone": "+49 40 6789012",
            "praxis_user_email": "info@orthopaedie-elbblick.de",
            "praxis_user_name": "Andrea Fischer",
        },
        {
            "dr_email": "dr.tanaka@chrizz1001.de",
            "praxis_name": "Frauenarztpraxis an der Frauenkirche",
            "praxis_desc": "Gynaekologische Praxis mit Schwerpunkt Schwangerenvorsorge, Geburtsplanung und Krebsfrueherkennung.",
            "praxis_cat": "Gynaekologie",
            "praxis_tags": ["Praxis"],
            "praxis_website": "https://frauenarzt-frauenkirche.de",
            "praxis_address": "An der Frauenkirche 9, 01067 Dresden",
            "praxis_phone": "+49 351 7890123",
            "praxis_user_email": "termin@frauenarzt-frauenkirche.de",
            "praxis_user_name": "Sabine Richter",
        },
    ]

    # Available logos from digifort-experts.de (cycle through for Praxis)
    praxis_logos = [
        "https://digifort-experts.de/wp-content/uploads/2026/02/dreieck.png",
        "https://digifort-experts.de/wp-content/uploads/2026/02/famed.png",
        "https://digifort-experts.de/wp-content/uploads/2026/03/gw.png",
        "https://digifort-experts.de/wp-content/uploads/2025/10/ALTE-invert-small.png",
        "https://digifort-experts.de/wp-content/uploads/2026/02/digiFORT.png",
        "https://digifort-experts.de/wp-content/uploads/2026/02/habs.png",
        "https://digifort-experts.de/wp-content/uploads/2026/02/hc-und-s.png",
        "https://digifort-experts.de/wp-content/uploads/2026/02/interpers.png",
    ]

    print("========== CREATING PRAXIS PARTNERS ==========")
    for i, pd in enumerate(praxis_data):
        dr_user = user_by_email.get(pd["dr_email"])
        if not dr_user:
            print(f"  SKIP: Dr. user {pd['dr_email']} not found")
            continue

        dr_uid = str(dr_user["_id"])

        # Check if Praxis already exists
        existing_praxis = await db.partners.find_one({"name": pd["praxis_name"]})
        if existing_praxis:
            praxis_id = str(existing_praxis["_id"])
            print(f"  EXISTS: {pd['praxis_name']} (id={praxis_id})")
        else:
            result = await db.partners.insert_one({
                "name": pd["praxis_name"],
                "description": pd["praxis_desc"],
                "category": pd["praxis_cat"],
                "tags": pd["praxis_tags"],
                "website": pd["praxis_website"],
                "contact_email": pd["praxis_user_email"],
                "phone": pd["praxis_phone"],
                "address": pd["praxis_address"],
                "logo_url": praxis_logos[i % len(praxis_logos)],
                "is_active": True,
                "created_at": ago(60),
            })
            praxis_id = str(result.inserted_id)
            print(f"  CREATED: {pd['praxis_name']} (id={praxis_id})")

        # Create partner-role user for this Praxis (if not exists)
        existing_pu = user_by_email.get(pd["praxis_user_email"])
        if existing_pu:
            print(f"    Partner user {pd['praxis_user_email']} already exists")
        else:
            pu_result = await db.users.insert_one({
                "email": pd["praxis_user_email"],
                "password_hash": hp("Partner123!"),
                "name": pd["praxis_user_name"],
                "role": "partner",
                "partner_id": praxis_id,
                "profile": {},
                "created_at": ago(60),
            })
            # Also store user_id on the partner doc
            await db.partners.update_one(
                {"_id": ObjectId(praxis_id)},
                {"$set": {"user_id": str(pu_result.inserted_id)}}
            )
            print(f"    Partner user: {pd['praxis_user_name']} ({pd['praxis_user_email']})")

        # Create partner_submission so Dr. shows up in Praxis dashboard
        existing_sub = await db.partner_submissions.find_one({
            "user_id": dr_uid, "partner_id": praxis_id
        })
        if not existing_sub:
            await db.partner_submissions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": dr_uid,
                "partner_id": praxis_id,
                "user_email": pd["dr_email"],
                "user_name": dr_user["name"],
                "data": {"source": "employer"},
                "status": "submitted",
                "created_at": ago(28),
                "updated_at": now(),
            })
            print(f"    Linked {pd['dr_email']} -> {pd['praxis_name']}")

    # ========== SERVICE PARTNER USERS ==========
    print("\n========== CREATING SERVICE PARTNER USERS ==========")
    service_partner_users = [
        {"partner_name": "ILS2", "email": "beratung@ils-kp.de", "name": "Thomas Klein", "pw": "Partner123!"},
        {"partner_name": "ILS3", "email": "beratung@ils-wb.de", "name": "Sandra Braun", "pw": "Partner123!"},
        {"partner_name": "digiFORT Experts", "email": "partner@digifort-experts.de", "name": "Martin Schulz", "pw": "Partner123!"},
        {"partner_name": "HABS e.V.", "email": "partner@habs-ev.de", "name": "Maria Theresia Franz-Goetz", "pw": "Partner123!"},
        {"partner_name": "HC&S Personaldienstleistungen", "email": "partner@hc-und-s.de", "name": "Elitsa Seidel", "pw": "Partner123!"},
        {"partner_name": "Lingoda", "email": "partner@lingoda.com", "name": "Felix Neumann", "pw": "Partner123!"},
        {"partner_name": "InterPers", "email": "partner@interpers.de", "name": "Julia Krause", "pw": "Partner123!"},
    ]

    for spu in service_partner_users:
        partner = partner_by_name.get(spu["partner_name"])
        if not partner:
            print(f"  SKIP: Partner '{spu['partner_name']}' not found")
            continue

        pid = str(partner["_id"])

        # Check if already has a linked partner user
        existing_linked = await db.users.find_one({"partner_id": pid})
        if existing_linked:
            print(f"  EXISTS: {spu['partner_name']} already has user {existing_linked['email']}")
            continue

        # Check if email already exists
        existing_user = await db.users.find_one({"email": spu["email"]})
        if existing_user:
            print(f"  EXISTS: {spu['email']} already exists")
            continue

        result = await db.users.insert_one({
            "email": spu["email"],
            "password_hash": hp(spu["pw"]),
            "name": spu["name"],
            "role": "partner",
            "partner_id": pid,
            "profile": {},
            "created_at": ago(45),
        })
        await db.partners.update_one(
            {"_id": ObjectId(pid)},
            {"$set": {"user_id": str(result.inserted_id)}}
        )
        print(f"  CREATED: {spu['name']} ({spu['email']}) -> {spu['partner_name']}")

    # ========== FINAL SUMMARY ==========
    print("\n========== FINAL STATE ==========")
    all_p = await db.partners.find().to_list(100)
    for p in all_p:
        pid = str(p["_id"])
        linked = await db.users.find_one({"partner_id": pid}, {"email": 1, "name": 1})
        subs = await db.partner_submissions.count_documents({"partner_id": pid})
        linked_info = f"{linked['name']} ({linked['email']})" if linked else "KEIN USER"
        print(f"  {p['name']:45s} | {p.get('category',''):20s} | tags={str(p.get('tags',[])):25s} | user={linked_info:45s} | subs={subs}")

    user_count = await db.users.count_documents({})
    partner_count = await db.partners.count_documents({})
    sub_count = await db.partner_submissions.count_documents({})
    print(f"\n  Gesamt: {user_count} Users, {partner_count} Partners, {sub_count} Submissions")

    client.close()

asyncio.run(run())
