"""Identity resolution application service."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from slices.identity_access.ports import IdentityRepository
from slices.identity_access.domain import (
    initial_progress, login_identifier, login_is_locked, normalized_email,
    partner_registration_documents, user_registration_document,
)
from slices.identity_access.models import RegisteredAccount


class IdentityAccessError(ValueError): pass
class InvalidAccessToken(IdentityAccessError): pass
class IdentityNotFound(IdentityAccessError): pass
class DuplicateEmail(IdentityAccessError): pass
class LoginLocked(IdentityAccessError): pass
class InvalidCredentials(IdentityAccessError): pass
class InvalidResetToken(IdentityAccessError): pass
class ExpiredResetToken(IdentityAccessError): pass


class IdentityAccessService:
    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    async def current_user(self, claims: Mapping[str, Any]) -> dict[str, Any]:
        if claims.get("type") != "access":
            raise InvalidAccessToken
        user = await self._repository.find_user(claims.get("sub"))
        if user is None:
            raise IdentityNotFound
        result = dict(user)
        result["_id"] = str(result["_id"])
        result.pop("password_hash", None)
        return result

    async def user(self, user_id: object) -> dict[str, Any] | None:
        try: return await self._repository.find_user(user_id)
        except Exception: return None

    async def update_profile(self, user_id: object, values: Mapping[str, Any]) -> None:
        fields = {key: value for key, value in values.items() if value is not None}
        name = fields.pop("name", None)
        if name is not None:
            await self._repository.update_user(user_id, {"name": name})
        if fields:
            await self._repository.update_user(
                user_id, {f"profile.{key}": value for key, value in fields.items()},
            )

    async def update_notification_preferences(
        self, user_id: object, values: Mapping[str, Any],
    ) -> None:
        await self._repository.update_user(user_id, {"notification_preferences": dict(values)})

    async def register_user(self, data: Mapping[str, Any], survey: Mapping[str, Any], group_id: str | None,
                            password_hash: str, timestamp: str, default_slug: str) -> RegisteredAccount:
        email = normalized_email(str(data["email"]))
        if await self._repository.user_by_email(email): raise DuplicateEmail
        document = user_registration_document(email, password_hash, str(data["name"]), survey,
                                              group_id, timestamp, default_slug)
        user_id, native_id = await self._repository.insert_user(document)
        survey_id = str(survey["_id"]); steps = await self._repository.steps(survey_id)
        await self._repository.insert_progress(initial_progress(user_id, survey_id, steps, timestamp))
        return RegisteredAccount(user_id, {**document, "_id": native_id})

    async def register_partner(self, data: Mapping[str, Any], group_id: str | None,
                               password_hash: str, timestamp: str) -> RegisteredAccount:
        email = normalized_email(str(data["email"]))
        if await self._repository.user_by_email(email): raise DuplicateEmail
        user, partner = partner_registration_documents(data, password_hash, group_id, timestamp)
        user_id, native_id = await self._repository.insert_user(user); partner["user_id"] = user_id
        partner_id = await self._repository.insert_partner(partner)
        await self._repository.update_user(native_id, {"partner_id": partner_id})
        return RegisteredAccount(user_id, {**user, "_id": native_id, "partner_id": partner_id}, partner_id)

    async def authenticate(self, email: str, password: str, ip: str,
                           verify: Callable[[str, str], bool], now: datetime) -> dict[str, Any]:
        normalized = normalized_email(email); identifier = login_identifier(ip, normalized)
        attempt = await self._repository.login_attempt(identifier)
        if login_is_locked(attempt, now): raise LoginLocked
        if attempt and int(attempt.get("count", 0)) >= 5: await self._repository.clear_login_attempt(identifier)
        user = await self._repository.user_by_email(normalized)
        if not user or not verify(password, str(user.get("password_hash", ""))):
            await self._repository.record_failed_login(identifier, (now + timedelta(minutes=15)).isoformat())
            raise InvalidCredentials
        await self._repository.clear_login_attempt(identifier); return user

    async def begin_password_reset(self, email: str, token: str, now: datetime) -> dict[str, Any] | None:
        user = await self._repository.user_by_email(normalized_email(email))
        if user is None: return None
        user_id = str(user["_id"]); await self._repository.consume_reset_tokens(user_id)
        await self._repository.insert_reset_token({"user_id": user_id, "token": token,
                                                   "expires_at": now + timedelta(hours=1), "used": False})
        return user

    async def reset_password(self, token: str, password_hash: str, now: datetime) -> None:
        document = await self._repository.reset_token(token)
        if document is None: raise InvalidResetToken
        expires_at = document["expires_at"]
        if isinstance(expires_at, str): expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now: raise ExpiredResetToken
        await self._repository.update_user(document["user_id"], {"password_hash": password_hash})
        await self._repository.mark_reset_token_used(token)
