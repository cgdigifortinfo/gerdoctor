"""Application service for user-owned survey progress commands."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from slices.survey_runtime.progress import validate_completion


class ProgressStepNotFound(ValueError): pass


class SurveyProgressRepository(Protocol):
    async def step(self, step_id: str) -> dict[str, Any] | None: ...
    async def progress(self, user_id: str, step_id: str) -> dict[str, Any] | None: ...
    async def step_count(self, survey_id: str) -> int: ...
    async def history(self, document: Mapping[str, Any]) -> None: ...


@dataclass(frozen=True)
class ProgressCommand:
    step_id: str
    status: str
    data: Mapping[str, Any]


WriteRevision = Callable[..., Awaitable[Any]]
SendEmail = Callable[..., Awaitable[Any]]


class SurveyProgressService:
    def __init__(
        self, repository: SurveyProgressRepository,
        assert_editable: Callable[[str, Mapping[str, Any]], Awaitable[None]],
        default_survey: Callable[[], Awaitable[Mapping[str, Any]]],
        write_revision: WriteRevision, send_email: SendEmail,
        auto_complete: Callable[[str], Awaitable[Any]],
        now_iso: Callable[[], str], content_field_types: frozenset[str],
    ) -> None:
        self._repo, self._editable, self._default = repository, assert_editable, default_survey
        self._write, self._email = write_revision, send_email
        self._auto = auto_complete
        self._now, self._content = now_iso, content_field_types

    async def update(self, user: Mapping[str, Any], command: ProgressCommand) -> None:
        step = await self._repo.step(command.step_id)
        if step is None:
            raise ProgressStepNotFound
        user_id = str(user["_id"])
        existing = await self._repo.progress(user_id, command.step_id)
        await self._editable(user_id, step)
        if command.status == "completed" and not command.data.get("skipped"):
            validate_completion(step, command.data, self._content)

        preferences = user.get("notification_preferences") or {
            "email_on_step_enter": True, "email_on_step_edit": False,
            "email_on_step_leave": True,
        }
        survey_id = step.get("survey_id") or user.get("survey_id")
        if not survey_id:
            survey_id = str((await self._default())["_id"])
        variables = {
            "user_name": user["name"], "user_email": user["email"],
            "step_title": step["title"], "step_order": step["order"],
            "step_description": step.get("description", ""),
            "total_steps": await self._repo.step_count(str(survey_id)),
        }
        if existing and step.get("email_on_edit") and command.data and preferences.get("email_on_step_edit", False):
            await self._send(user, "user_step_updated", variables, step, "edit")
        if not existing and step.get("email_on_enter") and preferences.get("email_on_step_enter", True):
            await self._send(user, "user_step_entered", variables, step, "enter")
        if command.status == "completed" and step.get("email_on_leave") and preferences.get("email_on_step_leave", True):
            await self._send(user, "user_step_completed", variables, step, "leave")

        now = self._now()
        extra: dict[str, Any] = {"survey_id": str(survey_id)}
        if (not existing or not existing.get("started_at")) and command.status in {"in_progress", "completed"}:
            extra["started_at"] = now
        if command.status == "completed":
            extra["completed_at"] = now
        await self._write(
            user_id=user_id, step=step, status=command.status, data=dict(command.data),
            actor={"id": user_id, "email": user.get("email", ""), "role": user.get("role", "user")},
            change_type="user_update", extra_fields=extra,
        )
        await self._repo.history({
            "user_id": user_id, "step_id": command.step_id, "step_title": step["title"],
            "step_order": step["order"], "action": command.status, "timestamp": now,
        })
        # A form answer must only complete the addressed step. Recognition
        # status is ordinary survey data and must never bulk-complete future
        # blocks as an implicit side effect of the user progress endpoint.
        await self._auto(user_id)

    async def _send(self, user: Mapping[str, Any], template: str, variables: Mapping[str, Any],
                    step: Mapping[str, Any], suffix: str) -> None:
        await self._email(
            str(user["email"]), template, dict(variables),
            override_subject=step.get(f"email_subject_{suffix}") or "",
            override_body=step.get(f"email_body_{suffix}") or "",
        )
