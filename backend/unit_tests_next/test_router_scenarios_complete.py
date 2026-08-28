"""Focused success and failure scenarios for stateful HTTP adapters."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException

from slices.email_notifications.router import build_email_notifications_router
from slices.email_notifications.models import MessageTemplate
from slices.email_notifications.web import EmailPreviewPayload, EmailTestSendPayload, NotificationPreviewPayload
from slices.partner_selection import router as selection_router
from slices.partner_selection.domain import EmptyPartnerSelection
from slices.partner_selection.web import MultiPartnerSubmission, PartnerSubmissionCreate
from slices.partner_workspace.router import (
    build_partner_workspace_action_router, build_partner_workspace_command_router,
    build_partner_workspace_detail_router, build_partner_workspace_read_router,
    build_partner_workspace_router,
)
from slices.partner_workspace.profile import PartnerProfileNotLinked
from slices.partner_workspace.logo import InvalidPartnerLogo, PartnerLogoTooLarge
from slices.partner_workspace.read_service import PartnerNotLinked
from slices.partner_workspace.service import WorkspaceUserNotFound
from slices.partner_workspace.action_service import WorkspaceActionStepNotFound, WorkspaceActionStepNotManaged
from slices.partner_workspace.command_service import ManagedMilestoneNotFound, WorkspaceCommandStepNotFound, WorkspaceStepNotManaged
from slices.partner_workspace.domain import InvalidWorkspaceAction, RejectionReasonRequired
from slices.partner_workspace.web import PartnerSelfUpdate, PartnerStepAction
from slices.identity_access.web import ProfileUpdate
from slices.survey_runtime.web import UserProgressUpdate
from slices.survey_runtime.router import build_survey_progress_router
from slices.survey_runtime.progress_service import ProgressStepNotFound
from slices.survey_runtime.progress import MissingRequiredFields, MissingRequiredUploads, MissingMultiUpload
from slices.stripe_subscription.router import (
    build_partner_payment_router, build_stripe_connection_administration_router,
    build_stripe_webhook_router,
)
from slices.stripe_subscription.web import PartnerBillingSettingsUpdate
from slices.stripe_subscription.administration import StripeConnectionInvalidPartnerId, StripeConnectionPartnerNotFound
from slices.stripe_subscription.partner_portal import PartnerPortalNotLinked, PartnerPortalPartnerNotFound
from slices.stripe_subscription.domain import MissingStripeCustomer
from infrastructure.stripe_webhook import StripeWebhookConfigurationError, StripeWebhookSignatureError


ACTOR = {"_id": str(ObjectId()), "email": "admin@test", "name": "Admin", "role": "admin",
         "partner_id": str(ObjectId())}


def guard(*_roles):
    async def dependency(_request): return ACTOR
    return dependency


def endpoint(router, name):
    return next(route.endpoint for route in router.routes if route.name == name)


@pytest.mark.anyio
async def test_partner_selection_create_update_multi_notifications_and_errors(monkeypatch) -> None:
    partner1 = SimpleNamespace(id="p1", document={"id": "p1", "name": "P1"})
    partner2 = SimpleNamespace(id="p2", document={"id": "p2", "name": "P2"})
    step = SimpleNamespace(document={"_id": "step", "title": "S"})
    plan = SimpleNamespace(step=step, partners=(partner1,), partner_ids=("p1",), selection_data={"selected_partner_old": "x"})
    service = SimpleNamespace(
        list_partners=AsyncMock(return_value=[{"id": "p1", "name": "P1", "description": "", "logo_url": "", "tags": []}]),
        prepare=AsyncMock(return_value=plan),
    )
    monkeypatch.setattr(selection_router, "PartnerSelectionService", lambda _repo: service)
    repository = SimpleNamespace(
        partner_document=AsyncMock(return_value={"id": "p1", "name": "P1", "description": "", "logo_url": "", "tags": []}),
        submission=AsyncMock(side_effect=[None, {"_id": ObjectId(), "id": "existing"}, None, None]),
        update_submission=AsyncMock(), insert_submission=AsyncMock(), remove_other_submissions=AsyncMock(),
    )
    notify_partner = AsyncMock(); notify_waiting = AsyncMock(); write = AsyncMock()
    router = selection_router.build_partner_selection_router(
        repository, AsyncMock(return_value={"_id": "u", "email": "u@test", "name": "U"}),
        AsyncMock(), write, notify_partner, notify_waiting, lambda: "now", lambda: "new",
        MagicMock(),
    )
    assert await endpoint(router, "partners")() and await endpoint(router, "partner")("p1")
    request = MagicMock()
    payload = PartnerSubmissionCreate.model_construct(partner_id="p1", data={"_step_id": "step"})
    assert (await endpoint(router, "submit")(payload, request))["submission_id"] == "new"
    assert (await endpoint(router, "submit")(payload, request))["submission_id"] == "existing"
    plan.partners = (partner1, partner2); plan.partner_ids = ("p1", "p2")
    multi = MultiPartnerSubmission.model_construct(partner_ids=["p1", "p2"], data={"_step_id": "step"})
    assert len((await endpoint(router, "submit_multi")(multi, request))["submission_ids"]) == 2
    repository.partner_document.return_value = None
    with pytest.raises(HTTPException): await endpoint(router, "partner")("missing")
    service.prepare.side_effect = EmptyPartnerSelection()
    with pytest.raises(HTTPException): await endpoint(router, "submit")(payload, request)
    service.prepare.side_effect = None
    service.prepare.return_value = SimpleNamespace(
        step=None, partners=(partner1,), partner_ids=("p1",), selection_data={},
    )
    repository.submission.side_effect = [None, None, {"_id": ObjectId(), "id": "old"}]
    notify_partner.side_effect = RuntimeError("mail")
    notify_waiting.side_effect = RuntimeError("mail")
    assert (await endpoint(router, "submit")(
        PartnerSubmissionCreate.model_construct(partner_id="p1", data={}), request,
    ))["submission_id"] == "new"
    assert await endpoint(router, "submit_multi")(
        MultiPartnerSubmission.model_construct(partner_ids=["p1"], data={}), request,
    )
    service.prepare.return_value = SimpleNamespace(
        step=step, partners=(partner1,), partner_ids=("p1",), selection_data={},
    )
    assert await endpoint(router, "submit_multi")(
        MultiPartnerSubmission.model_construct(partner_ids=["p1"], data={"_step_id": "step"}), request,
    )


@pytest.mark.anyio
async def test_email_router_all_render_and_delivery_outcomes() -> None:
    row = MessageTemplate("k", "general", "S", "H")
    service = SimpleNamespace(
        templates=AsyncMock(return_value=[row]), template=AsyncMock(return_value=row),
        update=AsyncMock(return_value=row), reset=AsyncMock(return_value=row),
    )
    renderer = AsyncMock(return_value={"subject": "S", "html": "H"})
    notification = AsyncMock(return_value={"title": "T", "body": "B"})
    deliveries = AsyncMock(side_effect=[{"status": "success"}, {"status": "skipped"},
                                        {"status": "failed", "error": "bad"}, RuntimeError("down")])
    audit = AsyncMock()
    router = build_email_notifications_router(service, guard, audit, renderer, notification,
                                               deliveries, lambda: "now")
    request = MagicMock()
    assert (await endpoint(router, "templates")(request))["templates"]
    assert await endpoint(router, "template")("k", request)
    assert await endpoint(router, "update")("k", {"subject": "New"}, request)
    assert await endpoint(router, "reset")("k", request)
    preview = EmailPreviewPayload.model_construct(variables={}, subject=None, body_html=None)
    note = NotificationPreviewPayload.model_construct(variables={}, title=None, body=None)
    assert await endpoint(router, "preview")("k", preview, request)
    assert await endpoint(router, "notification_preview")("k", note, request)
    send = EmailTestSendPayload.model_construct(
        variables={}, subject=None, body_html=None,
        recipients=["admin@test", "good@test", "skip@test", "bad@test", "down@test", "", "invalid"],
    )
    result = await endpoint(router, "send_test")("k", send, request)
    assert result["sent"] == 1 and result["skipped"] == 1 and len(result["failed"]) == 3
    renderer.return_value = None
    with pytest.raises(HTTPException): await endpoint(router, "preview")("k", preview, request)
    with pytest.raises(HTTPException): await endpoint(router, "send_test")("k", send, request)
    notification.return_value = None
    with pytest.raises(HTTPException): await endpoint(router, "notification_preview")("k", note, request)
    ACTOR["email"] = ""
    renderer.return_value = {"subject": "S", "html": "H"}
    empty = EmailTestSendPayload.model_construct(variables={}, subject=None, body_html=None, recipients=[])
    with pytest.raises(HTTPException): await endpoint(router, "send_test")("k", empty, request)
    ACTOR["email"] = "admin@test"
    service.reset.side_effect = KeyError("missing")
    with pytest.raises(HTTPException): await endpoint(router, "reset")("missing", request)


@pytest.mark.anyio
async def test_partner_workspace_happy_paths_and_http_error_mapping() -> None:
    profile = SimpleNamespace(
        profile=AsyncMock(return_value={}),
        update_organization=AsyncMock(return_value=("p", ["name"])),
        update_logo=AsyncMock(return_value=("p", "data:image/png;base64,x")),
    )
    identity = SimpleNamespace(update_profile=AsyncMock())
    insights = SimpleNamespace(insights=AsyncMock(return_value={}))
    audit = AsyncMock()
    router = build_partner_workspace_router(profile, identity, insights, guard, audit, lambda: "now")
    request = MagicMock()
    assert await endpoint(router, "get_profile")(request) == {}
    assert await endpoint(router, "update_profile")(ProfileUpdate.model_construct(name="N", profile={}), request)
    self_update = PartnerSelfUpdate.model_construct(name="P")
    assert await endpoint(router, "update_partner_data")(self_update, request)
    upload = MagicMock(filename="x.png", content_type="image/png"); upload.read = AsyncMock(return_value=b"png")
    assert (await endpoint(router, "upload_logo")(request, upload))["logo_url"]
    assert await endpoint(router, "partner_insights")(request) == {}
    for error in (PartnerProfileNotLinked(),):
        profile.update_organization.side_effect = error
        with pytest.raises(HTTPException): await endpoint(router, "update_partner_data")(self_update, request)
    for error in (PartnerProfileNotLinked(), PartnerLogoTooLarge(), InvalidPartnerLogo("bad")):
        profile.update_logo.side_effect = error
        with pytest.raises(HTTPException): await endpoint(router, "upload_logo")(request, upload)
    profile.update_logo.side_effect = None
    original = ACTOR.pop("partner_id")
    with pytest.raises(HTTPException): await endpoint(router, "partner_insights")(request)
    ACTOR["partner_id"] = original

    action_service = SimpleNamespace(execute=AsyncMock(return_value={"ok": True}))
    action_router = build_partner_workspace_action_router(action_service, guard)
    action = PartnerStepAction.model_construct(action="complete", reason=None, data={})
    assert await endpoint(action_router, "action")("u", "s", action, request)
    for error in (PartnerNotLinked(), InvalidWorkspaceAction(), RejectionReasonRequired(),
                  WorkspaceActionStepNotManaged(), WorkspaceActionStepNotFound(), WorkspaceUserNotFound()):
        action_service.execute.side_effect = error
        with pytest.raises(HTTPException): await endpoint(action_router, "action")("u", "s", action, request)

    command = SimpleNamespace(reopen=AsyncMock(return_value="s"), update_progress=AsyncMock())
    command_router = build_partner_workspace_command_router(command, guard)
    assert await endpoint(command_router, "reopen")("u", request)
    update = UserProgressUpdate.model_construct(step_id="s", status="pending", data={})
    assert await endpoint(command_router, "update_progress")("u", update, request)
    for error in (PartnerNotLinked(), ManagedMilestoneNotFound()):
        command.reopen.side_effect = error
        with pytest.raises(HTTPException): await endpoint(command_router, "reopen")("u", request)
    for error in (PartnerNotLinked(), WorkspaceCommandStepNotFound(), WorkspaceStepNotManaged(), WorkspaceUserNotFound()):
        command.update_progress.side_effect = error
        with pytest.raises(HTTPException): await endpoint(command_router, "update_progress")("u", update, request)

    for builder, method, errors in (
        (build_partner_workspace_detail_router, "detail", (PartnerNotLinked(), WorkspaceUserNotFound())),
        (build_partner_workspace_read_router, "submissions", (PartnerNotLinked(),)),
        (build_partner_workspace_read_router, "other_users", (PartnerNotLinked(),)),
    ):
        service = SimpleNamespace(detail=AsyncMock(return_value={}), submissions=AsyncMock(return_value=[]), other_users=AsyncMock(return_value=[]))
        built = builder(service, guard)
        result = await endpoint(built, method)("u", request) if method == "detail" else await endpoint(built, method)(request)
        assert result == ({} if method == "detail" else [])
        for error in errors:
            getattr(service, method).side_effect = error
            with pytest.raises(HTTPException):
                await endpoint(built, method)("u", request) if method == "detail" else await endpoint(built, method)(request)


@pytest.mark.anyio
async def test_stripe_admin_partner_and_webhook_routes_cover_all_outcomes() -> None:
    request = MagicMock(); request.body = AsyncMock(return_value=b"body"); request.headers = {"stripe-signature": "sig"}
    report = SimpleNamespace(proposed_customer_id="cus", proposed_subscription_id="sub")
    admin_service = SimpleNamespace(
        audit=AsyncMock(return_value={}), repair_all=AsyncMock(return_value=(["p"], ["q"])),
        repair=AsyncMock(return_value=report),
    )
    audit = AsyncMock()
    admin = build_stripe_connection_administration_router(admin_service, guard, audit)
    assert await endpoint(admin, "connection_audit")(request) == {}
    assert (await endpoint(admin, "repair_all")(request))["repaired"] == 1
    assert await endpoint(admin, "repair")("p", request)
    for error in (StripeConnectionInvalidPartnerId(), StripeConnectionPartnerNotFound()):
        admin_service.repair.side_effect = error
        with pytest.raises(HTTPException): await endpoint(admin, "repair")("p", request)
    admin_service.repair.side_effect = None; admin_service.repair.return_value = None
    with pytest.raises(HTTPException): await endpoint(admin, "repair")("p", request)

    partner = {"_id": ObjectId()}
    service = SimpleNamespace(
        own_partner=AsyncMock(return_value=partner), settings=AsyncMock(return_value={}),
        status=AsyncMock(return_value={}), checkout=AsyncMock(return_value="checkout"),
        portal=AsyncMock(return_value="portal"), update_settings=AsyncMock(return_value=["x"]),
        stripe_status=AsyncMock(return_value={}), invoices=AsyncMock(return_value=[]),
    )
    payment = build_partner_payment_router(service, guard, audit, lambda: "now")
    assert await endpoint(payment, "settings")(request) == {}
    assert await endpoint(payment, "status")(request, "session") == {}
    assert (await endpoint(payment, "checkout")(request))["url"] == "checkout"
    assert (await endpoint(payment, "portal")(request))["url"] == "portal"
    settings = PartnerBillingSettingsUpdate.model_construct(billing_email="billing@test")
    assert await endpoint(payment, "update_settings")(settings, request)
    assert await endpoint(payment, "stripe_status")(request) == {}
    assert await endpoint(payment, "invoices")(request) == []
    for error in (PartnerPortalNotLinked(), PartnerPortalPartnerNotFound()):
        service.own_partner.side_effect = error
        with pytest.raises(HTTPException): await endpoint(payment, "settings")(request)
    service.own_partner.side_effect = None
    for method in ("status", "checkout", "portal"):
        getattr(service, method).side_effect = MissingStripeCustomer()
        with pytest.raises(HTTPException):
            await endpoint(payment, method)(request, None) if method == "status" else await endpoint(payment, method)(request)
        getattr(service, method).side_effect = None

    webhook_service = SimpleNamespace(handle=AsyncMock())
    webhook = build_stripe_webhook_router(webhook_service)
    assert await endpoint(webhook, "webhook")(request) == {"received": True}
    for error in (StripeWebhookConfigurationError(), StripeWebhookSignatureError()):
        webhook_service.handle.side_effect = error
        with pytest.raises(HTTPException): await endpoint(webhook, "webhook")(request)


@pytest.mark.anyio
async def test_survey_progress_maps_every_validation_error() -> None:
    service = SimpleNamespace(update=AsyncMock())
    router = build_survey_progress_router(service, AsyncMock(return_value=ACTOR))
    update = UserProgressUpdate.model_construct(step_id="s", status="completed", data={})
    request = MagicMock()
    assert await endpoint(router, "update_progress")(update, request)
    errors = (
        ProgressStepNotFound(), MissingRequiredFields(["Name"]),
        MissingRequiredUploads(["Diplom"]), MissingMultiUpload("Dokumente"),
    )
    for error in errors:
        service.update.side_effect = error
        with pytest.raises(HTTPException): await endpoint(router, "update_progress")(update, request)
