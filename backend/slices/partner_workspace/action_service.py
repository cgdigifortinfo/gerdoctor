"""Approve/reject commands for partner-managed steps."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from slices.partner_workspace.command_repository import MongoPartnerWorkspaceCommandRepository
from slices.partner_workspace.domain import (
    adjacent_visible_step, merge_progress_data, new_partner_uploads,
    validate_workspace_action,
)
from slices.partner_workspace.mappers import workspace_step_from_document
from slices.partner_workspace.read_service import PartnerNotLinked


class WorkspaceActionStepNotFound(ValueError): pass
class WorkspaceActionStepNotManaged(ValueError): pass


@dataclass(frozen=True)
class WorkspaceActionCommand:
    action: str
    reason: str | None
    data: Mapping[str, Any] | None


class PartnerWorkspaceActionService:
    def __init__(
        self, repository: MongoPartnerWorkspaceCommandRepository,
        context: Callable[[str, str, Mapping[str, Any] | None], Awaitable[tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[str]]]],
        write_revision: Callable[..., Awaitable[Any]], emit: Callable[..., Awaitable[Any]],
        record_charge: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any] | None], Awaitable[Any]],
        service_step: Callable[[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], Mapping[str, Any]], Mapping[str, Any] | None],
        auto_complete: Callable[[str], Awaitable[Any]],
        visibility: Callable[[str], Awaitable[tuple[list[dict[str, Any]], Any, set[str], Any]]],
        audit: Callable[..., Awaitable[Any]], now_iso: Callable[[], str],
    ) -> None:
        self._repo, self._context, self._write, self._emit = repository, context, write_revision, emit
        self._charge, self._service_step, self._auto = record_charge, service_step, auto_complete
        self._visibility, self._audit, self._now = visibility, audit, now_iso

    async def execute(self, actor: Mapping[str, Any], user_id: str, step_id: str,
                      command: WorkspaceActionCommand) -> dict[str, Any]:
        partner_id_value = actor.get("partner_id")
        if not partner_id_value: raise PartnerNotLinked
        partner_id = str(partner_id_value)
        action = validate_workspace_action(command.action, command.reason)
        partner = await self._repo.partner(partner_id)
        target, progress, steps, managed = await self._context(user_id, partner_id, partner)
        if step_id not in managed: raise WorkspaceActionStepNotManaged
        step = next((row for row in steps if row.get("id") == step_id), None)
        if step is None: raise WorkspaceActionStepNotFound
        existing = next((row for row in progress if row.get("step_id") == step_id), {})
        old_data = existing.get("data") or {}; merged = merge_progress_data(old_data, command.data)
        partner_name = str((partner or {}).get("name") or actor.get("name") or "Partner")
        now = self._now()
        event_base = {
            "user_id": user_id, "user_name": target.get("name", ""), "user_email": target.get("email", ""),
            "user_email_notifications_enabled": (target.get("notification_preferences") or {}).get("email_on_step_leave", True),
            "partner_id": partner_id, "partner_name": partner_name, "step_id": step_id,
            "step_title": step.get("title", ""), "milestone_title": step.get("title", ""),
            "step_order": step.get("order", 0), "step_description": step.get("description", ""),
        }
        events = []
        uploads = new_partner_uploads(old_data, merged)
        actor_data = {"id": str(actor.get("_id") or ""), "email": actor.get("email", ""),
                      "role": "partner", "partner_id": partner_id, "partner_name": partner_name}
        for upload in uploads:
            events.append(await self._emit("partner.document.uploaded", {
                **event_base, "file_id": upload.file_id, "filename": upload.filename,
            }, actor_data))
        if uploads and partner:
            service_step = self._service_step(steps, progress, step, partner)
            await self._charge(partner, target, uploads[0].document, service_step)

        reopened: dict[str, Any] | None = None
        if action.value == "complete":
            was_rejected = bool(old_data.get("partner_rejection")); merged.pop("partner_rejection", None)
            await self._write(user_id=user_id, step=step, status="completed", data=merged, actor=actor_data,
                              change_type="partner_complete", extra_fields={"completed_at": now})
            if was_rejected:
                _, _, hidden_before, _ = await self._visibility(user_id)
                corrected = adjacent_visible_step(
                    (workspace_step_from_document(row) for row in steps), workspace_step_from_document(step),
                    hidden_before, forward=False,
                )
                corrected_step = next((row for row in steps if corrected and row["id"] == corrected.id), None)
                if corrected_step:
                    current = await self._repo.progress(user_id, corrected_step["id"])
                    await self._repo.update_progress(user_id, corrected_step["id"], {"$set": {
                        "status": "completed", "started_at": (current or {}).get("started_at") or now,
                        "completed_at": now, "updated_at": now,
                    }})
            await self._auto(user_id)
            _, _, hidden, _ = await self._visibility(user_id)
            following = adjacent_visible_step(
                (workspace_step_from_document(row) for row in steps), workspace_step_from_document(step), hidden,
                forward=True,
            )
            next_step = next((row for row in steps if following and row["id"] == following.id), None)
            if next_step:
                current = await self._repo.progress(user_id, next_step["id"])
                if not current or current.get("status") != "completed":
                    await self._repo.update_progress(user_id, next_step["id"], {"$set": {
                        "user_id": user_id, "step_id": next_step["id"], "survey_id": target.get("survey_id"),
                        "step_order": next_step.get("order", 0), "status": "in_progress",
                        "started_at": (current or {}).get("started_at") or now, "updated_at": now,
                    }})
            events.append(await self._emit("partner.step.completed", event_base, actor_data))
            history_action, status = "completed_by_partner", "completed"
        else:
            _, _, hidden, _ = await self._visibility(user_id)
            previous = adjacent_visible_step(
                (workspace_step_from_document(row) for row in steps), workspace_step_from_document(step), hidden,
                forward=False,
            )
            reopened = next((row for row in steps if previous and row["id"] == previous.id), None)
            reason = str(command.reason or "").strip()
            merged["partner_rejection"] = {"reason": reason, "partner_id": partner_id,
                                           "partner_name": partner_name, "rejected_at": now}
            await self._write(user_id=user_id, step=step, status="pending", data=merged, actor=actor_data,
                              change_type="partner_reject", unset_fields=["completed_at"])
            if reopened:
                await self._repo.update_progress(user_id, reopened["id"], {"$set": {
                    "user_id": user_id, "step_id": reopened["id"], "survey_id": target.get("survey_id"),
                    "step_order": reopened.get("order", 0), "status": "in_progress", "updated_at": now,
                }, "$unset": {"completed_at": ""}})
            events.append(await self._emit("partner.step.rejected", {
                **event_base, "rejection_reason": reason,
                "reopened_step_id": reopened["id"] if reopened else "",
                "reopened_step_title": reopened.get("title", "") if reopened else "",
                "reopened_step_order": reopened.get("order", "") if reopened else "",
            }, actor_data))
            history_action, status = "rejected_by_partner", "pending"
        await self._repo.history({
            "user_id": user_id, "step_id": step_id, "step_title": step.get("title", ""),
            "step_order": step.get("order", 0), "action": history_action,
            "reason": command.reason or "", "changed_by": actor.get("email", ""),
            "partner_id": partner_id, "timestamp": now,
        })
        await self._audit(str(actor.get("_id") or ""), actor.get("email", ""), history_action,
                          "user_step", step_id, {"user_id": user_id, "step_order": step.get("order"),
                                                  "reason": command.reason or ""})
        return {"message": "Step completed" if status == "completed" else "Step rejected",
                "step_id": step_id, "status": status, "reopened_step": reopened, "events": events}
