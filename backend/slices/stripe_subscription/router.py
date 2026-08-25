"""FastAPI routes for administrative Stripe connection maintenance."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from slices.stripe_subscription.administration import (
    StripeConnectionAdministrationService,
    StripeConnectionInvalidPartnerId,
    StripeConnectionPartnerNotFound,
)
from slices.stripe_subscription.domain import SubscriptionRuleError
from slices.stripe_subscription.partner_portal import (
    PartnerPortalNotLinked,
    PartnerPortalPartnerNotFound,
    PartnerPortalService,
)
from slices.stripe_subscription.web import (
    PartnerBillingSettingsUpdate,
    stripe_subscription_http_error,
)
from infrastructure.stripe_webhook import (
    StripeWebhookConfigurationError,
    StripeWebhookSignatureError,
)
from slices.stripe_subscription.webhook import StripeWebhookService


Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]


def build_stripe_connection_administration_router(
    service: StripeConnectionAdministrationService, require_role: Guard, audit: Audit,
) -> APIRouter:
    router = APIRouter(prefix="/admin/billing", tags=["admin"])

    @router.get("/connection-audit")
    async def connection_audit(request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        return await service.audit()

    @router.post("/connection-repairs/all")
    async def repair_all(request: Request) -> dict[str, Any]:
        actor = await require_role("admin")(request)
        repaired, skipped = await service.repair_all()
        await audit(actor["_id"], actor["email"], "stripe_connections_repair_all",
                    "partner", "", {"repaired": repaired, "skipped": skipped})
        return {
            "repaired": len(repaired), "skipped": len(skipped),
            "repaired_partner_ids": repaired,
        }

    @router.post("/connection-repairs/{partner_id}")
    async def repair(partner_id: str, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request)
        try:
            report = await service.repair(partner_id)
        except StripeConnectionInvalidPartnerId as error:
            raise HTTPException(400, "Invalid partner id") from error
        except StripeConnectionPartnerNotFound as error:
            raise HTTPException(404, "Partner not found") from error
        if report is None:
            raise HTTPException(
                409, "Die Stripe-Verbindung ist nicht eindeutig automatisch reparierbar",
            )
        await audit(actor["_id"], actor["email"], "stripe_connection_repair", "partner",
                    partner_id, {"customer_id": report.proposed_customer_id,
                                 "subscription_id": report.proposed_subscription_id})
        return {"message": "Stripe-Verbindung repariert", "partner_id": partner_id}

    return router


def build_partner_payment_router(
    service: PartnerPortalService, require_role: Guard, audit: Audit,
    now_iso: Callable[[], str],
) -> APIRouter:
    router = APIRouter(prefix="/partner-payment", tags=["partner-payment"])

    async def context(request: Request) -> tuple[Actor, dict[str, Any]]:
        user = await require_role("partner")(request)
        try:
            return user, await service.own_partner(user)
        except PartnerPortalNotLinked as error:
            raise HTTPException(400, "User not linked to a partner") from error
        except PartnerPortalPartnerNotFound as error:
            raise HTTPException(404, "Partner not found") from error

    @router.get("/settings")
    async def settings(request: Request) -> dict[str, Any]:
        _, partner = await context(request)
        return await service.settings(partner)

    @router.get("/status")
    async def status(request: Request, session_id: str | None = None) -> dict[str, Any]:
        _, partner = await context(request)
        try:
            return await service.status(partner, session_id, now_iso())
        except SubscriptionRuleError as error:
            raise stripe_subscription_http_error(error)

    @router.post("/checkout")
    async def checkout(request: Request) -> dict[str, str]:
        user, partner = await context(request)
        try:
            return {"url": await service.checkout(user, partner)}
        except SubscriptionRuleError as error:
            raise stripe_subscription_http_error(error)

    @router.post("/portal")
    async def portal(request: Request) -> dict[str, str]:
        _, partner = await context(request)
        try:
            return {"url": await service.portal(partner)}
        except SubscriptionRuleError as error:
            raise stripe_subscription_http_error(error)

    @router.put("/settings")
    async def update_settings(
        data: PartnerBillingSettingsUpdate, request: Request,
    ) -> dict[str, str]:
        user, partner = await context(request)
        fields = await service.update_settings(str(partner["_id"]), data.model_dump())
        await audit(user["_id"], user["email"], "partner_billing_update", "partner",
                    str(partner["_id"]), {"fields": fields})
        return {"message": "Billing settings updated"}

    @router.get("/stripe-status")
    async def stripe_status(request: Request) -> dict[str, Any]:
        _, partner = await context(request)
        return await service.stripe_status(partner)

    @router.get("/invoices")
    async def invoices(request: Request) -> list[dict[str, Any]]:
        _, partner = await context(request)
        return await service.invoices(partner)

    return router


def build_stripe_webhook_router(service: StripeWebhookService) -> APIRouter:
    router = APIRouter(prefix="/partner-payment", tags=["partner-payment"])

    @router.post("/webhook")
    async def webhook(request: Request) -> dict[str, bool]:
        try:
            await service.handle(
                await request.body(), request.headers.get("stripe-signature", ""),
            )
        except StripeWebhookConfigurationError as error:
            raise HTTPException(503, "Stripe webhook secret is not configured") from error
        except StripeWebhookSignatureError as error:
            raise HTTPException(400, "Invalid Stripe signature") from error
        return {"received": True}

    return router
