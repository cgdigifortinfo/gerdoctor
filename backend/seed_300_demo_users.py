"""Re-seed 300 demo users (none fully done) with logical, ordered step
progress + real placeholder file uploads via GridFS-backed object storage.

Step 1 — Cleanup
  • Delete every user with "flowbug" in the email + their progress / submissions
    / progress_history / files.
  • Delete every existing demoNNN-* user + their data so we start from a clean
    baseline.

Step 2 — Generate 300 fresh users
  • All in-progress (NO user reaches the "fully_done" stage).
  • Distributed across stages so the system shows realistic variety.
  • 164 users are explicitly routed through MVZ Gruppe — they pick
    decision=partner on a block whose `filter_tag` is in MVZ's tag set
    ("Fachsprachenprüfung" or "Kenntnisprüfung"), and the partner_submission
    references MVZ Gruppe.
  • Steps are filled in canonical order: Stammdaten → decision → upload OR
    partner-selection → milestone (the milestone auto-completes for upload
    paths after the document arrives, and stays in_progress on partner paths
    until the partner finishes the work).

Run: python3 /app/backend/seed_300_demo_users.py
"""
import asyncio
import base64
import os
import random
import sys
import uuid
import bcrypt
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
from helpers import put_object, APP_NAME  # noqa: E402

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

random.seed(2026)
NOW = datetime.now(timezone.utc)
TOTAL = 300
MVZ_TARGET = 164

RED_1x1_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------------
# Test data pools
FIRST_NAMES = [
    "Maria", "Ahmed", "Yuki", "Liam", "Aisha", "Carlos", "Anya", "Hassan",
    "Sofia", "Raj", "Chen", "Olga", "Diego", "Fatima", "Ibrahim", "Lin",
    "Marek", "Nadia", "Pavel", "Priya", "Samir", "Elena", "Tom", "Wei",
    "Nora", "Omar", "Yara", "Ezgi", "Lucas", "Mei", "Yusuf", "Tariq",
    "Astrid", "Bashir", "Catalina", "Dimitri", "Esmeralda", "Faisal",
    "Gabriela", "Hiroshi", "Iris", "Jamal", "Kira", "Leon", "Maja", "Niko",
    "Otto", "Paula", "Qasim", "Rosa",
]
LAST_NAMES = [
    "Hassan", "Tanaka", "Mueller", "Singh", "Kim", "Garcia", "Petrov",
    "Yilmaz", "Schmidt", "Chen", "Rossi", "Nguyen", "Okafor", "Silva",
    "Kowalski", "Sato", "Lopez", "Ali", "Becker", "Fischer", "Weber",
    "Hofmann", "Schaefer", "Bauer", "Koehler", "Lehmann", "Walter", "Mayer",
    "Frank", "Berg", "Krueger", "Sanchez", "Martins", "Park", "Liu", "Wang",
    "Zhang", "Iqbal", "Patel", "Khan", "Novak", "Costa", "Jung", "Volkov",
]
ANERKENNUNGSSTATUS = [
    "Die Approbation ist beantragt",
    "Die Fachsprachenprüfung Medizin ist geplant",
    "Die Fachsprachenprüfung Medizin ist abgeschlossen",
    "Die Gleichwertigkeitsprüfung wurde geplant",
]
FIELDS = ["Innere Medizin", "Chirurgie", "Pädiatrie", "Allgemeinmedizin",
          "Dermatologie", "Neurologie", "Orthopädie", "Gynäkologie", "Psychiatrie"]
BUNDESLAENDER = ["Berlin", "Bayern", "Hamburg", "Hessen", "Sachsen",
                 "Niedersachsen", "Nordrhein-Westfalen", "Baden-Württemberg"]
STREETS = ["Hauptstr.", "Goethestr.", "Lindenweg", "Dorfstr.", "Bahnhofstr.",
           "Schillerstr.", "Mühlweg", "Kirchgasse"]

