"""Read-model repository for administrative user views and exports."""
from __future__ import annotations
from typing import Any, cast
from infrastructure.mongo_ids import object_id_or_none

class MongoAdminUserListingRepository:
    def __init__(self,database: Any) -> None: self._db=database
    async def users(self,limit: int=10000) -> list[dict[str,Any]]:
        return cast(list[dict[str,Any]],await self._db.users.find({}, {"password_hash":0}).to_list(limit))
    async def groups(self) -> list[dict[str,Any]]:
        return cast(list[dict[str,Any]],await self._db.permission_groups.find({}, {"name":1,"role":1}).to_list(500))
    async def partners(self) -> list[dict[str,Any]]:
        return cast(list[dict[str,Any]],await self._db.partners.find({}, {"name":1,"linked_user_ids":1,"registration_status":1,"is_active":1}).to_list(1000))
    async def partner_step_ids(self) -> set[str]:
        rows=await self._db.steps.find({"step_type":{"$in":["partner_selection","partner_multiselection"]}},{"_id":1}).to_list(1000)
        return {str(row["_id"]) for row in rows}
    async def partner_progress(self,step_ids: set[str]) -> list[dict[str,Any]]:
        if not step_ids: return []
        return cast(list[dict[str,Any]],await self._db.user_progress.find({"step_id":{"$in":list(step_ids)}},{"user_id":1,"data":1}).to_list(20000))
    async def submissions(self) -> list[dict[str,Any]]:
        return cast(list[dict[str,Any]],await self._db.partner_submissions.find({},{"user_id":1,"partner_id":1}).to_list(20000))
    async def detail(self,user_id: str) -> tuple[dict[str,Any],list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]]] | None:
        oid=object_id_or_none(user_id)
        if oid is None: return None
        user=await self._db.users.find_one({"_id":oid},{"password_hash":0})
        if not user: return None
        progress=await self._db.user_progress.find({"user_id":user_id},{"_id":0}).to_list(100)
        submissions=await self._db.partner_submissions.find({"user_id":user_id},{"_id":0}).to_list(100)
        history=await self._db.progress_history.find({"user_id":user_id},{"_id":0}).sort("timestamp",-1).to_list(200)
        return cast(dict[str,Any],user),cast(list[dict[str,Any]],progress),cast(list[dict[str,Any]],submissions),cast(list[dict[str,Any]],history)
    async def active_steps(self) -> list[dict[str,Any]]:
        return cast(list[dict[str,Any]],await self._db.steps.find({"is_active":True}).sort("order",1).to_list(100))
    async def progress(self,user_id: str) -> list[dict[str,Any]]:
        return cast(list[dict[str,Any]],await self._db.user_progress.find({"user_id":user_id},{"_id":0}).to_list(100))
