"""Pure message rendering and recipient rules."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from slices.email_notifications.models import MessageTemplate, RenderedEmail, RenderedNotification

TEMPLATE_VARIABLES: dict[str, tuple[str, ...]] = {
    "layout": ("app_url",),
    "partner": ("partner_name", "user_name", "user_email", "field_of_study",
                "bundesland", "step_order", "open_user_link", "app_url"),
    "user": ("user_name", "partner_name", "milestone_title", "step_title",
             "rejection_reason", "reopened_step_title", "reset_link", "app_url"),
    "step": ("user_name", "step_title", "step_order", "step_description",
             "total_steps", "partner_name", "app_url"),
}
EDITABLE_TEMPLATE_FIELDS = frozenset({
    "subject", "body_html", "notification_title", "notification_body", "description",
})
CATEGORY_ORDER = {"layout": 0, "partner": 1, "user": 2, "step": 3}


class MessageRuleError(ValueError): pass
class NoEditableFields(MessageRuleError): pass
class NoValidRecipients(MessageRuleError): pass


def replace_variables(text: str, variables: Mapping[str, Any]) -> str:
    def substitute(match: re.Match[str]) -> str:
        value = variables.get(match.group(1).strip())
        return "" if value is None else str(value)
    return re.sub(r"{{\s*([\w.]+)\s*}}", substitute, text) if text else ""


def render_email(template: MessageTemplate, header: str, footer: str,
                 variables: Mapping[str, Any], override_subject: str = "",
                 override_body: str = "") -> RenderedEmail:
    subject = replace_variables(override_subject or template.subject, variables)
    body = replace_variables(override_body or template.body_html, variables)
    rendered_header = replace_variables(header, variables)
    rendered_footer = replace_variables(footer, variables)
    html = ("<!DOCTYPE html>\n<html>\n<head><meta charset=\"utf-8\"/></head>\n"
            "<body style=\"margin:0;padding:0;background:#f8fafc;\">\n"
            "  <div style=\"max-width:640px;margin:0 auto;background:#ffffff;\">\n"
            f"    {rendered_header}\n    {body}\n    {rendered_footer}\n"
            "  </div>\n</body>\n</html>")
    return RenderedEmail(subject, html)


def render_notification(template: MessageTemplate, variables: Mapping[str, Any],
                        override_title: str | None = None,
                        override_body: str | None = None) -> RenderedNotification:
    title = template.notification_title if override_title is None else override_title
    body = template.notification_body if override_body is None else override_body
    return RenderedNotification(replace_variables(title, variables), replace_variables(body, variables))


def editable_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {key: value for key, value in payload.items() if key in EDITABLE_TEMPLATE_FIELDS}
    if not fields:
        raise NoEditableFields
    return fields


def normalized_recipients(primary: str | None, additional: Iterable[str | None]) -> tuple[str, ...]:
    candidates = ((primary,) if primary else ()) + tuple(additional)
    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        email = candidate.strip()
        normalized = email.casefold()
        if email and "@" in email and normalized not in seen:
            seen.add(normalized)
            result.append(email)
    if not result:
        raise NoValidRecipients
    return tuple(result)


def template_sort_key(template: MessageTemplate) -> tuple[int, str]:
    return CATEGORY_ORDER.get(template.category, 99), template.key


def partner_deep_link(frontend_url: str, user_id: str) -> str:
    base = frontend_url.removesuffix("/")
    path = f"/partner-dashboard?openUser={user_id}"
    return f"{base}{path}" if base else path
