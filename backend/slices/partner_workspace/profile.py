"""Partner profile and organization self-service workflows."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast

from infrastructure.mongo_ids import object_id_or_none


class PartnerProfileNotLinked(ValueError): pass


class PartnerProfileRepository(Protocol):
    async def partner(self, partner_id: str) -> dict[str, Any] | None: ...
    async def update_partner(self, partner_id: str, fields: Mapping[str, Any]) -> None: ...


class MongoPartnerProfileRepository:
    def __init__(self, database: Any) -> None:
        self._database = database

    async def partner(self, partner_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id)
        if object_id is None:
            return None
        return cast(dict[str, Any] | None, await self._database.partners.find_one({"_id": object_id}))

    async def update_partner(self, partner_id: str, fields: Mapping[str, Any]) -> None:
        object_id = object_id_or_none(partner_id)
        if object_id is not None:
            await self._database.partners.update_one({"_id": object_id}, {"$set": dict(fields)})


class PartnerProfileService:
    def __init__(self, repository: PartnerProfileRepository) -> None:
        self._repository = repository

    async def profile(self, user: Mapping[str, Any]) -> dict[str, Any]:
        base = {"name": user["name"], "email": user["email"]}
        partner_id = user.get("partner_id")
        if not partner_id:
            return {**base, "partner_name": None, "partner_id": None}
        partner = await self._repository.partner(str(partner_id))
        if partner is None:
            return {**base, "partner_name": None, "partner_id": partner_id}
        return {
            **base, "partner_name": partner.get("name"), "partner_id": str(partner_id),
            "description": partner.get("description", ""), "category": partner.get("category", ""),
            "tags": partner.get("tags", []), "logo_url": partner.get("logo_url", ""),
            "survey_ids": partner.get("survey_ids", []),
            "registration_status": partner.get("registration_status", "active"),
            "registration_source": partner.get("registration_source", "admin"),
            "is_active": partner.get("is_active", True),
        }

    async def update_organization(
        self, user: Mapping[str, Any], values: Mapping[str, Any], timestamp: str,
    ) -> tuple[str, list[str]]:
        partner_id = user.get("partner_id")
        if not partner_id:
            raise PartnerProfileNotLinked
        fields = {key: value for key, value in values.items() if value is not None}
        if "tags" in fields:
            fields["tags"] = sorted({
                value.strip() for value in fields["tags"]
                if isinstance(value, str) and value.strip()
            })
        fields["updated_at"] = timestamp
        await self._repository.update_partner(str(partner_id), fields)
        return str(partner_id), list(fields)
