"""Generate 100 demo users distributed across the journey with diverse decisions.

Distribution (deterministic via seeded RNG so re-runs yield the same dataset):
  • ~5 users at every milestone block (5/9/13/17/20/24) and "in_progress" for
    decisions, uploads, partner_selections in between → covers all states.
  • Random anerkennungsstatus (which auto-completes some blocks).
  • Random decision per block ('upload' or 'partner', for Jobangebote
    'selbst' or 'partner_nutzen').
  • Upload path: the upload step is marked completed with dummy `documents`
    so milestone auto-completes.
  • Partner path: partner_submission is created so the partner sees the user.

Run: python3 /app/backend/seed_100_demo_users.py
"""
import asyncio
import os
import random
import bcrypt
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

random.seed(42)
NOW = datetime.now(timezone.utc)


# Realistic-sounding test names (deterministic — seeded RNG draws from these)
FIRST_NAMES = [
    "Maria", "Ahmed", "Yuki", "Liam", "Aisha", "Carlos", "Anya", "Hassan",
    "Sofia", "Raj", "Chen", "Olga", "Diego", "Fatima", "Ibrahim", "Lin",
    "Marek", "Nadia", "Pavel", "Priya", "Samir", "Elena", "Tom", "Wei",
    "Nora", "Omar", "Yara", "Ezgi", "Lucas", "Mei", "Yusuf", "Tariq",
    "Astrid", "Bashir", "Catalina", "Dimitri", "Esmeralda", "Faisal",
    "Gabriela", "Hiroshi", "Iris", "Jamal", "Kira", "Leon", "Maja", "Niko",
]
LAST_NAMES = [
    "Hassan", "Tanaka", "Müller", "Singh", "Kim", "Garcia", "Petrov",
    "Yılmaz", "Schmidt", "Chen", "Rossi", "Nguyen", "Okafor", "Silva",
    "Kowalski", "Sato", "Lopez", "Ali", "Becker", "Fischer", "Weber",
    "Hofmann", "Schäfer", "Bauer", "Köhler", "Lehmann", "Walter", "Mayer",
    "Frank", "Berg", "Krüger", "Sanchez", "Martins", "Park", "Liu", "Wang",
    "Zhang", "Iqbal", "Patel", "Khan",
]

ANERKENNUNGSSTATUS_OPTIONS = [
    "Die Approbation ist beantragt",
    "Die Fachsprachenprüfung Medizin ist geplant",
    "Die Fachsprachenprüfung Medizin ist abgeschlossen",
    "Die Gleichwertigkeitsprüfung wurde geplant",
    "Die Kenntnisprüfung wurde abgeschlossen",
]
FIELDS_OF_STUDY = ["Innere Medizin", "Chirurgie", "Pädiatrie", "Allgemeinmedizin",
                   "Dermatologie", "Neurologie", "Orthopädie", "Gynäkologie", "Psychiatrie"]
BUNDESLAENDER = ["Berlin", "Bayern", "Hamburg", "Hessen", "Sachsen",
                 "Niedersachsen", "Nordrhein-Westfalen", "Baden-Württemberg"]


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()


# ----------------------------------------------------------------------------
def progress_doc(user_id, step_id, step_order, status="completed", data=None,
                 days_ago=0):
    when = (NOW - timedelta(days=days_ago)).isoformat()
    doc = {
        "user_id": str(user_id),
        "step_id": str(step_id),
        "step_order": step_order,
        "status": status,
        "data": data or {},
        "created_at": when,
        "updated_at": when,
        "started_at": when,
    }
    if status == "completed":
        doc["completed_at"] = when
    return doc


# (decision_order, upload_order_or_None, partner_or_multi_step_order, milestone_order)
BLOCKS = [
    (2, 3, 4, 5, "Antragstellung Approbation", False),
    (6, 7, 8, 9, "Fachsprachenprüfung", False),
    (10, 11, 12, 13, "Gleichwertigkeitsprüfung", False),
    (14, 15, 16, 17, "Kenntnisprüfung", False),
    (18, None, 19, 20, "Jobangebote", True),  # multi
    (21, 22, 23, 24, "Weiterbildung", False),
]


