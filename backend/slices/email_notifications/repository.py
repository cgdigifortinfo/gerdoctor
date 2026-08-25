"""MongoDB template persistence adapter."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from slices.email_notifications.models import MessageTemplate


def template_from_document(document: Mapping[str, Any]) -> MessageTemplate:
    return MessageTemplate(
        key=str(document.get("key", "")), category=str(document.get("category", "user")),
        subject=str(document.get("subject", "")), body_html=str(document.get("body_html", "")),
        notification_title=str(document.get("notification_title", "")),
        notification_body=str(document.get("notification_body", "")),
        description=str(document.get("description", "")),
    )


def template_document(template: MessageTemplate) -> dict[str, str]:
    return {
        "key": template.key, "category": template.category, "subject": template.subject,
        "body_html": template.body_html, "notification_title": template.notification_title,
        "notification_body": template.notification_body, "description": template.description,
    }


class MongoMessageTemplateRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def get(self, key: str) -> MessageTemplate | None:
        document = await self._db.email_templates.find_one({"key": key})
        return template_from_document(document) if document else None

    async def list(self) -> list[MessageTemplate]:
        documents = await self._db.email_templates.find({}, {"_id": 0}).to_list(200)
        return [template_from_document(document) for document in documents]

    async def update(self, key: str, fields: Mapping[str, Any]) -> MessageTemplate | None:
        await self._db.email_templates.update_one({"key": key}, {"$set": dict(fields)})
        return await self.get(key)

    async def upsert(self, template: MessageTemplate, timestamp: str) -> MessageTemplate:
        document = {**template_document(template), "updated_at": timestamp}
        await self._db.email_templates.update_one({"key": template.key}, {"$set": document}, upsert=True)
        return template

    async def seed(self, templates: Sequence[MessageTemplate], timestamp: str) -> None:
        for template in templates:
            existing = await self._db.email_templates.find_one({"key": template.key})
            document = {**template_document(template), "updated_at": timestamp}
            if existing:
                additions = {key: value for key, value in document.items()
                             if key != "key" and (key not in existing or existing.get(key) in (None, ""))}
                if additions:
                    await self._db.email_templates.update_one({"key": template.key}, {"$set": additions})
            else:
                await self._db.email_templates.insert_one({**document, "created_at": timestamp})
