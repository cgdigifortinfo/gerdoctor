"""Application service for editable templates and notifications."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from slices.email_notifications.domain import (
    editable_fields, normalized_recipients, render_email, render_notification,
    template_sort_key,
)
from slices.email_notifications.models import (
    DeliveryResult, MessageTemplate, RenderedEmail, RenderedNotification,
)
from slices.email_notifications.ports import EmailGateway, MessageTemplateRepository


class TemplateNotFound(LookupError): pass


class EmailNotificationsService:
    def __init__(self, repository: MessageTemplateRepository, gateway: EmailGateway,
                 app_url: str) -> None:
        self._repository = repository
        self._gateway = gateway
        self._app_url = app_url

    def _variables(self, values: Mapping[str, Any]) -> dict[str, Any]:
        variables = dict(values)
        variables.setdefault("app_url", self._app_url)
        return variables

    async def templates(self) -> list[MessageTemplate]:
        return sorted(await self._repository.list(), key=template_sort_key)

    async def template(self, key: str) -> MessageTemplate:
        template = await self._repository.get(key)
        if template is None:
            raise TemplateNotFound(key)
        return template

    async def update(self, key: str, payload: Mapping[str, Any], timestamp: str) -> MessageTemplate:
        await self.template(key)
        fields = editable_fields(payload)
        updated = await self._repository.update(key, {**fields, "updated_at": timestamp})
        if updated is None:
            raise TemplateNotFound(key)
        return updated

    async def reset(self, key: str, defaults: Mapping[str, MessageTemplate], timestamp: str) -> MessageTemplate:
        template = defaults.get(key)
        if template is None:
            raise TemplateNotFound(key)
        return await self._repository.upsert(template, timestamp)

    async def seed(self, defaults: Sequence[MessageTemplate], timestamp: str) -> None:
        await self._repository.seed(defaults, timestamp)

    async def email(self, key: str, variables: Mapping[str, Any], override_subject: str = "",
                    override_body: str = "") -> RenderedEmail:
        template = await self._repository.get(key)
        if template is None:
            if not override_body:
                raise TemplateNotFound(key)
            template = MessageTemplate(key, "user", "", "")
        header = await self._repository.get("header")
        footer = await self._repository.get("footer")
        return render_email(template, header.body_html if header else "", footer.body_html if footer else "",
                            self._variables(variables), override_subject, override_body)

    async def notification(self, key: str, variables: Mapping[str, Any],
                           override_title: str | None = None,
                           override_body: str | None = None) -> RenderedNotification:
        template = await self.template(key)
        return render_notification(template, self._variables(variables), override_title, override_body)

    async def send_rendered(self, recipient: str, key: str, variables: Mapping[str, Any],
                            override_subject: str = "", override_body: str = "") -> DeliveryResult:
        try:
            rendered = await self.email(key, variables, override_subject, override_body)
        except TemplateNotFound:
            return DeliveryResult("skipped", error=f"template '{key}' missing")
        return await self._gateway.send(recipient, rendered.subject, rendered.html)

    async def send(self, recipient: str, subject: str, html: str) -> DeliveryResult:
        return await self._gateway.send(recipient, subject, html)

    async def send_test(self, primary: str | None, additional: Sequence[str | None],
                        rendered: RenderedEmail) -> tuple[tuple[str, ...], tuple[DeliveryResult, ...]]:
        recipients = normalized_recipients(primary, additional)
        results = tuple([await self._gateway.send(item, rendered.subject, rendered.html)
                         for item in recipients])
        return recipients, results