# Nice "stage" archetype each user is shaped into. We pick one per user.
STAGES = [
    "fresh",                    # only registered, nothing done
    "stammdaten_only",          # step 1 done
    "block1_decision",          # at block-1 decision in_progress
    "block1_upload_inprogress", # picked upload, hasn't uploaded yet
    "block1_milestone_waiting", # uploaded, waiting for partner-side completion (rare for upload)
    "block1_partner_waiting",   # picked partner, waiting
    "block1_done",              # whole block 1 complete
    "block2_done",
    "block3_done",
    "block4_done",
    "block5_done",
    "almost_done",              # blocks 1-5 done, in block 6
    "fully_done",               # everything completed
]


async def main():
    # Collect blueprints
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    step_by_order = {s["order"]: s for s in steps}
    partners = await db.partners.find({"is_active": True}).to_list(100)
    partners_by_tag = {}
    for p in partners:
        for t in (p.get("tags") or []):
            partners_by_tag.setdefault(t, []).append(p)

    pw_hash = hash_password("Demo123!")

    target_count = 100
    inserted = 0

    for i in range(target_count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        # Build deterministic email
        email = f"demo{i+1:03d}-{last.lower().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')}@chrizz1001.de"
        if await db.users.find_one({"email": email}):
            continue

        stage = random.choice(STAGES)
        anerkennungs = random.choice(ANERKENNUNGSSTATUS_OPTIONS)
        field = random.choice(FIELDS_OF_STUDY)
        bundesland = random.choice(BUNDESLAENDER)

        user_doc = {
            "name": f"Dr. {first} {last}",
            "email": email,
            "password_hash": pw_hash,
            "role": "user",
            "is_active": True,
            "created_at": (NOW - timedelta(days=random.randint(7, 240))).isoformat(),
            "notification_preferences": {
                "email_on_step_enter": True,
                "email_on_step_edit": False,
                "email_on_step_leave": True,
            },
        }
        result = await db.users.insert_one(user_doc)
        user_id = result.inserted_id

        progress = []

        # --- Step 1 (Stammdaten)
        if stage != "fresh":
            progress.append(progress_doc(
                user_id, step_by_order[1]["_id"], 1,
                status="completed",
                data={
                    "first_name": first, "name": last,
                    "date_of_birth": f"{random.randint(1970, 1995)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                    "phone": f"+49 {random.randint(150, 179)} {random.randint(1000000, 9999999)}",
                    "address": f"{random.choice(['Hauptstr.', 'Goethestr.', 'Lindenweg', 'Dorfstr.'])} {random.randint(1, 99)}, {random.randint(10000, 90000)} {bundesland}",
                    "anerkennungsstatus": anerkennungs,
                    "anerkennungsverfahren_bundesland": bundesland,
                    "fachrichtung_praktiziert": field,
                    "fachrichtung_gewuenscht": field,
                    "field_of_study": field,
                },
                days_ago=random.randint(5, 60),
            ))

        # Decide which blocks to fully complete, partial, or skip.
        # Map stage → number of blocks fully completed (decision+upload/partner+milestone)
        n_done_map = {
            "fresh": 0, "stammdaten_only": 0, "block1_decision": 0,
            "block1_upload_inprogress": 0, "block1_milestone_waiting": 0,
            "block1_partner_waiting": 0, "block1_done": 1,
            "block2_done": 2, "block3_done": 3, "block4_done": 4, "block5_done": 5,
            "almost_done": 5, "fully_done": 6,
        }
        n_done = n_done_map.get(stage, 0)

        for blk_idx, (dec_o, up_o, ps_o, ms_o, blk_name, is_multi) in enumerate(BLOCKS):
            block_pos = blk_idx + 1
            if block_pos <= n_done:
                # fully complete this block
                decision_value = "selbst" if is_multi else random.choice(["upload", "partner"])
                if is_multi:
                    decision_value = random.choice(["selbst", "partner_nutzen"])
                progress.append(progress_doc(
                    user_id, step_by_order[dec_o]["_id"], dec_o,
                    status="completed", data={"decision": decision_value},
                    days_ago=random.randint(2, 40)))
                if decision_value == "upload" and up_o is not None:
                    progress.append(progress_doc(
                        user_id, step_by_order[up_o]["_id"], up_o,
                        status="completed",
                        data={"documents": [{"file_id": f"demo-{user_id}-{up_o}",
                                              "filename": "approbation_dokumente.pdf",
                                              "uploaded_at": NOW.isoformat()}]},
                        days_ago=random.randint(1, 30)))
                elif decision_value in ("partner", "partner_nutzen") and ps_o is not None:
                    # find a partner with the right tag
                    pts = partners_by_tag.get(blk_name, [])
                    if pts:
                        chosen = random.sample(pts, k=min(2 if is_multi else 1, len(pts)))
                        ids = [str(p["_id"]) for p in chosen]
                        names = [p["name"] for p in chosen]
                        data = ({"selected_partner_ids": ids, "selected_partner_names": names}
                                if is_multi else
                                {"selected_partner_id": ids[0], "selected_partner_name": names[0]})
                        progress.append(progress_doc(
                            user_id, step_by_order[ps_o]["_id"], ps_o,
                            status="completed", data=data,
                            days_ago=random.randint(1, 20)))
                        # Create partner_submission
                        for cp, cid in zip(chosen, ids):
                            await db.partner_submissions.insert_one({
                                "user_id": str(user_id),
                                "user_email": email,
                                "user_name": user_doc["name"],
                                "partner_id": cid,
                                "data": {"step_order": ps_o, "field_of_study": field,
                                         "bundesland": bundesland},
                                "status": "submitted",
                                "partner_work_completed": True,
                                "completed_at": (NOW - timedelta(days=random.randint(1, 15))).isoformat(),
                                "created_at": (NOW - timedelta(days=random.randint(2, 25))).isoformat(),
                                "id": f"sub-{user_id}-{cid}",
                            })
                # Milestone completed
                progress.append(progress_doc(
                    user_id, step_by_order[ms_o]["_id"], ms_o,
                    status="completed", data={"completed_by": "auto" if decision_value in ("upload", "selbst") else "partner"},
                    days_ago=random.randint(0, 15)))
            elif block_pos == n_done + 1:
                # partial state for the "active" block based on stage
                if stage == "block1_decision":
                    progress.append(progress_doc(
                        user_id, step_by_order[dec_o]["_id"], dec_o,
                        status="in_progress", data={}, days_ago=1))
                elif stage in ("block1_upload_inprogress",):
                    progress.append(progress_doc(
                        user_id, step_by_order[dec_o]["_id"], dec_o,
                        status="completed", data={"decision": "upload"}, days_ago=2))
                    if up_o:
                        progress.append(progress_doc(
                            user_id, step_by_order[up_o]["_id"], up_o,
                            status="in_progress", data={}, days_ago=1))
                elif stage == "block1_partner_waiting":
                    progress.append(progress_doc(
                        user_id, step_by_order[dec_o]["_id"], dec_o,
                        status="completed", data={"decision": "partner"}, days_ago=3))
                    pts = partners_by_tag.get(blk_name, [])
                    if pts and ps_o:
                        chosen = pts[0]
                        cid = str(chosen["_id"])
                        progress.append(progress_doc(
                            user_id, step_by_order[ps_o]["_id"], ps_o,
                            status="completed",
                            data={"selected_partner_id": cid,
                                  "selected_partner_name": chosen["name"]},
                            days_ago=2))
                        await db.partner_submissions.insert_one({
                            "user_id": str(user_id), "user_email": email,
                            "user_name": user_doc["name"], "partner_id": cid,
                            "data": {"step_order": ps_o, "field_of_study": field,
                                     "bundesland": bundesland},
                            "status": "submitted", "partner_work_completed": False,
                            "created_at": (NOW - timedelta(days=2)).isoformat(),
                            "id": f"sub-{user_id}-{cid}",
                        })
                elif stage == "block1_milestone_waiting":
                    progress.append(progress_doc(
                        user_id, step_by_order[dec_o]["_id"], dec_o,
                        status="completed", data={"decision": "upload"}, days_ago=4))
                    if up_o:
                        progress.append(progress_doc(
                            user_id, step_by_order[up_o]["_id"], up_o,
                            status="completed",
                            data={"documents": [{"file_id": f"demo-{user_id}-{up_o}",
                                                  "filename": "docs.pdf"}]}, days_ago=2))

        if progress:
            await db.user_progress.insert_many(progress)
        inserted += 1
        if inserted % 25 == 0:
            print(f"  …{inserted} users seeded")

    print(f"\nDone. Inserted {inserted} demo users.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
