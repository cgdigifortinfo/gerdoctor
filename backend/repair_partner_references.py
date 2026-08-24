"""Audit and repair inconsistent partner references.

Dry-run is the default::

    python /app/backend/repair_partner_references.py

Apply reviewed repairs explicitly::

    python /app/backend/repair_partner_references.py --apply

The script is idempotent. It resolves unique legacy partner names, removes
dangling partner references, resets invalid completed partner-selection steps
to ``pending``, and deletes records only when their owning user/step/partner no
longer exists. It never deletes a user or partner organisation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


PARTNER_SELECTION_TYPES = {"partner_selection", "partner_multiselection"}
PARTNER_DATA_KEYS = {
    "selected_partner_id",
    "selected_partner_name",
    "selected_partner_ids",
    "selected_partner_names",
}


def _name_key(value: Any) -> str:
    return str(value or "").strip().casefold()


def build_partner_lookups(partners: list[dict]) -> tuple[dict[str, str], dict[str, list[str]]]:
    names_by_id = {str(row["_id"]): str(row.get("name") or "").strip() for row in partners}
    ids_by_name: dict[str, list[str]] = defaultdict(list)
    for partner_id, name in names_by_id.items():
        if name:
            ids_by_name[_name_key(name)].append(partner_id)
    return names_by_id, dict(ids_by_name)


def _unique_id_for_name(name: Any, ids_by_name: dict[str, list[str]]) -> str | None:
    matches = ids_by_name.get(_name_key(name), [])
    return matches[0] if len(matches) == 1 else None


def _split_legacy_names(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def repair_progress_partner_data(
    data: dict | None,
    names_by_id: dict[str, str],
    ids_by_name: dict[str, list[str]],
) -> tuple[dict, list[dict[str, str]]]:
    """Return corrected progress data plus machine-readable repair actions."""
    original = deepcopy(data or {})
    corrected = deepcopy(original)
    actions: list[dict[str, str]] = []

    single_id = str(original.get("selected_partner_id") or "").strip()
    single_name = str(original.get("selected_partner_name") or "").strip()
    if single_id:
        if single_id in names_by_id:
            canonical = names_by_id[single_id]
            if single_name != canonical:
                corrected["selected_partner_name"] = canonical
                actions.append({"action": "canonicalize_name", "value": canonical})
        else:
            replacement = _unique_id_for_name(single_name, ids_by_name)
            if replacement:
                corrected["selected_partner_id"] = replacement
                corrected["selected_partner_name"] = names_by_id[replacement]
                actions.append({"action": "replace_stale_id", "value": single_id})
            else:
                corrected.pop("selected_partner_id", None)
                corrected.pop("selected_partner_name", None)
                actions.append({"action": "remove_orphan_single", "value": single_name or single_id})
    elif single_name:
        replacement = _unique_id_for_name(single_name, ids_by_name)
        if replacement:
            corrected["selected_partner_id"] = replacement
            corrected["selected_partner_name"] = names_by_id[replacement]
            actions.append({"action": "resolve_legacy_name", "value": single_name})
        else:
            corrected.pop("selected_partner_name", None)
            actions.append({"action": "remove_orphan_name", "value": single_name})

    original_multi_ids = [str(value) for value in (original.get("selected_partner_ids") or []) if value]
    legacy_names = _split_legacy_names(original.get("selected_partner_names"))
    valid_multi_ids: list[str] = []
    for partner_id in original_multi_ids:
        if partner_id in names_by_id and partner_id not in valid_multi_ids:
            valid_multi_ids.append(partner_id)
        elif partner_id not in names_by_id:
            actions.append({"action": "remove_orphan_multi_id", "value": partner_id})

    # Name-only multi selections can be recovered only through unique names.
    if not original_multi_ids and legacy_names:
        for name in legacy_names:
            partner_id = _unique_id_for_name(name, ids_by_name)
            if partner_id and partner_id not in valid_multi_ids:
                valid_multi_ids.append(partner_id)
                actions.append({"action": "resolve_legacy_multi_name", "value": name})
            elif not partner_id:
                actions.append({"action": "remove_orphan_multi_name", "value": name})

    if original_multi_ids or "selected_partner_ids" in original or legacy_names:
        if valid_multi_ids:
            corrected["selected_partner_ids"] = valid_multi_ids
            corrected["selected_partner_names"] = ", ".join(names_by_id[value] for value in valid_multi_ids)
        else:
            corrected.pop("selected_partner_ids", None)
            corrected.pop("selected_partner_names", None)

    return corrected, actions


def _has_partner_selection(data: dict) -> bool:
    return bool(data.get("selected_partner_id") or data.get("selected_partner_ids"))


async def audit_and_repair(db, *, apply: bool = False, user_email: str | None = None) -> dict:
    users = await db.users.find({}, {"email": 1, "name": 1, "role": 1, "partner_id": 1, "survey_id": 1}).to_list(None)
    partners = await db.partners.find({}, {"name": 1, "user_id": 1, "linked_user_ids": 1, "tags": 1, "survey_ids": 1, "is_active": 1, "registration_status": 1}).to_list(None)
    steps = await db.steps.find({}, {"step_type": 1, "filter_tag": 1, "survey_id": 1, "order": 1}).to_list(None)
    user_ids = {str(row["_id"]) for row in users}
    partner_ids = {str(row["_id"]) for row in partners}
    step_ids = {str(row["_id"]) for row in steps}
    partner_step_ids = {
        str(row["_id"]) for row in steps if row.get("step_type") in PARTNER_SELECTION_TYPES
    }
    names_by_id, ids_by_name = build_partner_lookups(partners)
    email_by_user_id = {str(row["_id"]): row.get("email") for row in users}
    scoped_user_ids = {
        user_id for user_id, email in email_by_user_id.items()
        if not user_email or str(email or "").casefold() == user_email.casefold()
    }
    now = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "mode": "apply" if apply else "dry-run",
        "scope": user_email or "all-users",
        "counts": defaultdict(int),
        "actions": [],
    }

    def record(collection: str, record_id: Any, action: str, details: Any = None):
        report["counts"][f"{collection}.{action}"] += 1
        report["actions"].append({
            "collection": collection,
            "record_id": str(record_id),
            "action": action,
            "details": details,
        })

    progress_query = {"user_id": {"$in": list(scoped_user_ids)}} if user_email else {}
    async for row in db.user_progress.find(progress_query):
        user_id, step_id = row.get("user_id"), row.get("step_id")
        if user_id not in user_ids or step_id not in step_ids:
            record("user_progress", row["_id"], "delete_orphan_record", {"user_id": user_id, "step_id": step_id})
            if apply:
                await db.user_progress.delete_one({"_id": row["_id"]})
            continue
        if step_id not in partner_step_ids and not PARTNER_DATA_KEYS.intersection((row.get("data") or {}).keys()):
            continue
        corrected, actions = repair_progress_partner_data(row.get("data"), names_by_id, ids_by_name)
        if not actions:
            continue
        update_set: dict[str, Any] = {"data": corrected, "updated_at": now}
        update_unset: dict[str, str] = {}
        if row.get("status") == "completed" and not _has_partner_selection(corrected):
            update_set["status"] = "pending"
            update_unset["completed_at"] = ""
        record("user_progress", row["_id"], "repair_partner_data", actions)
        if apply:
            update: dict[str, Any] = {"$set": update_set}
            if update_unset:
                update["$unset"] = update_unset
            await db.user_progress.update_one({"_id": row["_id"]}, update)

    submission_query = {"user_id": {"$in": list(scoped_user_ids)}} if user_email else {}
    async for row in db.partner_submissions.find(submission_query):
        if row.get("user_id") not in user_ids or row.get("partner_id") not in partner_ids:
            record("partner_submissions", row["_id"], "delete_orphan_record", {
                "user_id": row.get("user_id"), "partner_id": row.get("partner_id"),
            })
            if apply:
                await db.partner_submissions.delete_one({"_id": row["_id"]})

    # Reconcile the two representations of a partner choice. user_progress is
    # authoritative when it contains a selection. A legacy submission can
    # restore an empty completed selection only when it points to itself and
    # maps unambiguously to exactly one selection step.
    partners_by_id = {str(row["_id"]): row for row in partners}
    selection_steps = [row for row in steps if row.get("step_type") in PARTNER_SELECTION_TYPES]
    step_by_id = {str(row["_id"]): row for row in selection_steps}
    for user_id in scoped_user_ids:
        user = next((row for row in users if str(row["_id"]) == user_id), None)
        user_steps = [row for row in selection_steps if not user or not user.get("survey_id") or row.get("survey_id") == user.get("survey_id")]
        progress_rows = await db.user_progress.find({"user_id": user_id, "step_id": {"$in": [str(row["_id"]) for row in user_steps]}}).to_list(None)
        progress_by_step = {row.get("step_id"): row for row in progress_rows}
        submissions = await db.partner_submissions.find({"user_id": user_id}).to_list(None)

        def candidate_step_ids(submission: dict) -> list[str]:
            explicit = submission.get("step_id") or (submission.get("data") or {}).get("_step_id")
            if explicit in step_by_id:
                return [explicit]
            partner = partners_by_id.get(submission.get("partner_id")) or {}
            tags = set(partner.get("tags") or [])
            return [str(step["_id"]) for step in user_steps if step.get("filter_tag") in tags]

        for step in user_steps:
            step_id = str(step["_id"])
            progress = progress_by_step.get(step_id)
            progress_data = deepcopy((progress or {}).get("data") or {})
            selected_ids = set(str(value) for value in (progress_data.get("selected_partner_ids") or []) if value)
            if progress_data.get("selected_partner_id"):
                selected_ids.add(str(progress_data["selected_partner_id"]))
            selected_ids.intersection_update(names_by_id)
            candidates = [submission for submission in submissions if candidate_step_ids(submission) == [step_id]]

            if not selected_ids:
                trustworthy = []
                for submission in candidates:
                    data = submission.get("data") or {}
                    claimed = {str(value) for value in (data.get("selected_partner_ids") or []) if value}
                    if data.get("selected_partner_id"):
                        claimed.add(str(data["selected_partner_id"]))
                    if submission.get("partner_id") in claimed:
                        trustworthy.append(submission)
                if len(trustworthy) == 1 and progress:
                    submission = trustworthy[0]
                    partner_id = submission["partner_id"]
                    partner_name = names_by_id[partner_id]
                    restored = ({"selected_partner_ids": [partner_id], "selected_partner_names": partner_name}
                                if step.get("step_type") == "partner_multiselection"
                                else {"selected_partner_id": partner_id, "selected_partner_name": partner_name})
                    selected_ids = {partner_id}
                    record("user_progress", progress["_id"], "restore_selection_from_submission", {"step_id": step_id, "partner_id": partner_id})
                    if apply:
                        await db.user_progress.update_one({"_id": progress["_id"]}, {"$set": {"data": restored, "status": "completed", "updated_at": now}})

            if not selected_ids:
                continue
            for submission in candidates:
                if submission.get("partner_id") not in selected_ids:
                    record("partner_submissions", submission["_id"], "delete_stale_step_assignment", {"step_id": step_id, "partner_id": submission.get("partner_id")})
                    if apply:
                        await db.partner_submissions.delete_one({"_id": submission["_id"]})
            for partner_id in selected_ids:
                matching = next((row for row in candidates if row.get("partner_id") == partner_id), None)
                ordered_selected_ids = sorted(selected_ids)
                canonical_data = {k: v for k, v in ((matching or {}).get("data") or {}).items() if k != "_step_id"}
                canonical_data.update({"selected_partner_ids": ordered_selected_ids, "selected_partner_names": ", ".join(names_by_id[value] for value in ordered_selected_ids)}
                                      if step.get("step_type") == "partner_multiselection"
                                      else {"selected_partner_id": partner_id, "selected_partner_name": names_by_id[partner_id]})
                if matching and (matching.get("step_id") != step_id or (matching.get("data") or {}) != canonical_data):
                    record("partner_submissions", matching["_id"], "synchronize_with_progress", {"step_id": step_id, "partner_id": partner_id})
                    if apply:
                        await db.partner_submissions.update_one({"_id": matching["_id"]}, {"$set": {"step_id": step_id, "data": canonical_data, "updated_at": now}})
                elif not matching:
                    record("partner_submissions", f"new:{user_id}:{step_id}:{partner_id}", "create_from_progress", {"step_id": step_id, "partner_id": partner_id})
                    if apply:
                        await db.partner_submissions.insert_one({
                            "id": f"repair-{user_id}-{step_id}-{partner_id}", "user_id": user_id,
                            "user_email": (user or {}).get("email", ""), "user_name": (user or {}).get("name", ""),
                            "partner_id": partner_id, "step_id": step_id, "data": canonical_data,
                            "status": "submitted", "created_at": now, "updated_at": now,
                        })

    # Global structural checks are skipped for a single-user scope.
    if not user_email:
        for partner in partners:
            partner_id = str(partner["_id"])
            linked = partner.get("linked_user_ids") or []
            cleaned_linked = list(dict.fromkeys(value for value in linked if value in user_ids))
            if cleaned_linked != linked:
                record("partners", partner_id, "remove_orphan_linked_users", {
                    "removed": [value for value in linked if value not in user_ids],
                })
                if apply:
                    await db.partners.update_one(
                        {"_id": partner["_id"]}, {"$set": {"linked_user_ids": cleaned_linked, "updated_at": now}}
                    )
            dashboard_user_id = partner.get("user_id")
            if dashboard_user_id and dashboard_user_id not in user_ids:
                record("partners", partner_id, "unset_orphan_dashboard_user", dashboard_user_id)
                if apply:
                    await db.partners.update_one(
                        {"_id": partner["_id"]}, {"$unset": {"user_id": ""}, "$set": {"updated_at": now}}
                    )
            if partner.get("is_active", True) and not partner.get("survey_ids"):
                tags = set(partner.get("tags") or [])
                inferred_surveys = sorted({
                    step.get("survey_id") for step in selection_steps
                    if step.get("survey_id") and step.get("filter_tag") in tags
                })
                if inferred_surveys:
                    record("partners", partner_id, "restore_survey_assignment_from_service_steps", inferred_surveys)
                    if apply:
                        await db.partners.update_one({"_id": partner["_id"]}, {"$set": {
                            "survey_ids": inferred_surveys, "registration_status": "active",
                            "is_active": True, "updated_at": now,
                        }})

        for user in users:
            partner_id = user.get("partner_id")
            if partner_id and partner_id not in partner_ids:
                record("users", user["_id"], "unset_orphan_partner_id", partner_id)
                if apply:
                    await db.users.update_one(
                        {"_id": user["_id"]}, {"$unset": {"partner_id": ""}, "$set": {"updated_at": now}}
                    )

    report["counts"] = dict(sorted(report["counts"].items()))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist the reported repairs")
    parser.add_argument("--user-email", help="Limit progress/submission checks to one user")
    parser.add_argument("--json", action="store_true", help="Print the complete JSON report")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    load_dotenv("/app/backend/.env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    try:
        report = await audit_and_repair(
            client[os.environ["DB_NAME"]], apply=args.apply, user_email=args.user_email
        )
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        else:
            print(f"Partner reference audit ({report['mode']}, scope={report['scope']})")
            for key, value in report["counts"].items():
                print(f"  {key}: {value}")
            print(f"Total actions: {len(report['actions'])}")
            if not args.apply:
                print("No data changed. Review with --json; apply explicitly with --apply.")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
