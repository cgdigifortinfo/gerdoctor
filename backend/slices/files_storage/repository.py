"""MongoDB adapter for file metadata and access relationships."""
from __future__ import annotations

from typing import Any

from infrastructure.mongo_ids import object_id_or_none
from slices.files_storage.models import StoredFile


class MongoFilesRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def insert(self, stored_file: StoredFile, created_at: str) -> None:
        await self._db.files.insert_one({
            "id": stored_file.id, "user_id": stored_file.user_id,
            "storage_path": stored_file.storage_path,
            "original_filename": stored_file.original_filename,
            "content_type": stored_file.content_type, "size": stored_file.size,
            "is_deleted": stored_file.is_deleted, "created_at": created_at,
        })

    async def find_active(self, file_id: str) -> StoredFile | None:
        document = await self._db.files.find_one({"id": file_id, "is_deleted": False})
        if document is None:
            return None
        return StoredFile(
            id=str(document["id"]), user_id=document.get("user_id"),
            storage_path=str(document["storage_path"]),
            original_filename=str(document.get("original_filename") or document.get("filename") or ""),
            content_type=str(document.get("content_type") or "application/octet-stream"),
            size=int(document.get("size") or 0), is_deleted=bool(document.get("is_deleted", False)),
        )

    async def user_references_file(self, user_id: str, file_id: str) -> bool:
        document = await self._db.user_progress.find_one({
            "user_id": user_id,
            "$or": [
                {"data.partner_uploads.file_id": file_id},
                {"data.documents.file_id": file_id},
            ],
        }, {"_id": 1})
        return document is not None

    async def partner_links_user(self, partner_id: str, user_id: str) -> bool:
        object_id = object_id_or_none(partner_id)
        if object_id is None:
            return False
        partner = await self._db.partners.find_one({"_id": object_id}, {"linked_user_ids": 1})
        return user_id in set((partner or {}).get("linked_user_ids", []))

    async def partner_submission_exists(self, partner_id: str, user_id: str) -> bool:
        document = await self._db.partner_submissions.find_one({
            "partner_id": partner_id, "user_id": user_id,
        }, {"_id": 1})
        return document is not None

    async def protect_owner_files(self, user_id: str, deleted_at: str) -> None:
        await self._db.files.update_many(
            {"user_id": user_id},
            {"$set": {"historical_protected": True, "owner_deleted_at": deleted_at}},
        )
