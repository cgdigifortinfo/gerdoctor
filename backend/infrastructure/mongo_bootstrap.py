"""MongoDB schema/index initialization for the application lifecycle."""
from __future__ import annotations

from typing import Any


async def initialize_mongo_schema(database: Any) -> None:
    """Create indexes and migrate deleted-user login addresses idempotently."""
    await database.users.update_many(
        {"is_deleted": True, "archived_original_email": {"$exists": False}},
        [{"$set": {
            "archived_original_email": "$email",
            "email": {"$concat": ["deleted+", {"$toString": "$_id"}, "+", "$email"]},
        }}],
    )
    indexes: tuple[tuple[Any, Any, dict[str, Any]], ...] = (
        (database.users, "email", {"unique": True}),
        (database.surveys, "slug", {"unique": True}),
        (database.password_reset_tokens, "expires_at", {"expireAfterSeconds": 0}),
        (database.login_attempts, "identifier", {}),
        (database.users, [("role", 1), ("survey_id", 1)], {}),
        (database.users, "partner_id", {}),
        (database.users, [("role", 1), ("created_at", -1)], {}),
        (database.surveys, [("is_active", 1), ("is_default", 1)], {}),
        (database.permission_groups, "key", {"unique": True}),
        (database.permission_groups, "name_key", {"unique": True}),
        (database.steps, [("survey_id", 1), ("is_active", 1), ("order", 1)], {}),
        (database.steps, [("is_active", 1), ("order", 1)], {}),
        (database.user_progress, [("user_id", 1), ("step_id", 1)], {"unique": True}),
        (database.user_progress, [("user_id", 1), ("survey_id", 1)], {}),
        (database.user_progress, [("user_id", 1), ("step_order", 1)], {}),
        (database.user_progress, [("step_id", 1), ("status", 1)], {}),
        (database.user_progress, [("user_id", 1), ("status", 1), ("step_order", 1)], {}),
        (database.partner_submissions, [("partner_id", 1), ("user_id", 1)], {}),
        (database.partner_submissions, [("user_id", 1), ("partner_id", 1)], {}),
        (database.partner_submissions, [("user_id", 1), ("step_id", 1), ("partner_id", 1)], {"unique": True}),
        (database.partner_submissions, [("partner_id", 1), ("created_at", -1)], {}),
        (database.partner_usage_charges, [("partner_id", 1), ("user_id", 1), ("service_step_id", 1)], {"unique": True}),
        (database.partner_usage_charges, [("partner_id", 1), ("status", 1), ("created_at", -1)], {}),
        (database.files, "id", {"unique": True}),
        (database.files, [("user_id", 1), ("created_at", -1)], {}),
        (database.partners, "name", {}),
        (database.partners, [("is_active", 1), ("tags", 1)], {}),
        (database.partners, [("registration_status", 1), ("registered_at", -1)], {}),
        (database.progress_history, [("user_id", 1), ("timestamp", -1)], {}),
        (database.step_versions, [("step_id", 1), ("version", 1)], {"unique": True}),
        (database.user_progress_revisions, [("user_id", 1), ("step_id", 1), ("revision", 1)], {"unique": True}),
        (database.user_progress_revisions, [("user_id", 1), ("created_at", -1)], {}),
        (database.document_bindings, [("file_id", 1), ("user_id", 1), ("step_id", 1), ("step_version", 1), ("progress_revision", 1), ("field_path", 1)], {"unique": True}),
        (database.document_bindings, [("user_id", 1), ("step_id", 1)], {}),
    )
    usage_indexes = await database.partner_usage_charges.index_information()
    legacy = next((name for name, spec in usage_indexes.items()
                   if spec.get("key") == [("partner_id", 1), ("user_id", 1)]), None)
    if legacy:
        await database.partner_usage_charges.drop_index(legacy)
    for collection, keys, options in indexes:
        await collection.create_index(keys, **options)