# Survey blocks: (decision_order, upload_order|None, partner_select_order, milestone_order, block_filter_tag, is_multi)
# Orders post-2026-04-28 ueberholspur insertion: every theme block shifted +1.
BLOCKS = [
    (3, 4, 5, 6, "Antragstellung Approbation", False),
    (7, 8, 9, 10, "Fachsprachenprüfung", False),
    (11, 12, 13, 14, "Gleichwertigkeitsprüfung", False),
    (15, 16, 17, 18, "Kenntnisprüfung", False),
    (19, None, 20, 21, "Jobangebote", True),  # multi
    (22, 23, 24, 25, "Weiterbildung", False),
]
UPLOAD_FILENAMES = {
    4:  "approbations_dokumente.png",
    8:  "fachsprachenpruefung_dokumente.png",
    12: "gleichwertigkeitspruefung_dokumente.png",
    16: "kenntnispruefung_dokumente.png",
    23: "weiterbildung_dokumente.png",
}
PARTNER_PROOF_FILENAMES = {
    6:  "partner_bestaetigung_approbation.png",
    10: "partner_bestaetigung_fachsprache.png",
    14: "partner_bestaetigung_gleichwertigkeit.png",
    18: "partner_bestaetigung_kenntnispruefung.png",
    21: "partner_bestaetigung_jobangebote.png",
    25: "partner_bestaetigung_weiterbildung.png",
}

# Stage = "this many blocks fully done; the next block is currently active in
# the indicated state".  Never includes 6 (no fully_done).
STAGES = [
    "fresh",                    #  0 blocks done
    "stammdaten_only",          #  0 blocks done
    "block1_decision",          #  0 blocks done — at decision step
    "block1_upload_inprogress", #  0 — picked upload, not yet uploaded
    "block1_partner_waiting",   #  0 — picked partner, partner_submission pending
    "block1_done",              #  1 block done
    "block2_partner_waiting",   #  1 done, on block 2 partner_waiting (MVZ-eligible: Fachsprache)
    "block2_done",              #  2 done
    "block3_done",              #  3 done
    "block4_partner_waiting",   #  3 done, on block 4 partner_waiting (MVZ-eligible: Kenntnis)
    "block4_done",              #  4 done
    "block5_done",              #  5 done — only block 6 left
    "almost_done",              #  5 done, in block 6
]

# How many full blocks each stage has finished
N_DONE = {
    "fresh": 0, "stammdaten_only": 0, "block1_decision": 0,
    "block1_upload_inprogress": 0, "block1_partner_waiting": 0,
    "block1_done": 1, "block2_partner_waiting": 1, "block2_done": 2,
    "block3_done": 3, "block4_partner_waiting": 3, "block4_done": 4,
    "block5_done": 5, "almost_done": 5,
}


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()


