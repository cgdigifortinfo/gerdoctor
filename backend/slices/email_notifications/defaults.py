"""Typed access to the canonical editable message defaults."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from email_template_defaults import DEFAULT_TEMPLATES
from slices.email_notifications.models import MessageTemplate


def message_template(key: str, values: Mapping[str, Any]) -> MessageTemplate:
    return MessageTemplate(
        key, str(values.get("category", "user")), str(values.get("subject", "")),
        str(values.get("body_html", "")), str(values.get("notification_title", "")),
        str(values.get("notification_body", "")), str(values.get("description", "")),
    )


def default_message_templates() -> dict[str, MessageTemplate]:
    return {key: message_template(key, values) for key, values in DEFAULT_TEMPLATES.items()}
