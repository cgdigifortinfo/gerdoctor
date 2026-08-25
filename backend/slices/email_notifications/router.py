"""Administrative FastAPI routes for message templates and test delivery."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from fastapi import APIRouter, HTTPException, Request
from slices.email_notifications.defaults import default_message_templates
from slices.email_notifications.domain import TEMPLATE_VARIABLES, editable_fields
from slices.email_notifications.repository import template_document
from slices.email_notifications.service import EmailNotificationsService
from slices.email_notifications.web import (
    EmailPreviewPayload, EmailTestSendPayload, NotificationPreviewPayload,
    email_notifications_http_error,
)

Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]
Renderer = Callable[..., Awaitable[dict[str, Any] | None]]
Sender = Callable[[str, str, str], Awaitable[Mapping[str, Any] | None]]

def build_email_notifications_router(service: EmailNotificationsService, require_role: Guard,
                                     audit: Audit, render_email: Renderer,
                                     render_notification: Renderer, send_email: Sender,
                                     now: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])
    @router.get("/email-templates")
    async def templates(request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        rows = await service.templates()
        return {"templates": [template_document(item) for item in rows],
                "variables": {key: list(value) for key, value in TEMPLATE_VARIABLES.items()}}
    @router.get("/email-templates/{key}")
    async def template(key: str, request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        try: return template_document(await service.template(key))
        except Exception as error: raise email_notifications_http_error(error)
    @router.put("/email-templates/{key}")
    async def update(key: str, payload: dict[str, Any], request: Request) -> dict[str, Any]:
        actor = await require_role("admin")(request)
        try:
            fields = editable_fields(payload or {})
            updated = await service.update(key, fields, now())
        except Exception as error: raise email_notifications_http_error(error)
        await audit(actor["_id"], actor["email"], "email_template_update", "email_template", key,
                    {"fields": [*fields, "updated_at"]})
        return template_document(updated)
    @router.post("/email-templates/{key}/reset")
    async def reset(key: str, request: Request) -> dict[str, Any]:
        actor = await require_role("admin")(request)
        try: result = await service.reset(key, default_message_templates(), now())
        except Exception as error:
            http_error = email_notifications_http_error(error)
            if http_error.status_code == 404: http_error.detail = "No default for this template key"
            raise http_error
        await audit(actor["_id"], actor["email"], "email_template_reset", "email_template", key, {})
        return template_document(result)
    @router.post("/email-templates/{key}/preview")
    async def preview(key: str, payload: EmailPreviewPayload, request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        rendered = await render_email(key, payload.variables or {}, override_subject=payload.subject or "",
                                      override_body=payload.body_html or "")
        if not rendered: raise HTTPException(404, "Template not found")
        return rendered
    @router.post("/email-templates/{key}/notification-preview")
    async def notification_preview(key: str, payload: NotificationPreviewPayload,
                                   request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        rendered = await render_notification(key, payload.variables or {}, override_title=payload.title,
                                             override_body=payload.body)
        if not rendered: raise HTTPException(404, "Notification content not found")
        return rendered
    @router.post("/email-templates/{key}/send-test")
    async def send_test(key: str, payload: EmailTestSendPayload, request: Request) -> dict[str, Any]:
        actor = await require_role("admin")(request)
        rendered = await render_email(key, payload.variables or {}, override_subject=payload.subject or "",
                                      override_body=payload.body_html or "")
        if not rendered: raise HTTPException(404, "Template not found")
        recipients: list[str] = []; seen: set[str] = set()
        admin_email = str(actor.get("email") or "").strip()
        if admin_email: recipients.append(admin_email); seen.add(admin_email.lower())
        for value in payload.recipients or []:
            email = (value or "").strip()
            if not email or "@" not in email or email.lower() in seen: continue
            seen.add(email.lower()); recipients.append(email)
        if not recipients: raise HTTPException(400, "No valid recipients")
        sent, skipped = 0, 0; failed: list[dict[str, str]] = []
        for recipient in recipients:
            try:
                delivery = await send_email(recipient, str(rendered["subject"]), str(rendered["html"]))
                status = (delivery or {}).get("status")
                if status == "success": sent += 1
                elif status == "skipped": skipped += 1
                else: failed.append({"email": recipient, "error": str((delivery or {}).get("error", "unknown"))})
            except Exception as error: failed.append({"email": recipient, "error": str(error)})
        await audit(actor["_id"], actor["email"], "email_template_test_send", "email_template", key,
                    {"recipients": recipients, "sent": sent, "failed": len(failed), "skipped": skipped})
        return {"sent": sent, "failed": failed, "skipped": skipped, "recipients": recipients,
                "smtp_configured": skipped == 0 or sent > 0 or len(failed) > 0}
    return router
