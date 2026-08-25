"""Administrative user list, detail and export read models."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol
import csv, io


class AdminUserListingRepository(Protocol):
    async def users(self, limit: int = 10000) -> list[dict[str, Any]]: ...
    async def groups(self) -> list[dict[str, Any]]: ...
    async def partners(self) -> list[dict[str, Any]]: ...
    async def partner_step_ids(self) -> set[str]: ...
    async def partner_progress(self, step_ids: set[str]) -> list[dict[str, Any]]: ...
    async def submissions(self) -> list[dict[str, Any]]: ...
    async def detail(self, user_id: str) -> tuple[
        dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]],
    ] | None: ...
    async def active_steps(self) -> list[dict[str, Any]]: ...
    async def progress(self, user_id: str) -> list[dict[str, Any]]: ...

Statuses=Callable[[list[str],str,str],Awaitable[dict[str,dict[str,Any]]]]
Metrics=Callable[[list[str]],Awaitable[dict[str,dict[str,Any]]]]
RevisionView=Callable[[str],Awaitable[list[dict[str,Any]]]]
UserValue=Callable[[Mapping[str,Any]],Awaitable[Any]]

class AdminUserListingService:
    def __init__(self,repository: AdminUserListingRepository,statuses: Statuses,metrics: Metrics,
                 revisions: RevisionView,completion: Callable[[str],Awaitable[int]],groups: UserValue,
                 permissions: UserValue,primary_admin_email: str) -> None:
        self._repo,self._statuses,self._metrics=repository,statuses,metrics
        self._revisions,self._completion,self._groups,self._permissions=revisions,completion,groups,permissions
        self._primary=primary_admin_email
    async def users(self) -> list[dict[str,Any]]:
        users=await self._repo.users(); groups=await self._repo.groups(); partners=await self._repo.partners()
        group_by_id={str(g["_id"]):g for g in groups}; partner_by_id={str(p["_id"]):p for p in partners}
        partner_name_by_key={str(p.get("name","")).strip().casefold():p.get("name","") for p in partners if str(p.get("name","")).strip()}
        linked: dict[str,list[str]]={}
        for partner_row in partners:
            for uid in partner_row.get("linked_user_ids") or []: linked.setdefault(uid,[]).append(str(partner_row.get("name","")))
        step_ids=await self._repo.partner_step_ids(); progress_by_user: dict[str,list[dict[str,Any]]]={}
        for row in await self._repo.partner_progress(step_ids): progress_by_user.setdefault(str(row.get("user_id")),[]).append(row)
        submissions=await self._repo.submissions(); by_partner: dict[str,list[dict[str,Any]]]={}; ids_by_user: dict[str,set[str]]={}
        for row in submissions:
            pid,uid=row.get("partner_id"),row.get("user_id")
            if pid: by_partner.setdefault(str(pid),[]).append(row)
            if pid and uid: ids_by_user.setdefault(str(uid),set()).add(str(pid))
        pending: dict[str,int]={}
        for partner_row in partners:
            pid=str(partner_row["_id"]); candidates={str(x["user_id"]) for x in by_partner.get(pid,[]) if x.get("user_id")}
            candidates.update(str(x) for x in (partner_row.get("linked_user_ids") or []))
            statuses=await self._statuses(list(candidates),pid,str(partner_row.get("name","")))
            pending[pid]=sum(1 for uid in candidates if not statuses.get(uid,{}).get("completed",False))
        metrics=await self._metrics([str(u["_id"]) for u in users if u.get("role")=="user"]); result=[]
        for user in users:
            uid=str(user["_id"]); names=[]; orphaned=[]
            partner_id=user.get("partner_id")
            if user.get("role")=="partner" and partner_id:
                selected_partner=partner_by_id.get(str(partner_id))
                if selected_partner: names.append(str(selected_partner.get("name","")))
                else: orphaned.append({"type":"partner_id","value":str(partner_id)})
            for name in linked.get(uid,[]):
                if name and name not in names: names.append(name)
            if user.get("role")=="user" and step_ids:
                for row in progress_by_user.get(uid,[]):
                    data=row.get("data") or {}; selected=data.get("selected_partner_id"); many=data.get("selected_partner_ids") or []
                    for pid in ([selected] if selected else [])+list(many):
                        selected_partner=partner_by_id.get(str(pid))
                        if selected_partner:
                            name=str(selected_partner.get("name",""));
                            if name not in names: names.append(name)
                        else: orphaned.append({"type":"partner_id","value":str(pid)})
                    legacy=data.get("selected_partner_name")
                    if legacy and not selected and not many:
                        canonical=partner_name_by_key.get(str(legacy).strip().casefold())
                        if canonical:
                            if canonical not in names: names.append(str(canonical))
                        else: orphaned.append({"type":"legacy_name","value":str(legacy)})
            registrations=None
            if user.get("role")=="partner" and partner_id: registrations=pending.get(str(partner_id),0)
            elif user.get("role")=="user" and ids_by_user.get(uid): registrations=sum(pending.get(pid,0) for pid in ids_by_user[uid])
            metric=metrics.get(uid,{"completion_pct":0,"estimated_completion":None})
            result.append({"id":uid,"email":user["email"],"name":user["name"],"role":user["role"],"created_at":user.get("created_at"),
                "survey_id":user.get("survey_id"),"survey_slug":user.get("survey_slug"),**metric,"partner_names":names,
                "orphaned_partner_references":list({(x["type"],x["value"]):(x) for x in orphaned}.values()),
                "pending_registrations":registrations,"group_ids":user.get("group_ids",[]),
                "permission_groups":[{"id":gid,"name":group_by_id[gid].get("name",""),"role":group_by_id[gid].get("role","user")} for gid in user.get("group_ids",[]) if gid in group_by_id],
                "permission_overrides":user.get("permission_overrides",{"allow":[],"deny":[]}),
                "partner_registration_status":partner_by_id.get(str(partner_id),{}).get("registration_status") if partner_id else None,
                "partner_is_active":partner_by_id.get(str(partner_id),{}).get("is_active") if partner_id else None})
        return result
    async def detail(self,user_id: str) -> dict[str,Any] | None:
        loaded=await self._repo.detail(user_id)
        if loaded is None: return None
        user,progress,submissions,history=loaded; revisions=await self._revisions(user_id)
        latest={(row["step_id"],row["revision"]):row for row in revisions}
        progress=[{**row,**{key:latest.get((row.get("step_id"),row.get("revision")),{}).get(key) for key in
            ("current_step_version","configuration_changed","step_deleted","step_snapshot","removed_field_names")}} for row in progress]
        return {"id":str(user["_id"]),"email":user["email"],"name":user["name"],"role":user["role"],"profile":user.get("profile",{}),
            "survey_id":user.get("survey_id"),"survey_slug":user.get("survey_slug"),"created_at":user.get("created_at"),"progress":progress,
            "revisions":revisions,"submissions":submissions,"history":history,"completion_pct":await self._completion(user_id),
            "group_ids":user.get("group_ids",[]),"permission_groups":await self._groups(user),"permission_overrides":user.get("permission_overrides",{"allow":[],"deny":[]}),
            "effective_permissions":await self._permissions(user),"is_primary_admin":user.get("email")==self._primary}
    async def csv_export(self) -> str:
        users=await self._repo.users(10000); steps=await self._repo.active_steps(); output=io.StringIO(); writer=csv.writer(output)
        writer.writerow(["Name","Email","Role","Created At"]+[str(s["title"]) for s in steps])
        for user in users:
            progress={row["step_id"]:row["status"] for row in await self._repo.progress(str(user["_id"]))}
            writer.writerow([user.get("name",""),user.get("email",""),user.get("role",""),user.get("created_at","")]+[progress.get(str(s["_id"]),"not_started") for s in steps])
        return output.getvalue()
