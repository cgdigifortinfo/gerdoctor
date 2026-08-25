"""Partner-owned workspace commands."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol

from slices.partner_workspace.read_service import PartnerNotLinked
from slices.survey_runtime.progress_service import ProgressCommand


class ManagedMilestoneNotFound(ValueError): pass
class WorkspaceCommandStepNotFound(ValueError): pass
class WorkspaceStepNotManaged(ValueError): pass


class PartnerWorkspaceCommandRepository(Protocol):
    async def partner(self, partner_id: str) -> dict[str, Any] | None: ...
    async def step(self, step_id: str) -> dict[str, Any] | None: ...
    async def progress(self, user_id: str, step_id: str) -> dict[str, Any] | None: ...
    async def active_step_count(self) -> int: ...
    async def history(self, document: Mapping[str, Any], *, tolerant: bool = False) -> None: ...


class PartnerWorkspaceCommandService:
    def __init__(
        self, repository: PartnerWorkspaceCommandRepository,
        work_status: Callable[[str, str, str], Awaitable[Mapping[str, Any]]],
        write_revision: Callable[..., Awaitable[Any]], now_iso: Callable[[], str],
        workspace_context: Callable[[str, str, Mapping[str, Any] | None], Awaitable[tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[str]]]] | None = None,
        auto_complete: Callable[[str], Awaitable[Any]] | None = None,
        notify_completed: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], Awaitable[Any]] | None = None,
        send_email: Callable[..., Awaitable[Any]] | None = None,
        visibility: Callable[[str], Awaitable[tuple[list[dict[str, Any]], Any, set[str], Any]]] | None = None,
    ) -> None:
        self._repo, self._status, self._write, self._now = repository, work_status, write_revision, now_iso
        self._context, self._auto = workspace_context, auto_complete
        self._notify, self._email, self._visibility = notify_completed, send_email, visibility

    async def reopen(self, actor: Mapping[str, Any], user_id: str) -> str:
        partner_id_value = actor.get("partner_id")
        if not partner_id_value: raise PartnerNotLinked
        partner_id = str(partner_id_value)
        partner = await self._repo.partner(partner_id)
        partner_name = str((partner or {}).get("name") or "")
        status = await self._status(user_id, partner_id, partner_name)
        milestone_id = str(status.get("milestone_step_id") or "")
        if not milestone_id: raise ManagedMilestoneNotFound
        step = await self._repo.step(milestone_id)
        if step is None: raise ManagedMilestoneNotFound
        existing = await self._repo.progress(user_id, milestone_id)
        await self._write(
            user_id=user_id, step=step, status="in_progress", data=(existing or {}).get("data") or {},
            actor={"id": str(actor["_id"]), "email": actor["email"], "role": "partner", "partner_id": partner_id},
            change_type="partner_reopen", unset_fields=["completed_at"],
        )
        await self._repo.history({
            "user_id": user_id, "step_id": milestone_id, "action": "reopened_by_partner",
            "partner_id": partner_id, "partner_name": partner_name, "actor": actor["email"],
            "created_at": self._now(),
        }, tolerant=True)
        return milestone_id

    async def update_progress(self, actor: Mapping[str, Any], user_id: str,
                              command: ProgressCommand) -> None:
        partner_id_value = actor.get("partner_id")
        if not partner_id_value: raise PartnerNotLinked
        partner_id = str(partner_id_value)
        partner = await self._repo.partner(partner_id)
        assert self._context is not None
        target, progress, steps, managed = await self._context(user_id, partner_id, partner)
        if command.step_id not in managed: raise WorkspaceStepNotManaged
        step = next((row for row in steps if row.get("id") == command.step_id), None)
        if step is None: raise WorkspaceCommandStepNotFound
        existing = next((row for row in progress if row.get("step_id") == command.step_id), None)
        now = self._now()
        data = dict(command.data) if command.data else dict((existing or {}).get("data") or {})
        extra: dict[str, Any] = {"status": command.status, "updated_at": now}
        if not existing or not existing.get("started_at"): extra["started_at"] = now
        if command.status == "completed": extra["completed_at"] = now
        await self._write(
            user_id=user_id, step=step, status=command.status, data=data,
            actor={"id": str(actor.get("_id") or ""), "email": actor.get("email", ""),
                   "role": "partner", "partner_id": partner_id},
            change_type="partner_update", extra_fields=extra,
        )
        await self._repo.history({
            "user_id": user_id, "step_id": command.step_id, "step_title": step.get("title", ""),
            "step_order": step.get("order", 0), "action": command.status,
            "changed_by": actor["email"], "timestamp": now,
        })
        assert self._auto is not None
        await self._auto(user_id)
        if command.status != "completed": return
        preferences = target.get("notification_preferences") or {
            "email_on_step_enter": True, "email_on_step_edit": False, "email_on_step_leave": True,
        }
        partner_name = str((partner or {}).get("name", ""))
        variables = {
            "user_name": target["name"], "user_email": target["email"],
            "step_title": step["title"], "step_order": step["order"],
            "step_description": step.get("description", ""), "partner_name": partner_name,
            "milestone_title": step["title"], "total_steps": await self._repo.active_step_count(),
        }
        if preferences.get("email_on_step_leave", True):
            assert self._notify is not None
            await self._notify(target, partner or {}, step)
        if step.get("email_on_leave") and preferences.get("email_on_step_leave", True):
            assert self._email is not None
            await self._email(target["email"], "user_step_completed", variables,
                              override_subject=step.get("email_subject_leave") or "",
                              override_body=step.get("email_body_leave") or "")
        assert self._visibility is not None
        context_steps, _, hidden, _ = await self._visibility(user_id)
        next_step = next((row for row in context_steps
                          if row["order"] > step.get("order", 0) and str(row["_id"]) not in hidden), None)
        if next_step is None: return
        next_id = str(next_step["_id"]); next_progress = await self._repo.progress(user_id, next_id)
        if next_progress and next_progress.get("status") != "pending": return
        await self._write(
            user_id=user_id, step=next_step, status="in_progress", data=(next_progress or {}).get("data") or {},
            actor={"id": str(actor.get("_id") or ""), "email": actor.get("email", ""),
                   "role": "partner", "partner_id": partner_id},
            change_type="partner_unlocked_next_step",
        )
        if preferences.get("email_on_step_enter", True):
            assert self._email is not None
            await self._email(target["email"], "user_next_step_unlocked", {
                **variables, "step_title": next_step["title"], "step_order": next_step["order"],
                "step_description": next_step.get("description", ""),
            }, override_subject=next_step.get("email_subject_enter") or "",
               override_body=next_step.get("email_body_enter") or "")
