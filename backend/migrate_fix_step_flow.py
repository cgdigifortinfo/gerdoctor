"""Migration: clean up step flow + add congratulations step.

Fixes (idempotent):
  1. Step #19 (multi-partner Jobangebote): hide condition was `decision != 'selbst'`
     which made the multi-select appear when user wants to search ALONE.
     Correct: hide when `decision != 'partner_nutzen'`.
  2. Add a final "display" step #25 ("Herzlichen Glückwunsch") if missing.

Run:  python3 /app/backend/migrate_fix_step_flow.py
"""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]


CONGRATS_BODY_HTML = """
<div style="text-align:center;padding:32px 16px;">
  <div style="font-size:64px;margin-bottom:12px;">🎉</div>
  <h2 style="color:#114f55;font-size:28px;font-weight:800;margin:0 0 12px 0;letter-spacing:-0.02em;">
    Herzlichen Glückwunsch!
  </h2>
  <p style="font-size:18px;color:#0f172a;margin:0 0 16px 0;">
    Du hast deinen Weg zum Facharzt in Deutschland erfolgreich abgeschlossen.
  </p>
  <p style="font-size:15px;color:#475569;line-height:1.7;max-width:560px;margin:0 auto 24px;">
    Alle Meilensteine sind freigeschaltet — Approbation, Sprache, Anerkennung,
    Kenntnisprüfung und Weiterbildung. Du bist jetzt in der Lage, in Deutschland
    eigenverantwortlich tätig zu werden.
  </p>
  <div style="display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-top:8px;">
    <span style="background:#114f55;color:#fff;padding:6px 14px;border-radius:999px;font-size:13px;font-weight:600;">
      Approbation ✓
    </span>
    <span style="background:#114f55;color:#fff;padding:6px 14px;border-radius:999px;font-size:13px;font-weight:600;">
      Fachsprache ✓
    </span>
    <span style="background:#114f55;color:#fff;padding:6px 14px;border-radius:999px;font-size:13px;font-weight:600;">
      Anerkennung ✓
    </span>
    <span style="background:#114f55;color:#fff;padding:6px 14px;border-radius:999px;font-size:13px;font-weight:600;">
      Weiterbildung ✓
    </span>
  </div>
</div>
""".strip()


async def fix_jobangebote_multi():
    s = await db.steps.find_one({"order": 19})
    if not s:
        print("step #19 missing — skip")
        return
    conds = s.get("conditions") or []
    changed = False
    for c in conds:
        if (c.get("action") == "hide"
            and c.get("source_step_order") == 18
            and c.get("field") == "decision"
            and c.get("operator") == "not_equals"
            and c.get("value") == "selbst"):
            c["value"] = "partner_nutzen"
            changed = True
    if changed:
        await db.steps.update_one({"_id": s["_id"]}, {"$set": {"conditions": conds}})
        print("step #19 condition fixed: hide when decision != 'partner_nutzen'")
    else:
        print("step #19 condition already correct")


async def ensure_congrats_step():
    existing = await db.steps.find_one({"order": 25})
    payload = {
        "title": "Herzlichen Glückwunsch!",
        "step_type": "display",
        "description": "Du hast deine Reise erfolgreich abgeschlossen.",
        "content": CONGRATS_BODY_HTML,
        "is_active": True,
        "skippable": False,
        "filter_tag": "",
        "fields": [],
        "conditions": [],
        "duration_value": 0,
        "duration_unit": "days",
        "translations": {
            "de": {"title": "Herzlichen Glückwunsch!",
                   "description": "Du hast deine Reise erfolgreich abgeschlossen.",
                   "content": CONGRATS_BODY_HTML},
            "en": {"title": "Congratulations!",
                   "description": "You have completed your journey successfully.",
                   "content": CONGRATS_BODY_HTML.replace("Du hast", "You have")
                                                 .replace("deinen Weg zum Facharzt in Deutschland erfolgreich abgeschlossen", "successfully completed your journey to becoming a medical specialist in Germany")
                                                 .replace("Alle Meilensteine sind freigeschaltet — Approbation, Sprache, Anerkennung, Kenntnisprüfung und Weiterbildung. Du bist jetzt in der Lage, in Deutschland eigenverantwortlich tätig zu werden.", "All milestones are unlocked — Approbation, Language, Recognition, Knowledge Exam and Specialist Training. You are now ready to practice independently in Germany.")},
        },
    }
    if existing:
        await db.steps.update_one({"_id": existing["_id"]}, {"$set": payload})
        print("step #25 (Herzlichen Glückwunsch) updated")
        return
    payload["order"] = 25
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_at"] = payload["created_at"]
    await db.steps.insert_one(payload)
    print("step #25 (Herzlichen Glückwunsch) created")


async def main():
    await fix_jobangebote_multi()
    await ensure_congrats_step()
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
