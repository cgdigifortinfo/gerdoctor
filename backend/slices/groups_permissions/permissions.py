"""Permission catalog, group seeding and effective RBAC evaluation."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from database import db as database_db
from slices.groups_permissions.domain import (
    compatible_group_ids,
    effective_permissions as resolve_effective_permissions,
    normalize_permissions as normalize_permission_values,
    permission_for_admin_request as resolve_admin_permission,
    permission_for_portal_request as resolve_portal_permission,
)
from slices.groups_permissions.models import PermissionInputs


db: Any = database_db

PERMISSION_CATALOG: list[dict[str, Any]] = [
    {"category": "Administration", "permissions": [
        {"key": "admin.access", "label": "Adminbereich öffnen", "description": "Erlaubt den Zugriff auf die Administrationsoberfläche."},
        {"key": "analytics.view", "label": "Dashboard ansehen", "description": "Kennzahlen und Auswertungen anzeigen."},
        {"key": "audit.view", "label": "Audit-Log ansehen", "description": "Protokollierte Änderungen und Aktionen einsehen."},
    ]},
    {"category": "Benutzer", "permissions": [
        {"key": "users.view", "label": "Benutzer ansehen", "description": "Benutzerliste und Details öffnen."},
        {"key": "users.create", "label": "Benutzer anlegen", "description": "Neue Benutzerkonten erstellen."},
        {"key": "users.update", "label": "Benutzer bearbeiten", "description": "Rollen und Fortschritte ändern."},
        {"key": "users.delete", "label": "Benutzer löschen", "description": "Benutzerkonten und abhängige Daten löschen."},
        {"key": "users.impersonate", "label": "Benutzer imitieren", "description": "Sich testweise als anderer Benutzer anmelden."},
        {"key": "users.export", "label": "Benutzer exportieren", "description": "Benutzerdaten als CSV exportieren."},
        {"key": "users.permissions.manage", "label": "Benutzerrechte überschreiben", "description": "Gruppen und individuelle Allow-/Deny-Regeln pflegen."},
    ]},
    {"category": "Nutzergruppen", "permissions": [
        {"key": "groups.view", "label": "Nutzergruppen ansehen", "description": "Gruppen und deren Berechtigungen anzeigen."},
        {"key": "groups.create", "label": "Nutzergruppen anlegen", "description": "Neue frei konfigurierbare Gruppen erstellen."},
        {"key": "groups.update", "label": "Nutzergruppen bearbeiten", "description": "Namen, Beschreibungen und Rechte ändern."},
        {"key": "groups.delete", "label": "Nutzergruppen löschen", "description": "Nicht systemgeschützte Gruppen löschen."},
    ]},
    {"category": "Surveys und Schritte", "permissions": [
        {"key": "surveys.view", "label": "Surveys ansehen", "description": "Survey-Konfigurationen anzeigen."},
        {"key": "surveys.manage", "label": "Surveys verwalten", "description": "Surveys erstellen und bearbeiten."},
        {"key": "steps.view", "label": "Schritte ansehen", "description": "Survey-Schritte und Flow anzeigen."},
        {"key": "steps.manage", "label": "Schritte verwalten", "description": "Schritte, Bedingungen und Vorlagen ändern."},
    ]},
    {"category": "Partner", "permissions": [
        {"key": "partners.view", "label": "Partner ansehen", "description": "Partnerliste und Verknüpfungen anzeigen."},
        {"key": "partners.manage", "label": "Partner verwalten", "description": "Partner erstellen, bearbeiten, verknüpfen und löschen."},
        {"key": "portal.partner.access", "label": "Partnerportal öffnen", "description": "Zugriff auf das Partner-Dashboard."},
        {"key": "partner.users.view", "label": "Partner-Benutzer ansehen", "description": "Zugeordnete Benutzer und deren Fortschritt anzeigen."},
        {"key": "partner.users.email.view", "label": "E-Mail-Adressen von Partner-Benutzern ansehen", "description": "E-Mail-Adressen von Benutzern im Partnerportal anzeigen. Bei zahlungspflichtigen Self-Service-Partnern wird zusätzlich eine bestätigte Zahlung vorausgesetzt."},
        {"key": "partner.users.manage", "label": "Partner-Benutzer bearbeiten", "description": "Fortschritte und Partneraktionen bearbeiten."},
    ]},
    {"category": "Inhalte und Kommunikation", "permissions": [
        {"key": "cms.view", "label": "CMS ansehen", "description": "Inhaltsseiten anzeigen."},
        {"key": "cms.manage", "label": "CMS verwalten", "description": "Inhaltsseiten und Übersetzungen bearbeiten."},
        {"key": "messages.view", "label": "Nachrichten ansehen", "description": "E-Mail-Vorlagen und Ereignisse anzeigen."},
        {"key": "messages.manage", "label": "Nachrichten verwalten", "description": "Vorlagen, Ereignisse und Testversand verwalten."},
        {"key": "settings.view", "label": "Einstellungen ansehen", "description": "Globale Einstellungen anzeigen."},
        {"key": "settings.manage", "label": "Einstellungen verwalten", "description": "Globale Einstellungen bearbeiten."},
    ]},
    {"category": "Eigenes Konto", "permissions": [
        {"key": "portal.user.access", "label": "Nutzerportal öffnen", "description": "Zugriff auf das persönliche Survey-Dashboard."},
        {"key": "profile.self.manage", "label": "Eigenes Profil bearbeiten", "description": "Eigene Profil- und Benachrichtigungseinstellungen ändern."},
        {"key": "survey.own.view", "label": "Eigenen Survey ansehen", "description": "Zugewiesene Survey-Schritte anzeigen."},
        {"key": "survey.own.submit", "label": "Eigenen Survey bearbeiten", "description": "Fortschritt und Antworten speichern."},
        {"key": "files.own.manage", "label": "Eigene Dateien verwalten", "description": "Dateien hochladen und abrufen."},
    ]},
]

ALL_PERMISSION_KEYS = tuple(
    permission["key"]
    for category in PERMISSION_CATALOG
    for permission in category["permissions"]
)
ALL_PERMISSION_SET = set(ALL_PERMISSION_KEYS)

DEFAULT_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "key": "administrators",
        "name": "Administratoren",
        "description": "Vollzugriff auf alle Bereiche und Einstellungen.",
        "role": "admin",
        "permissions": ["*"],
        "is_system": True,
    },
    {
        "key": "survey_users",
        "name": "Survey-Nutzer",
        "description": "Standardrechte für Benutzer des persönlichen Surveys.",
        "role": "user",
        "permissions": ["portal.user.access", "profile.self.manage", "survey.own.view", "survey.own.submit", "files.own.manage"],
        "is_system": True,
    },
    {
        "key": "partners",
        "name": "Partner",
        "description": "Standardrechte für das Partnerportal und zugeordnete Benutzer.",
        "role": "partner",
        "permissions": ["portal.partner.access", "profile.self.manage", "partner.users.view", "partner.users.email.view", "partner.users.manage", "files.own.manage"],
        "default_permission_version": 2,
        "is_system": True,
    },
)


def normalize_permissions(values: list[str] | None, allow_wildcard: bool = False) -> list[str]:
    return normalize_permission_values(values, frozenset(ALL_PERMISSION_SET), allow_wildcard)


async def effective_permissions(user: dict[str, Any]) -> list[str]:
    administrator = user.get("email") == os.environ.get("ADMIN_EMAIL", "admin@example.com")
    group_ids = [value for value in (user.get("group_ids") or []) if value]
    group_permissions: list[str] = []
    if group_ids:
        object_ids = []
        for group_id in group_ids:
            try:
                object_ids.append(ObjectId(group_id))
            except Exception:
                continue
        if object_ids:
            async for group in db.permission_groups.find({"_id": {"$in": object_ids}}):
                group_permissions.extend(group.get("permissions") or [])
    elif "permission_overrides" not in user:
        # Backward compatibility during the one-time startup migration and for
        # isolated test fixtures that still create legacy users.
        role = user.get("role", "user")
        fallback = next((group for group in DEFAULT_GROUPS if group["role"] == role), None)
        group_permissions.extend((fallback or {}).get("permissions", []))

    overrides = user.get("permission_overrides") or {}
    return resolve_effective_permissions(PermissionInputs(
        tuple(group_permissions), tuple(overrides.get("allow") or ()), tuple(overrides.get("deny") or ()),
        administrator,
    ), frozenset(ALL_PERMISSION_SET))


async def has_permission(user: dict[str, Any], permission: str) -> bool:
    permissions = await effective_permissions(user)
    return "*" in permissions or permission in permissions


async def permission_group_summaries(user: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    for group_id in user.get("group_ids") or []:
        try:
            group = await db.permission_groups.find_one({"_id": ObjectId(group_id)})
        except Exception:
            group = None
        if group:
            result.append({"id": str(group["_id"]), "name": group["name"], "role": group.get("role", "user")})
    return result


async def default_group_id(role: str) -> str | None:
    key_by_role = {"admin": "administrators", "user": "survey_users", "partner": "partners"}
    group = await db.permission_groups.find_one({"key": key_by_role.get(role, "survey_users")})
    return str(group["_id"]) if group else None


async def ensure_user_role_group(user: dict[str, Any]) -> dict[str, Any]:
    """Remove missing/foreign-role groups and ensure one compatible default.

    Custom groups for the user's current portal role are preserved. Permission
    overrides are deliberately untouched, so explicit denies remain effective.
    """
    role = user.get("role", "user")
    original_ids = [value for value in (user.get("group_ids") or []) if value]
    compatible_ids: list[str] = []
    object_ids = [ObjectId(value) for value in original_ids if ObjectId.is_valid(value)]
    if object_ids:
        async for group in db.permission_groups.find({"_id": {"$in": object_ids}, "role": role}, {"_id": 1}):
            compatible_ids.append(str(group["_id"]))
    compatible_ids = compatible_group_ids(original_ids, compatible_ids, await default_group_id(role))
    if compatible_ids != original_ids:
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"group_ids": compatible_ids}})
        user = {**user, "group_ids": compatible_ids}
    return user


async def ensure_permission_groups() -> int:
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    for definition in DEFAULT_GROUPS:
        existing = await db.permission_groups.find_one({"key": definition["key"]})
        if existing:
            # Apply each default-group capability migration once. Later admin
            # changes remain intact because the version marker is retained.
            target_version = definition.get("default_permission_version", 1)
            missing_defaults = [
                permission for permission in definition["permissions"]
                if permission not in (existing.get("permissions") or [])
            ]
            if existing.get("default_permission_version", 1) < target_version:
                update: dict[str, Any] = {"$set": {"updated_at": now, "default_permission_version": target_version}}
                if missing_defaults:
                    update["$addToSet"] = {"permissions": {"$each": missing_defaults}}
                await db.permission_groups.update_one(
                    {"_id": existing["_id"]},
                    update,
                )
            continue
        await db.permission_groups.insert_one({**definition, "name_key": definition["name"].casefold(), "created_at": now, "updated_at": now})
        created += 1
    defaults = {
        role: await default_group_id(role)
        for role in ("admin", "user", "partner")
    }
    async for user in db.users.find({"group_ids": {"$exists": False}}, {"role": 1}):
        group_id = defaults.get(user.get("role", "user"))
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"group_ids": [group_id] if group_id else [], "permission_overrides": {"allow": [], "deny": []}}},
        )
    await db.users.update_many(
        {"permission_overrides": {"$exists": False}},
        {"$set": {"permission_overrides": {"allow": [], "deny": []}}},
    )
    async for user in db.users.find({}, {"role": 1, "group_ids": 1}):
        await ensure_user_role_group(user)
    return created


def permission_for_admin_request(method: str, path: str) -> str | None:
    """Resolve granular permission for an /api/admin request."""
    return resolve_admin_permission(method, path)


def permission_for_portal_request(method: str, path: str) -> str | None:
    return resolve_portal_permission(method, path)
