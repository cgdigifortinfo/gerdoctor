"""Partner workspace list read models."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol


class PartnerNotLinked(ValueError): pass


class PartnerWorkspaceReadRepository(Protocol):
    async def partner(self, partner_id: str) -> dict[str, Any] | None: ...
    async def submissions(self, partner_id: str) -> list[dict[str, Any]]: ...
    async def step_one_data(self, user_ids: set[str]) -> dict[str, dict[str, Any]]: ...
    async def users(self, user_ids: set[str] | None = None) -> list[dict[str, Any]]: ...
    async def submitted_user_ids(self, partner_id: str) -> set[str]: ...


Metrics = Callable[[list[str]], Awaitable[dict[str, dict[str, Any]]]]
Work = Callable[[list[str], str, str], Awaitable[dict[str, dict[str, Any]]]]
SubmissionWork = Callable[[list[dict[str, Any]]], Awaitable[dict[tuple[str, str], dict[str, Any]]]]
VisibleEmail = Callable[[Mapping[str, Any], Mapping[str, Any] | None, str], Awaitable[str]]


class PartnerWorkspaceReadService:
    def __init__(self, repository: PartnerWorkspaceReadRepository, metrics: Metrics,
                 work: Work, submission_work: SubmissionWork, visible_email: VisibleEmail) -> None:
        self._repo, self._metrics, self._work = repository, metrics, work
        self._submission_work, self._email = submission_work, visible_email

    async def submissions(self, actor: Mapping[str, Any]) -> list[dict[str, Any]]:
        partner_id = self._partner_id(actor)
        partner = await self._repo.partner(partner_id)
        partner_name = str((partner or {}).get("name") or "")
        linked = {str(value) for value in (partner or {}).get("linked_user_ids", [])}
        rows = await self._repo.submissions(partner_id)
        seen = {str(row["user_id"]) for row in rows if row.get("user_id")}
        target = seen | linked
        metrics = await self._metrics(list(target))
        work = await self._work(list(target), partner_id, partner_name)
        per_submission = await self._submission_work(rows)
        profile = await self._repo.step_one_data(target)
        for row in rows:
            row["user_email"] = await self._email(actor, partner, str(row.get("user_email", "")))
            user_id = str(row.get("user_id") or "")
            if not user_id: continue
            self._decorate(row, metrics.get(user_id, {}), per_submission.get(
                (user_id, str(row.get("step_id") or "")), work.get(user_id, {}),
            ), profile.get(user_id, {}))
        users = {str(row["_id"]): row for row in await self._repo.users(linked - seen)}
        for user_id in linked - seen:
            user = users.get(user_id)
            if not user: continue
            row = {
                "user_id": user_id, "user_name": user["name"],
                "user_email": await self._email(actor, partner, str(user["email"])),
                "partner_id": partner_id, "data": {"source": "linked"}, "status": "linked",
            }
            self._decorate(row, metrics.get(user_id, {}), work.get(user_id, {}), profile.get(user_id, {}))
            rows.append(row)
        return rows

    async def other_users(self, actor: Mapping[str, Any]) -> list[dict[str, Any]]:
        partner_id = self._partner_id(actor)
        partner = await self._repo.partner(partner_id)
        mine = {str(value) for value in (partner or {}).get("linked_user_ids", [])}
        mine.update(await self._repo.submitted_user_ids(partner_id))
        users = [row for row in await self._repo.users() if str(row["_id"]) not in mine]
        ids = {str(row["_id"]) for row in users}
        metrics, profile = await self._metrics(list(ids)), await self._repo.step_one_data(ids)
        result = []
        for user in users:
            user_id = str(user["_id"]); data = profile.get(user_id, {}); metric = metrics.get(user_id, {})
            result.append({
                "user_id": user_id, "user_name": user["name"],
                "user_email": await self._email(actor, partner, str(user["email"])),
                "completion_pct": metric.get("completion_pct", 0),
                "estimated_completion": metric.get("estimated_completion"),
                "field_of_study": data.get("fachrichtung_gewuenscht") or data.get("fachrichtung_praktiziert") or data.get("field_of_study", ""),
                "bundesland": data.get("anerkennungsverfahren_bundesland", ""),
                "created_at": user.get("created_at", ""),
            })
        return result

    @staticmethod
    def _partner_id(actor: Mapping[str, Any]) -> str:
        partner_id = actor.get("partner_id")
        if not partner_id: raise PartnerNotLinked
        return str(partner_id)

    @staticmethod
    def _decorate(row: dict[str, Any], metrics: Mapping[str, Any], work: Mapping[str, Any],
                  profile: Mapping[str, Any]) -> None:
        row.update({
            "estimated_completion": metrics.get("estimated_completion"),
            "completion_pct": metrics.get("completion_pct", 0),
            "partner_work_completed": work.get("completed", False),
            "partner_work_completed_at": work.get("completed_at"),
            "partner_milestone_step_id": work.get("milestone_step_id"),
            "service_step_id": work.get("service_step_id") or row.get("step_id"),
            "service_step_title": work.get("service_step_title", ""),
            "partner_milestone_step_title": work.get("milestone_step_title", ""),
            "field_of_study": profile.get("fachrichtung_gewuenscht") or profile.get("fachrichtung_praktiziert") or profile.get("field_of_study", ""),
            "bundesland": profile.get("anerkennungsverfahren_bundesland", ""),
        })
