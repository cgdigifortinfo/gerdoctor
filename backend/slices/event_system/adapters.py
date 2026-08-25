"""Notification adapter connecting events to the message slice."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from slices.email_notifications.models import DeliveryResult, RenderedNotification
from slices.email_notifications.service import EmailNotificationsService, TemplateNotFound


class MessageEventNotifier:
    def __init__(self, messages: EmailNotificationsService) -> None: self._messages = messages

    async def email(self, recipient: str, template_key: str,
                    variables: Mapping[str, Any]) -> DeliveryResult:
        return await self._messages.send_rendered(recipient, template_key, variables)

    async def notification(self, template_key: str,
                           variables: Mapping[str, Any]) -> RenderedNotification | None:
        try:
            return await self._messages.notification(template_key, variables)
        except TemplateNotFound:
            return None