async def upload_placeholder(user_id: str, filename: str, kind: str) -> dict:
    """Persist a 1x1 PNG file in db.files + object storage. Retries on 5xx."""
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{user_id}/{file_id}.png"
    last_err = None
    for attempt in range(5):
        try:
            res = put_object(path, RED_1x1_PNG_BYTES, "image/png")
            break
        except Exception as e:
            last_err = e
            await asyncio.sleep(0.5 * (attempt + 1))
    else:
        raise RuntimeError(f"put_object failed after retries: {last_err}")
    await db.files.insert_one({
        "id": file_id,
        "user_id": str(user_id),
        "storage_path": res["path"],
        "original_filename": filename,
        "content_type": "image/png",
        "size": res.get("size", len(RED_1x1_PNG_BYTES)),
        "is_deleted": False,
        "kind": kind,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"file_id": file_id, "filename": filename}


def progress_doc(user_id, step_id, step_order, status="completed",
                 data=None, days_ago=0):
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


def random_email(idx: int, last: str) -> str:
    safe_last = (last.lower()
                 .replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                 .replace("ß", "ss").replace("í", "i").replace("é", "e"))
    return f"demo{idx:03d}-{safe_last}@chrizz1001.de"


# ============================================================================
async def cleanup():
    """Delete flowbug + existing demo users + their data."""
    flowbug = await db.users.find(
        {"email": {"$regex": "flowbug", "$options": "i"}}, {"_id": 1, "email": 1}
    ).to_list(500)
    flow_ids = [str(u["_id"]) for u in flowbug]
    if flow_ids:
        await db.user_progress.delete_many({"user_id": {"$in": flow_ids}})
        await db.partner_submissions.delete_many({"user_id": {"$in": flow_ids}})
        await db.progress_history.delete_many({"user_id": {"$in": flow_ids}})
        await db.files.delete_many({"user_id": {"$in": flow_ids}})
        await db.users.delete_many({"_id": {"$in": [u["_id"] for u in flowbug]}})
    print(f"[cleanup] removed {len(flow_ids)} flowbug users + their data.")

    demo = await db.users.find(
        {"email": {"$regex": r"^demo\d{3}-", "$options": "i"}}, {"_id": 1}
    ).to_list(2000)
    demo_ids = [str(u["_id"]) for u in demo]
    if demo_ids:
        await db.user_progress.delete_many({"user_id": {"$in": demo_ids}})
        await db.partner_submissions.delete_many({"user_id": {"$in": demo_ids}})
        await db.progress_history.delete_many({"user_id": {"$in": demo_ids}})
        await db.files.delete_many({"user_id": {"$in": demo_ids}})
        await db.users.delete_many({"_id": {"$in": [u["_id"] for u in demo]}})
    print(f"[cleanup] removed {len(demo_ids)} existing demo users + their data.")


async def seed():
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    step_by_order = {s["order"]: s for s in steps}
    if not step_by_order or 24 not in step_by_order:
        raise RuntimeError("Step seed missing — run seed_survey_v2.py first.")

    # Active step ids — used to insert pending stubs for everything we don't
    # explicitly progress. Every (user, active-step) gets one row.
    all_active_step_ids = [(str(s["_id"]), s["order"]) for s in steps]

    partners = await db.partners.find({"is_active": True}).to_list(100)
    partners_by_tag: dict[str, list] = {}
    for p in partners:
        for t in (p.get("tags") or []):
            partners_by_tag.setdefault(t, []).append(p)

    mvz = await db.partners.find_one({"name": "MVZ Gruppe"})
    if not mvz:
        raise RuntimeError("Partner 'MVZ Gruppe' not found")
    mvz_id = str(mvz["_id"])
    mvz_tags = set(mvz.get("tags") or [])
    # Steps where we can route a user to MVZ (filter_tag in MVZ's tag set)
    mvz_eligible_steps = [s for s in steps
                          if s.get("step_type") in ("partner_selection", "partner_multiselection")
                          and s.get("filter_tag") in mvz_tags]
    mvz_eligible_orders = {s["order"] for s in mvz_eligible_steps}
    print(f"[seed] MVZ Gruppe id={mvz_id} eligible-step-orders={sorted(mvz_eligible_orders)}")

    pw_hash = hash_password("Demo123!")

    # Pre-pick which user indices go to MVZ.
    mvz_user_idxs = set(random.sample(range(TOTAL), MVZ_TARGET))
    # MVZ users must reach a stage that hits at least one MVZ-eligible
    # partner_selection step on the partner path. Stages 8 (Fachsprache) and 16
    # (Kenntnis) are inside blocks 2 + 4. So we require these stages:
    mvz_stages = ["block2_partner_waiting", "block4_partner_waiting",
                  "block2_done", "block3_done", "block4_done",
                  "block5_done", "almost_done"]
    # For non-MVZ users we use stages that NEVER hit blocks 2 or 4 with a
    # partner choice routed to MVZ — earlier blocks, or upload-only paths.
    non_mvz_stages = ["fresh", "stammdaten_only", "block1_decision",
                      "block1_upload_inprogress", "block1_partner_waiting",
                      "block1_done"]

    print(f"[seed] generating {TOTAL} demo users (target MVZ: {MVZ_TARGET})…")

    inserted = 0
    mvz_count = 0
    stage_hist: dict[str, int] = {}

    for i in range(TOTAL):
        idx = i + 1
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = random_email(idx, last)
        # avoid email collisions on rare same-last-name draw
        suffix = 1
        while await db.users.find_one({"email": email}):
            email = random_email(idx, f"{last}{suffix}")
            suffix += 1

        is_mvz = i in mvz_user_idxs
        stage = random.choice(mvz_stages if is_mvz else non_mvz_stages)
        stage_hist[stage] = stage_hist.get(stage, 0) + 1

        anerkennung = random.choice(ANERKENNUNGSSTATUS)
        field = random.choice(FIELDS)
        bundesland = random.choice(BUNDESLAENDER)

        signup_days_ago = random.randint(7, 200)
        created_at = (NOW - timedelta(days=signup_days_ago)).isoformat()

        user_doc = {
            "name": f"Dr. {first} {last}",
            "email": email,
            "password_hash": pw_hash,
            "role": "user",
            "is_active": True,
            "created_at": created_at,
            "notification_preferences": {
                "email_on_step_enter": True,
                "email_on_step_edit": False,
                "email_on_step_leave": True,
            },
        }
        result = await db.users.insert_one(user_doc)
        user_id = result.inserted_id
        uid = str(user_id)

        progress: list[dict] = []
        completed_step_ids: set[str] = set()
        # the day-counter walks backwards from "stage just started" to
        # "stammdaten finished long ago" so timestamps stay monotonic.
        days_remaining = random.randint(2, 60)

        # ---- Step 1 (Stammdaten) ----
        if stage != "fresh":
            d_step1 = days_remaining + random.randint(2, 4)
            doc = progress_doc(
                user_id, step_by_order[1]["_id"], 1,
                status="completed",
                data={
                    "first_name": first, "name": last,
                    "date_of_birth": f"{random.randint(1970, 1995)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                    "phone": f"+49 {random.randint(150, 179)} {random.randint(1000000, 9999999)}",
                    "address": f"{random.choice(STREETS)} {random.randint(1, 99)}, {random.randint(10000, 90000)} {bundesland}",
                    "anerkennungsstatus": anerkennung,
                    "anerkennungsverfahren_bundesland": bundesland,
                    "fachrichtung_praktiziert": field,
                    "fachrichtung_gewuenscht": field,
                    "field_of_study": field,
                },
                days_ago=d_step1,
            )
            progress.append(doc)
            completed_step_ids.add(str(step_by_order[1]["_id"]))

            # ---- Step 2 (Schnellstart vs. Selbststart) ----
            # Every demo user picks "Selbststart" so they enter the actual
            # journey. Picking "Überholspur" is a frontend dead-end (info-only)
            # and would block all downstream progress.
            if 2 in step_by_order:
                d_step2 = max(1, d_step1 - 1)
                progress.append(progress_doc(
                    user_id, step_by_order[2]["_id"], 2,
                    status="completed", data={"decision": "selber"},
                    days_ago=d_step2,
                ))
                completed_step_ids.add(str(step_by_order[2]["_id"]))

        # ---- For each block, finish or partial-progress per stage ----
        n_done = N_DONE[stage]
        # If user is MVZ, mark first MVZ-eligible block as the "partner" block.
        # Otherwise random.
        mvz_block_assigned = False

        for blk_idx, (dec_o, up_o, ps_o, ms_o, blk_name, is_multi) in enumerate(BLOCKS):
            block_pos = blk_idx + 1

            # ---- Block fully completed ----
            if block_pos <= n_done:
                # Decide upload vs partner. For MVZ users, force partner on
                # their first MVZ-eligible block, then keep route consistent.
                if is_mvz and not mvz_block_assigned and ps_o in mvz_eligible_orders:
                    decision = "partner"
                    chosen_partner = mvz
                    mvz_block_assigned = True
                    mvz_count += 1
                elif is_multi:
                    decision = random.choice(["selbst", "partner_nutzen"])
                    chosen_partner = None
                else:
                    decision = random.choice(["upload", "partner"])
                    chosen_partner = None

                # decision step
                d_dec = days_remaining + random.randint(3, 8)
                progress.append(progress_doc(
                    user_id, step_by_order[dec_o]["_id"], dec_o,
                    status="completed", data={"decision": decision},
                    days_ago=d_dec))
                completed_step_ids.add(str(step_by_order[dec_o]["_id"]))

                # upload OR partner-selection step
                if decision == "upload" and up_o is not None:
                    placeholder = await upload_placeholder(
                        uid, UPLOAD_FILENAMES.get(up_o, "dokumente.png"), "user_upload"
                    )
                    placeholder["uploaded_at"] = (NOW - timedelta(days=days_remaining + 2)).isoformat()
                    placeholder["document_type"] = blk_name
                    progress.append(progress_doc(
                        user_id, step_by_order[up_o]["_id"], up_o,
                        status="completed",
                        data={"documents": [placeholder]},
                        days_ago=days_remaining + 2))
                    completed_step_ids.add(str(step_by_order[up_o]["_id"]))
                elif decision in ("partner", "partner_nutzen") and ps_o is not None:
                    if chosen_partner is None:
                        # pick a partner that matches this step's filter_tag.
                        # Exclude MVZ from the random pool — MVZ assignments
                        # are deterministic via the `is_mvz` flag, never random.
                        step_obj = step_by_order[ps_o]
                        ftag = step_obj.get("filter_tag")
                        candidates = [p for p in partners_by_tag.get(ftag, [])
                                      if str(p["_id"]) != mvz_id]
                        if not candidates:
                            candidates = [p for p in partners if str(p["_id"]) != mvz_id]
                        chosen_partner = random.choice(candidates)
                    chosen_list = [chosen_partner]
                    if is_multi and len(partners_by_tag.get(blk_name, [])) > 1:
                        chosen_list = random.sample(partners_by_tag[blk_name], k=2)
                    ids = [str(p["_id"]) for p in chosen_list]
                    names = [p["name"] for p in chosen_list]
                    data = ({"selected_partner_ids": ids, "selected_partner_names": names}
                            if is_multi else
                            {"selected_partner_id": ids[0], "selected_partner_name": names[0]})
                    progress.append(progress_doc(
                        user_id, step_by_order[ps_o]["_id"], ps_o,
                        status="completed", data=data,
                        days_ago=days_remaining + 1))
                    completed_step_ids.add(str(step_by_order[ps_o]["_id"]))
                    # partner_submission(s) — work_completed=True since the
                    # whole block is done
                    for cp, cid in zip(chosen_list, ids):
                        await db.partner_submissions.insert_one({
                            "user_id": uid, "user_email": email,
                            "user_name": user_doc["name"], "partner_id": cid,
                            "data": {"step_order": ps_o, "field_of_study": field,
                                     "bundesland": bundesland,
                                     "step_data": data},
                            "status": "submitted",
                            "partner_work_completed": True,
                            "completed_at": (NOW - timedelta(days=days_remaining)).isoformat(),
                            "created_at": (NOW - timedelta(days=days_remaining + 3)).isoformat(),
                            "id": f"sub-{uid}-{cid}",
                        })

                # milestone — completed for both routes since block is done
                ms_data = {"completed_by": "auto" if decision in ("upload", "selbst") else "partner"}
                if decision in ("partner", "partner_nutzen"):
                    proof = await upload_placeholder(
                        uid, PARTNER_PROOF_FILENAMES.get(ms_o, "nachweis.png"),
                        "partner_verification",
                    )
                    proof["uploaded_at"] = (NOW - timedelta(days=days_remaining)).isoformat()
                    proof["document_type"] = "Partner-Nachweis"
                    proof["uploaded_by"] = "partner"
                    ms_data["partner_uploads"] = [proof]
                progress.append(progress_doc(
                    user_id, step_by_order[ms_o]["_id"], ms_o,
                    status="completed", data=ms_data,
                    days_ago=days_remaining))
                completed_step_ids.add(str(step_by_order[ms_o]["_id"]))

            # ---- The "active" block (the one currently in progress) ----
            elif block_pos == n_done + 1:
                if stage in ("fresh", "stammdaten_only"):
                    pass  # nothing in this block yet
                elif stage == "block1_decision":
                    progress.append(progress_doc(
                        user_id, step_by_order[dec_o]["_id"], dec_o,
                        status="in_progress", data={}, days_ago=1))
                elif stage == "block1_upload_inprogress":
                    progress.append(progress_doc(
                        user_id, step_by_order[dec_o]["_id"], dec_o,
                        status="completed", data={"decision": "upload"}, days_ago=2))
                    completed_step_ids.add(str(step_by_order[dec_o]["_id"]))
                    if up_o:
                        progress.append(progress_doc(
                            user_id, step_by_order[up_o]["_id"], up_o,
                            status="in_progress", data={}, days_ago=1))
                elif stage in ("block1_partner_waiting", "block2_partner_waiting", "block4_partner_waiting"):
                    progress.append(progress_doc(
                        user_id, step_by_order[dec_o]["_id"], dec_o,
                        status="completed", data={"decision": "partner"}, days_ago=3))
                    completed_step_ids.add(str(step_by_order[dec_o]["_id"]))
                    if ps_o:
                        if is_mvz and not mvz_block_assigned and ps_o in mvz_eligible_orders:
                            chosen_partner = mvz
                            mvz_block_assigned = True
                            mvz_count += 1
                        else:
                            ftag = step_by_order[ps_o].get("filter_tag")
                            cands = [p for p in (partners_by_tag.get(ftag, []) or partners)
                                     if str(p["_id"]) != mvz_id]
                            chosen_partner = random.choice(cands) if cands else partners[0]
                        cid = str(chosen_partner["_id"])
                        progress.append(progress_doc(
                            user_id, step_by_order[ps_o]["_id"], ps_o,
                            status="completed",
                            data={"selected_partner_id": cid,
                                  "selected_partner_name": chosen_partner["name"]},
                            days_ago=2))
                        completed_step_ids.add(str(step_by_order[ps_o]["_id"]))
                        await db.partner_submissions.insert_one({
                            "user_id": uid, "user_email": email,
                            "user_name": user_doc["name"], "partner_id": cid,
                            "data": {"step_order": ps_o, "field_of_study": field,
                                     "bundesland": bundesland},
                            "status": "submitted",
                            "partner_work_completed": False,
                            "created_at": (NOW - timedelta(days=2)).isoformat(),
                            "id": f"sub-{uid}-{cid}",
                        })
                elif stage == "almost_done":
                    # block 6 — at decision step
                    progress.append(progress_doc(
                        user_id, step_by_order[dec_o]["_id"], dec_o,
                        status="in_progress", data={}, days_ago=1))

        # ---- Pending stubs for everything else ----
        for sid, sord in all_active_step_ids:
            if sid in completed_step_ids:
                continue
            # any progress already inserted (in_progress or completed)
            if any(p["step_id"] == sid for p in progress):
                continue
            progress.append({
                "user_id": uid, "step_id": sid, "step_order": sord,
                "status": "pending", "data": {},
                "created_at": created_at, "updated_at": created_at,
            })

        if progress:
            await db.user_progress.insert_many(progress)
        inserted += 1
        if inserted % 50 == 0:
            print(f"  …{inserted}/{TOTAL} users seeded")

    print(f"\n[seed] {inserted} demo users created. MVZ-routed: {mvz_count}/{MVZ_TARGET}")
    print(f"[seed] stage histogram: {sorted(stage_hist.items())}")
    if mvz_count < MVZ_TARGET:
        print(f"[WARN] MVZ count below target — check stage selection logic")


async def main():
    await cleanup()
    await seed()
    # Final sanity counts
    total_demo = await db.users.count_documents({"email": {"$regex": r"^demo\d{3}-"}})
    total_subs_mvz = await db.partner_submissions.count_documents({
        "partner_id": str((await db.partners.find_one({"name": "MVZ Gruppe"}))["_id"])
    })
    distinct_mvz_users = len(await db.partner_submissions.distinct(
        "user_id",
        {"partner_id": str((await db.partners.find_one({"name": "MVZ Gruppe"}))["_id"])},
    ))
    print(f"\n[sanity] demoNNN-* users: {total_demo}")
    print(f"[sanity] partner_submissions to MVZ Gruppe: {total_subs_mvz}")
    print(f"[sanity] distinct users assigned to MVZ Gruppe: {distinct_mvz_users}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
