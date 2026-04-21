"""
Migration: update milestone auto_complete conditions to require a real file upload.

BEFORE: milestone #5 has
  { action: auto_complete, source_step_order: 3, operator: status_is, value: completed }

AFTER: milestone #5 has
  { action: auto_complete, source_step_order: 3, field: "documents",
    operator: has_upload, value: "" }
  + additional block condition when user chose upload but uploaded nothing.

The migration is idempotent — it detects milestones that already have the new
`has_upload` + block-`all_of` pattern and skips them.

Only touches milestone steps whose auto_complete refers to a `form` step
(the pattern produced by seed_survey_v2.build_block). Standalone decision-based
milestones (Jobangebote) are untouched.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


async def run() -> int:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # Load all steps so we can find decision/upload pairs by order
    steps = await db.steps.find({}).sort("order", 1).to_list(500)
    by_order = {s["order"]: s for s in steps}

    updated = 0
    skipped = 0

    for ms in steps:
        if ms.get("step_type") != "milestone":
            continue
        conditions = list(ms.get("conditions") or [])
        # Find the legacy auto_complete condition that targets a form step
        legacy_idx = None
        upload_order = None
        decision_order = None
        for i, c in enumerate(conditions):
            if c.get("action") != "auto_complete":
                continue
            if c.get("operator") != "status_is":
                continue
            src = c.get("source_step_order")
            upstep = by_order.get(src)
            if upstep and upstep.get("step_type") == "form":
                legacy_idx = i
                upload_order = src
                # decision step is the one right before the upload step (upload_order - 1)
                prev = by_order.get(upload_order - 1)
                if prev and prev.get("step_type") == "decision":
                    decision_order = prev["order"]
                break
        if legacy_idx is None:
            skipped += 1
            continue

        # Already migrated? Detect `has_upload` auto_complete on documents
        already = any(
            c.get("action") == "auto_complete"
            and c.get("operator") == "has_upload"
            and c.get("field") == "documents"
            and c.get("source_step_order") == upload_order
            for c in conditions
        )
        if already:
            skipped += 1
            continue

        # Replace legacy auto_complete with has_upload variant
        new_auto = {
            "action": "auto_complete",
            "source_step_order": upload_order,
            "field": "documents", "operator": "has_upload", "value": "",
        }
        conditions[legacy_idx] = new_auto

        # Add block condition only if we know the decision order
        if decision_order is not None:
            block_cond = {
                "action": "block",
                "all_of": [
                    {
                        "source_step_order": decision_order,
                        "field": "decision", "operator": "equals", "value": "upload",
                    },
                    {
                        "source_step_order": upload_order,
                        "field": "documents", "operator": "missing_upload", "value": "",
                    },
                ],
                "message": "Bitte laden Sie Ihre Dokumente im vorigen Schritt hoch.",
            }
            # Don't duplicate if a matching block already exists
            has_block_all_of = any(
                c.get("action") == "block"
                and isinstance(c.get("all_of"), list)
                and any(sub.get("source_step_order") == upload_order
                        and sub.get("operator") == "missing_upload" for sub in c["all_of"])
                for c in conditions
            )
            if not has_block_all_of:
                conditions.append(block_cond)

        await db.steps.update_one(
            {"_id": ObjectId(str(ms["_id"]))},
            {"$set": {"conditions": conditions}},
        )
        print(f"  ✓ milestone #{ms['order']} '{ms['title']}' migrated "
              f"(upload=#{upload_order}, decision=#{decision_order})")
        updated += 1

    # Recompute user auto-completes since the trigger rule just changed:
    # Milestones that were auto-completed due to bare status=completed (no file)
    # should be rolled back to pending.
    rollback = 0
    for ms in await db.steps.find({"step_type": "milestone"}).to_list(200):
        sid = str(ms["_id"])
        # Find the upload-source-step_order in its new auto_complete condition
        upload_order = None
        for c in (ms.get("conditions") or []):
            if (c.get("action") == "auto_complete"
                    and c.get("operator") == "has_upload"
                    and c.get("field") == "documents"):
                upload_order = c.get("source_step_order")
                break
        if upload_order is None:
            continue
        upstep = by_order.get(upload_order)
        if not upstep:
            continue
        upstep_id = str(upstep["_id"])

        async for prog in db.user_progress.find({"step_id": sid, "status": "completed"}):
            # Check if this completion was auto (no real data) AND upload step has no file
            uid = prog["user_id"]
            up_prog = await db.user_progress.find_one({"user_id": uid, "step_id": upstep_id})
            up_data = (up_prog or {}).get("data") or {}
            docs = up_data.get("documents") or []
            has_file = isinstance(docs, list) and any(
                isinstance(d, dict) and d.get("file_id") for d in docs
            )
            if has_file:
                continue  # legit completion
            # No real file uploaded → this milestone was auto-completed by the old rule
            data = prog.get("data") or {}
            # Don't rollback if a partner actually uploaded something
            if isinstance(data.get("partner_uploads"), list) and data["partner_uploads"]:
                continue
            # Don't rollback manual admin/partner-set completions carrying other data
            if data and not data.get("auto_completed"):
                continue
            await db.user_progress.update_one(
                {"_id": prog["_id"]},
                {"$set": {"status": "pending", "completed_at": None},
                 "$unset": {"auto_completed": ""}},
            )
            rollback += 1

    client.close()
    print()
    print(f"Summary: {updated} milestone(s) migrated, {skipped} already-correct, "
          f"{rollback} user-progress row(s) rolled back to pending.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
