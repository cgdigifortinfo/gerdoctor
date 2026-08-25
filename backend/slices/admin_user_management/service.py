"""Application service for administrative user lifecycle operations."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any
from slices.admin_user_management.domain import (
    archived_user_fields, ensure_primary_admin_change, initial_progress,
    new_user_document, permission_overrides, role_fields, search_query,
    validate_partner_assignment, validated_role,
)
from slices.admin_user_management.models import CreatedUser, CreateUserCommand
from slices.admin_user_management.ports import AdminUserRepository

GroupValidator = Callable[[Sequence[str], str], Awaitable[list[str]]]
DefaultGroup = Callable[[str], Awaitable[str | None]]
DefaultSurvey = Callable[[], Awaitable[dict[str, Any] | None]]
AuditWriter = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]
FileProtector = Callable[[str, str], Awaitable[None]]

class AdminUserError(ValueError): pass
class UserNotFound(AdminUserError): pass
class DuplicateEmail(AdminUserError): pass
class UnknownPartner(AdminUserError): pass
class InvalidSurvey(AdminUserError): pass


class AdminUserManagementService:
    def __init__(self, repository: AdminUserRepository, now: Callable[[], str],
                 hash_password: Callable[[str], str], validate_groups: GroupValidator,
                 default_group: DefaultGroup, default_survey: DefaultSurvey,
                 audit: AuditWriter, protect_files: FileProtector,
                 primary_admin_email: str, default_survey_slug: str) -> None:
        self._repository, self._now, self._hash = repository, now, hash_password
        self._validate_groups, self._default_group = validate_groups, default_group
        self._default_survey, self._audit, self._protect_files = default_survey, audit, protect_files
        self._primary_email, self._default_slug = primary_admin_email, default_survey_slug

    async def search(self, text: str, role: str) -> list[dict[str, Any]]:
        users = await self._repository.search(search_query(text, role))
        return [{"id": str(user["_id"]), "email": user["email"], "name": user["name"],
                 "role": user["role"], "created_at": user.get("created_at"),
                 "partner_id": user.get("partner_id"), "group_ids": user.get("group_ids", [])}
                for user in users]

    async def user(self, user_id: str) -> dict[str, Any] | None:
        return await self._repository.user(user_id)

    async def create(self, command: CreateUserCommand, actor: Mapping[str, Any]) -> CreatedUser:
        role = validated_role(command.role); validate_partner_assignment(role, command.partner_id)
        email = command.email.lower()
        if await self._repository.user_by_email(email): raise DuplicateEmail
        partner = None
        if command.partner_id:
            partner = await self._repository.partner(command.partner_id)
            if partner is None: raise UnknownPartner
        survey = None
        if role == "user":
            if command.survey_id:
                survey = await self._repository.survey(command.survey_id)
                if survey is None: raise InvalidSurvey
            else: survey = await self._default_survey()
        groups = (await self._validate_groups(command.group_ids, role)) if command.group_ids else []
        if not groups:
            default = await self._default_group(role); groups = [default] if default else []
        timestamp = self._now()
        document = new_user_document(email, self._hash(command.password), command.name, role,
                                     groups, timestamp, survey, command.partner_id, self._default_slug)
        user_id = await self._repository.insert_user(document)
        survey_id = str(survey["_id"]) if survey else None
        if survey_id:
            steps = await self._repository.survey_steps(survey_id)
            await self._repository.insert_progress(initial_progress(user_id, survey_id, steps, timestamp))
        if partner and command.partner_id: await self._repository.link_partner(command.partner_id, user_id)
        await self._audit(actor.get("_id", ""), actor.get("email", ""), "user_create", "user", user_id,
                          {"email": email, "role": role, "survey_id": survey_id})
        return CreatedUser(user_id, survey_id, str(survey.get("slug")) if survey and survey.get("slug") else None)

    async def change_role(self, user_id: str, role: str, actor: Mapping[str, Any]) -> None:
        validated_role(role); target = await self._repository.user(user_id)
        if target is None: raise UserNotFound
        ensure_primary_admin_change(str(target.get("email", "")), self._primary_email, role)
        group = await self._default_group(role)
        await self._repository.update_user(user_id, role_fields(role, group))
        await self._audit(actor.get("_id", ""), actor.get("email", ""), "role_change", "user", user_id, {"new_role": role})

    async def bulk_role(self, user_ids: Sequence[str], role: str) -> int:
        validated_role(role); group = await self._default_group(role); fields = role_fields(role, group); updated = 0
        for user_id in user_ids:
            target = await self._repository.user(user_id)
            if target is None: continue
            try: ensure_primary_admin_change(str(target.get("email", "")), self._primary_email, role)
            except Exception: continue
            if await self._repository.update_user(user_id, fields): updated += 1
        return updated

    async def archive(self, user_id: str, actor: Mapping[str, Any]) -> None:
        target = await self._repository.user(user_id)
        if target is None: raise UserNotFound
        email = str(target["email"]); ensure_primary_admin_change(email, self._primary_email)
        timestamp = self._now(); await self._protect_files(user_id, timestamp)
        await self._repository.unlink_partners(user_id, target.get("partner_id"))
        await self._repository.update_user(user_id, archived_user_fields(
            user_id, email, target.get("archived_original_email"), str(actor.get("_id", "")), timestamp))
        await self._audit(actor.get("_id", ""), actor.get("email", ""), "user_delete", "user", user_id,
                          {"email": email, "soft_delete": True, "historical_files_protected": True})

    async def update_permissions(self, user_id: str, group_ids: Sequence[str], allow: Sequence[str],
                                 deny: Sequence[str], validate_permissions: Callable[[Sequence[str]], list[str]]) -> tuple[list[str], dict[str, list[str]]]:
        target = await self._repository.user(user_id)
        if target is None: raise UserNotFound
        ensure_primary_admin_change(str(target.get("email", "")), self._primary_email, None)
        groups = await self._validate_groups(group_ids, str(target.get("role", "user")))
        overrides = permission_overrides(validate_permissions(allow), validate_permissions(deny))
        await self._repository.update_user(user_id, {"group_ids": groups, "permission_overrides": overrides,
                                                     "updated_at": self._now()})
        return groups, overrides
