"""Immutable values for message templates and delivery."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MessageTemplate:
    key: str
    category: str
    subject: str
    body_html: str
    notification_title: str = ""
    notification_body: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class RenderedEmail:
    subject: str
    html: str

    def to_document(self) -> dict[str, str]:
        return {"subject": self.subject, "html": self.html}


@dataclass(frozen=True, slots=True)
class RenderedNotification:
    title: str
    body: str

    def to_document(self) -> dict[str, str]:
        return {"title": self.title, "body": self.body}


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    status: str
    message: str = ""
    error: str = ""

    def to_document(self) -> dict[str, str]:
        result = {"status": self.status}
        if self.message:
            result["message"] = self.message
        if self.error:
            result["error"] = self.error
        return result


Variables = dict[str, Any]
