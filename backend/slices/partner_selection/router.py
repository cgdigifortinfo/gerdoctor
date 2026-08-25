"""FastAPI adapter for public partner discovery and selection submissions."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from slices.partner_selection.mappers import selection_user_from_document
from slices.partner_selection.models import PartnerSelectionPlan
from slices.partner_selection.repository import MongoPartnerSelectionRepository
from slices.partner_selection.service import PartnerSelectionService
from slices.partner_selection.web import MultiPartnerSubmission, PartnerSubmissionCreate
from slices.partner_selection.web_errors import partner_selection_http_exception
from slices.partner_selection.web_serializers import public_partner_detail, public_partner_summary
from slices.partner_selection.domain import PartnerSelectionError


User = Mapping[str, Any]
CurrentUser = Callable[[Request], Awaitable[User]]
Editable = Callable[[str, dict[str, Any]], Awaitable[None]]
WriteProgress = Callable[[User, dict[str, Any], dict[str, Any]], Awaitable[None]]
Notify = Callable[[Mapping[str, Any], User, Mapping[str, Any]], Awaitable[None]]
NotifyWaiting = Callable[[User, Mapping[str, Any]], Awaitable[None]]


def build_partner_selection_router(
    repository: MongoPartnerSelectionRepository, get_current_user: CurrentUser,
    assert_editable: Editable, write_progress: WriteProgress,
    notify_partner: Notify, notify_waiting: NotifyWaiting,
    now_iso: Callable[[], str], new_id: Callable[[], str], logger: Any,
) -> APIRouter:
    router = APIRouter(tags=["partners"])
    service = PartnerSelectionService(repository)

    async def prepare(user: User, step_id: str | None, partner_ids: list[str],
                      data: dict[str, Any], multiple: bool) -> PartnerSelectionPlan:
        try:
            plan = await service.prepare(
                user=selection_user_from_document(user), step_id=step_id,
                partner_ids=partner_ids, data=data, multiple=multiple,
            )
        except PartnerSelectionError as error:
            raise partner_selection_http_exception(error)
        if plan.step:
            await assert_editable(str(user["_id"]), dict(plan.step.document))
        return plan

    @router.get("/partners")
    async def partners(tag: str = "") -> list[dict[str, Any]]:
        return [public_partner_summary(row) for row in await service.list_partners(tag)]

    @router.get("/partners/{partner_id}")
    async def partner(partner_id: str) -> dict[str, Any]:
        document = await repository.partner_document(partner_id)
        if not document:
            raise HTTPException(404, "Partner not found")
        return public_partner_detail(document)

    async def save(user: User, partner_id: str, step_id: str | None,
                   selection_data: dict[str, Any]) -> tuple[str, bool]:
        existing = await repository.submission(str(user["_id"]), partner_id, step_id)
        if existing:
            await repository.update_submission(existing["_id"], {
                "step_id": step_id, "data": selection_data, "status": "submitted",
                "updated_at": now_iso(),
            })
            return str(existing["id"]), False
        submission_id = new_id()
        await repository.insert_submission({
            "id": submission_id, "user_id": str(user["_id"]),
            "user_email": user["email"], "user_name": user["name"],
            "partner_id": partner_id, "step_id": step_id, "data": selection_data,
            "status": "submitted", "created_at": now_iso(),
        })
        return submission_id, True

    @router.post("/partners/submit")
    async def submit(data: PartnerSubmissionCreate, request: Request) -> dict[str, Any]:
        user = await get_current_user(request)
        raw_step_id = data.data.get("_step_id")
        step_id = str(raw_step_id) if raw_step_id else None
        plan = await prepare(user, step_id, [data.partner_id], data.data, False)
        step = dict(plan.step.document) if plan.step else None
        partner_document = dict(plan.partners[0].document)
        selection_data = dict(plan.selection_data)
        if step:
            assert step_id is not None
            selection_data.update({"selected_partner_id": data.partner_id,
                                   "selected_partner_name": partner_document.get("name", "")})
            await repository.remove_other_submissions(str(user["_id"]), step_id,
                                                      (data.partner_id,))
        submission_id, created = await save(user, data.partner_id, step_id, selection_data)
        if step:
            assert step_id is not None
            await write_progress(user, step, selection_data)
        if created:
            try:
                await notify_partner(partner_document, user, data.data)
            except Exception as error:
                logger.warning("notify_partner failed for %s: %s", data.partner_id, error)
            try:
                await notify_waiting(user, partner_document)
            except Exception as error:
                logger.warning("notify_user_awaiting_partner failed for %s: %s", user.get("email"), error)
        return {"message": "Submission successful" if created else "Submission updated",
                "submission_id": submission_id}

    @router.post("/partners/submit-multi")
    async def submit_multi(data: MultiPartnerSubmission, request: Request) -> dict[str, Any]:
        user = await get_current_user(request)
        raw_step_id = data.data.get("_step_id")
        step_id = str(raw_step_id) if raw_step_id else None
        plan = await prepare(user, step_id, data.partner_ids, data.data, True)
        step = dict(plan.step.document) if plan.step else None
        if step:
            assert step_id is not None
            await repository.remove_other_submissions(str(user["_id"]), step_id, plan.partner_ids)
        result: list[str] = []
        for selected in plan.partners:
            partner_document = dict(selected.document)
            selection_data = {key: value for key, value in plan.selection_data.items()
                              if not key.startswith("selected_partner_")}
            submission_id, created = await save(user, selected.id, step_id, selection_data)
            result.append(submission_id)
            if created:
                try:
                    await notify_partner(partner_document, user, data.data)
                except Exception as error:
                    logger.warning("notify_partner (multi) failed for %s: %s", selected.id, error)
                try:
                    await notify_waiting(user, partner_document)
                except Exception as error:
                    logger.warning("notify_user_awaiting_partner (multi) failed for %s: %s", selected.id, error)
        if step:
            await write_progress(user, step, dict(plan.selection_data))
        return {"message": f"Submitted to {len(result)} partners", "submission_ids": result}

    return router
