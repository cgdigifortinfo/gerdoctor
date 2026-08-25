"""MongoDB adapter for partner selection queries."""
from __future__ import annotations

from typing import Any, cast

from infrastructure.mongo_ids import object_id_or_none, valid_object_ids

from slices.partner_selection.mappers import selectable_partner_from_document, selection_step_from_document
from slices.partner_selection.models import SelectablePartner, SelectionStep


class MongoPartnerSelectionRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def find_step(self, step_id: str) -> SelectionStep | None:
        object_id = object_id_or_none(step_id)
        if object_id is None:
            return None
        document = await self._db.steps.find_one({"_id": object_id, "is_deleted": {"$ne": True}})
        return selection_step_from_document(document) if document else None

    async def find_partners(self, partner_ids: tuple[str, ...]) -> tuple[SelectablePartner, ...]:
        object_ids = valid_object_ids(partner_ids)
        if not object_ids:
            return ()
        documents = await self._db.partners.find({"_id": {"$in": object_ids}}).to_list(len(object_ids))
        return tuple(selectable_partner_from_document(document) for document in documents)

    async def list_active_partners(self, tag: str) -> tuple[SelectablePartner, ...]:
        query: dict[str, Any] = {"is_active": True}
        if tag:
            query["tags"] = tag
        documents = await self._db.partners.find(query).to_list(1000)
        return tuple(selectable_partner_from_document(document) for document in documents)

    async def partner_document(self, partner_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id)
        return await self._db.partners.find_one({"_id": object_id}) if object_id else None

    async def remove_other_submissions(
        self, user_id: str, step_id: str, partner_ids: tuple[str, ...],
    ) -> None:
        await self._db.partner_submissions.delete_many({
            "user_id": user_id, "step_id": step_id,
            "partner_id": {"$nin": list(partner_ids)},
        })

    async def submission(
        self, user_id: str, partner_id: str, step_id: str | None,
    ) -> dict[str, Any] | None:
        query: dict[str, Any] = {"user_id": user_id, "partner_id": partner_id}
        if step_id is not None:
            query["step_id"] = step_id
        return cast(dict[str, Any] | None, await self._db.partner_submissions.find_one(query))

    async def update_submission(self, document_id: Any, fields: dict[str, Any]) -> None:
        await self._db.partner_submissions.update_one({"_id": document_id}, {"$set": fields})

    async def insert_submission(self, document: dict[str, Any]) -> None:
        await self._db.partner_submissions.insert_one(document)
