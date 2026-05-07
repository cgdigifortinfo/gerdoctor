"""Migration: Insert "Bring mich auf die Überholspur" decision step at order 2.

Before:
  order 1  Stammdaten
  order 2  Decision Antragstellung Approbation
  order 3  Upload …
  order 4  Partner Selection …
  order 5  Milestone
  …
  order 25 (Congrats)

After:
  order 1  Stammdaten
  order 2  NEW Decision: "Bring mich auf die Überholspur" / "Lass mich selber starten"
           - Option "ueberholspur" is `primary=True` → frontend renders an
             inline info panel + Zurück (no Weiter), so the user is forced to
             go back and pick the other option to actually continue.
           - Option "selber" → completes the step, journey continues.
  order 3  was order 2 (Decision Antragstellung Approbation)
  order 4  was order 3 (Upload …)
  …
  order 26 was order 25 (Congrats)

Steps performed
---------------
1. Shift every active step with order >= 2 by +1.
2. Shift `source_step_order` in every step's `conditions` accordingly so the
   numeric references stay correct after the reorder.
3. Shift `step_order` in user_progress + progress_history likewise.
4. Insert the new step at order 2.
5. For every active user (role=user) insert a pending stub for the new step.

Idempotent — re-runs are no-ops once the new step exists.
Run: python3 /app/backend/migrate_add_ueberholspur_step.py
"""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")


NEW_STEP_TITLE = "Schnellstart oder Selbststart?"


def _shift_conditions(conds: list, threshold: int = 2, delta: int = 1) -> list:
    """Return a deep-shifted copy of `conditions` so any source_step_order >=
    threshold gets incremented by `delta`."""
    out = []
    for c in conds or []:
        nc = dict(c)
        if isinstance(c.get("source_step_order"), int) and c["source_step_order"] >= threshold:
            nc["source_step_order"] = c["source_step_order"] + delta
        for key in ("all_of", "any_of"):
            if isinstance(c.get(key), list):
                nc[key] = _shift_conditions(c[key], threshold, delta)
        out.append(nc)
    return out


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # --- Idempotency check ---
    existing = await db.steps.find_one({"order": 2, "is_active": True})
    if existing and existing.get("title") == NEW_STEP_TITLE:
        print("[migrate] Already applied (new step at order 2 exists). Nothing to do.")
        client.close()
        return

    # --- (1+2) Shift existing steps + their conditions ---
    # Sort descending so the order=N shift to order=N+1 doesn't collide with
    # the next iteration's expected order=N+1.
    affected_steps = await db.steps.find({"order": {"$gte": 2}}).sort("order", -1).to_list(200)
    print(f"[migrate] Shifting {len(affected_steps)} step rows by +1.")
    for s in affected_steps:
        new_conds = _shift_conditions(s.get("conditions") or [])
        await db.steps.update_one(
            {"_id": s["_id"]},
            {"$set": {"order": s["order"] + 1, "conditions": new_conds}},
        )

    # Conditions on order=1 (Stammdaten) reference no step >=2 in current
    # design, but apply the same transform defensively.
    stammdaten = await db.steps.find_one({"order": 1, "is_active": True})
    if stammdaten and (stammdaten.get("conditions") or []):
        new_conds = _shift_conditions(stammdaten["conditions"])
        await db.steps.update_one(
            {"_id": stammdaten["_id"]},
            {"$set": {"conditions": new_conds}},
        )

    # --- (3) Shift user_progress.step_order ---
    progress_res = await db.user_progress.update_many(
        {"step_order": {"$gte": 2}},
        [{"$set": {"step_order": {"$add": ["$step_order", 1]}}}],
    )
    history_res = await db.progress_history.update_many(
        {"step_order": {"$gte": 2}},
        [{"$set": {"step_order": {"$add": ["$step_order", 1]}}}],
    )
    print(f"[migrate] Shifted {progress_res.modified_count} user_progress rows + "
          f"{history_res.modified_count} progress_history rows.")

    # --- (4) Insert the new step ---
    now = datetime.now(timezone.utc).isoformat()
    new_step = {
        "title": NEW_STEP_TITLE,
        "description": "Wählen Sie, wie Sie Ihren Anerkennungsprozess starten wollen.",
        "order": 2,
        "step_type": "decision",
        "is_active": True,
        "duration_value": 0,
        "duration_unit": "days",
        "fields": [
            {
                "name": "decision",
                "field_type": "decision",
                "label": "Schnellstart oder Selbststart?",
                "required": True,
                "options": [
                    {
                        "value": "ueberholspur",
                        "label": "Bring mich auf die Überholspur",
                        "primary": True,
                        "info_title": "Persönliche Begleitung durch das gesamte Verfahren",
                        "info_body": (
                            "<p><strong>Mit der Überholspur</strong> übernehmen wir die komplette "
                            "Koordination Ihres Anerkennungsverfahrens. Sie sparen Zeit, Nerven "
                            "und vermeiden teure Verzögerungen.</p>"
                            "<ul class='list-disc pl-5 mt-3 space-y-1'>"
                            "<li>Persönlicher Ansprechpartner</li>"
                            "<li>Vorbereitung &amp; Einreichung aller Dokumente</li>"
                            "<li>Direkter Draht zu Behörden &amp; Prüfungsstellen</li>"
                            "<li>Garantierte Termine für Fach- und Kenntnisprüfung</li>"
                            "</ul>"
                            "<p class='mt-4 text-sm text-muted-foreground'>"
                            "Unser Team meldet sich innerhalb von 24 Stunden bei Ihnen. "
                            "Klicken Sie auf <em>Zurück</em>, um zur Auswahl zurückzukehren.</p>"
                        ),
                    },
                    {
                        "value": "selber",
                        "label": "Lass mich selber starten",
                    },
                ],
            }
        ],
        "conditions": [],
        "translations": {
            "en": {
                "title": "Fast lane or self-start?",
                "description": "Choose how to start your recognition process.",
                "fields": [{
                    "name": "decision",
                    "label": "Fast lane or self-start?",
                    "options": [
                        {"value": "ueberholspur", "label": "Put me on the fast lane",
                         "info_title": "Personal guidance through the whole process",
                         "info_body": ("<p><strong>The fast lane</strong> means we take care of the "
                                       "complete coordination of your recognition process.</p>"
                                       "<p class='mt-4 text-sm text-muted-foreground'>"
                                       "Our team will reach out within 24 hours. Click <em>Back</em> "
                                       "to return to the selection.</p>")},
                        {"value": "selber", "label": "Let me start on my own"},
                    ]
                }]
            }
        },
        "created_at": now,
    }
    res = await db.steps.insert_one(new_step)
    new_id = str(res.inserted_id)
    print(f"[migrate] Inserted new step at order=2 id={new_id}")

    # --- (5) Insert pending stub for every existing user ---
    users = await db.users.find({"role": "user"}, {"_id": 1, "created_at": 1}).to_list(2000)
    new_progress_rows = []
    for u in users:
        new_progress_rows.append({
            "user_id": str(u["_id"]),
            "step_id": new_id,
            "step_order": 2,
            "status": "pending",
            "data": {},
            "created_at": u.get("created_at") or now,
            "updated_at": now,
        })
    if new_progress_rows:
        await db.user_progress.insert_many(new_progress_rows)
    print(f"[migrate] Inserted {len(new_progress_rows)} pending stubs for the new step.")

    # --- Sanity: total active step count ---
    cnt = await db.steps.count_documents({"is_active": True})
    print(f"[migrate] Active step count is now {cnt}.")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
