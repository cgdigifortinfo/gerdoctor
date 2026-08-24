import asyncio
import os

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from repair_partner_references import (
    audit_and_repair,
    build_partner_lookups,
    repair_progress_partner_data,
)


def _lookups(*names):
    partners = [{"_id": ObjectId(), "name": name} for name in names]
    names_by_id, ids_by_name = build_partner_lookups(partners)
    return partners, names_by_id, ids_by_name


def test_valid_id_is_authoritative_and_name_is_canonicalized():
    partners, names_by_id, ids_by_name = _lookups("Alpha Partner")
    partner_id = str(partners[0]["_id"])
    corrected, actions = repair_progress_partner_data(
        {"selected_partner_id": partner_id, "selected_partner_name": "Old label", "note": "keep"},
        names_by_id,
        ids_by_name,
    )
    assert corrected == {
        "selected_partner_id": partner_id,
        "selected_partner_name": "Alpha Partner",
        "note": "keep",
    }
    assert actions == [{"action": "canonicalize_name", "value": "Alpha Partner"}]


def test_unique_legacy_name_is_resolved_case_insensitively():
    partners, names_by_id, ids_by_name = _lookups("Ärzte Hilfe")
    corrected, actions = repair_progress_partner_data(
        {"selected_partner_name": "  ÄRZTE HILFE  "}, names_by_id, ids_by_name
    )
    assert corrected["selected_partner_id"] == str(partners[0]["_id"])
    assert corrected["selected_partner_name"] == "Ärzte Hilfe"
    assert actions[0]["action"] == "resolve_legacy_name"


def test_unknown_legacy_name_is_removed_without_deleting_other_step_data():
    _, names_by_id, ids_by_name = _lookups("Real Partner")
    corrected, actions = repair_progress_partner_data(
        {"selected_partner_name": "Demo Partner", "comment": "retain this"},
        names_by_id,
        ids_by_name,
    )
    assert corrected == {"comment": "retain this"}
    assert actions == [{"action": "remove_orphan_name", "value": "Demo Partner"}]


def test_stale_id_can_be_repaired_only_by_a_unique_matching_name():
    partners, names_by_id, ids_by_name = _lookups("Recoverable")
    stale_id = str(ObjectId())
    corrected, actions = repair_progress_partner_data(
        {"selected_partner_id": stale_id, "selected_partner_name": "recoverable"},
        names_by_id,
        ids_by_name,
    )
    assert corrected["selected_partner_id"] == str(partners[0]["_id"])
    assert actions == [{"action": "replace_stale_id", "value": stale_id}]


def test_ambiguous_duplicate_name_is_not_guessed():
    _, names_by_id, ids_by_name = _lookups("Same Name", "same name")
    corrected, actions = repair_progress_partner_data(
        {"selected_partner_name": "Same Name"}, names_by_id, ids_by_name
    )
    assert corrected == {}
    assert actions[0]["action"] == "remove_orphan_name"


def test_multi_selection_deduplicates_valid_ids_and_removes_orphans():
    partners, names_by_id, ids_by_name = _lookups("Alpha", "Beta")
    alpha_id = str(partners[0]["_id"])
    stale_id = str(ObjectId())
    corrected, actions = repair_progress_partner_data(
        {
            "selected_partner_ids": [alpha_id, stale_id, alpha_id],
            "selected_partner_names": "Wrong, Historic",
        },
        names_by_id,
        ids_by_name,
    )
    assert corrected["selected_partner_ids"] == [alpha_id]
    assert corrected["selected_partner_names"] == "Alpha"
    assert {item["value"] for item in actions} == {stale_id}


def test_name_only_multi_selection_resolves_known_and_discards_unknown_names():
    partners, names_by_id, ids_by_name = _lookups("Alpha", "Beta")
    corrected, actions = repair_progress_partner_data(
        {"selected_partner_names": "beta, Missing, Alpha"}, names_by_id, ids_by_name
    )
    assert corrected["selected_partner_ids"] == [
        str(partners[1]["_id"]),
        str(partners[0]["_id"]),
    ]
    assert corrected["selected_partner_names"] == "Beta, Alpha"
    assert any(item == {"action": "remove_orphan_multi_name", "value": "Missing"} for item in actions)


def test_dry_run_preserves_and_apply_deletes_only_unreferenced_records():
    async def scenario():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        orphan_progress_id = ObjectId()
        orphan_submission_id = ObjectId()
        valid_submission_id = ObjectId()
        try:
            user = await db.users.find_one({"role": "user"}, {"_id": 1})
            partner = await db.partners.find_one({}, {"_id": 1})
            step = await db.steps.find_one({}, {"_id": 1})
            assert user and partner and step
            await db.user_progress.insert_one({
                "_id": orphan_progress_id,
                "user_id": str(ObjectId()),
                "step_id": str(step["_id"]),
                "status": "pending",
                "data": {},
            })
            await db.partner_submissions.insert_many([
                {
                    "_id": orphan_submission_id,
                    "id": f"repair-test-orphan-{orphan_submission_id}",
                    "user_id": str(ObjectId()),
                    "partner_id": str(partner["_id"]),
                    "status": "submitted",
                },
                {
                    "_id": valid_submission_id,
                    "id": f"repair-test-valid-{valid_submission_id}",
                    "user_id": str(user["_id"]),
                    "partner_id": str(partner["_id"]),
                    "status": "submitted",
                },
            ])

            dry_run = await audit_and_repair(db, apply=False)
            assert dry_run["counts"]["user_progress.delete_orphan_record"] >= 1
            assert dry_run["counts"]["partner_submissions.delete_orphan_record"] >= 1
            assert await db.user_progress.find_one({"_id": orphan_progress_id})
            assert await db.partner_submissions.find_one({"_id": orphan_submission_id})
            assert await db.partner_submissions.find_one({"_id": valid_submission_id})

            await audit_and_repair(db, apply=True)
            assert await db.user_progress.find_one({"_id": orphan_progress_id}) is None
            assert await db.partner_submissions.find_one({"_id": orphan_submission_id}) is None
            assert await db.partner_submissions.find_one({"_id": valid_submission_id}) is not None
        finally:
            await db.user_progress.delete_one({"_id": orphan_progress_id})
            await db.partner_submissions.delete_many({
                "_id": {"$in": [orphan_submission_id, valid_submission_id]}
            })
            client.close()

    asyncio.run(scenario())
