"""HTTP models and error mapping for message administration."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from slices.email_notifications.domain import NoEditableFields, NoValidRecipients
from slices.email_notifications.service import TemplateNotFound


class EmailPreviewPayload(BaseModel):
    subject: str | None = ""
    body_html: str | None = ""
    variables: dict[str, Any] | None = None


class NotificationPreviewPayload(BaseModel):
    title: str | None = None
    body: str | None = None
    variables: dict[str, Any] | None = None


class EmailTestSendPayload(EmailPreviewPayload):
    recipients: list[str] = Field(default_factory=list)


def email_notifications_http_error(error: Exception) -> HTTPException:
    if isinstance(error, TemplateNotFound):
        return HTTPException(status_code=404, detail="Template not found")
    if isinstance(error, NoEditableFields):
        return HTTPException(status_code=400, detail="No editable fields provided")
    if isinstance(error, NoValidRecipients):
        return HTTPException(status_code=400, detail="No valid recipients")
    return HTTPException(status_code=400, detail="Invalid notification operation")
