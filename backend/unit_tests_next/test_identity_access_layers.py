from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import jwt
import pytest
from bson import ObjectId
from fastapi import HTTPException
from starlette.requests import Request

from slices.identity_access.tokens import IdentityTokenCodec
from slices.identity_access.repository import InvalidUserIdentifier, MongoIdentityRepository
from slices.identity_access.service import IdentityAccessService, IdentityNotFound, InvalidAccessToken
from slices.identity_access.web import access_token_from_request, identity_http_error


class Clock:
    def now(self): return datetime(2030, 1, 1, tzinfo=timezone.utc)  # type: ignore[no-untyped-def]
    def now_iso(self): return self.now().isoformat()  # type: ignore[no-untyped-def]


def request(headers=(), cookie: str = "") -> Request:  # type: ignore[no-untyped-def]
    values = list(headers)
    if cookie: values.append((b"cookie", cookie.encode()))
    return Request({"type": "http", "headers": values})


def test_token_codec_and_web_token_extraction():
    codec = IdentityTokenCodec("identity-unit-test-secret-32-bytes", Clock())
    access = codec.access_token("u", "e", "user")
    refresh = codec.refresh_token("u")
    assert codec.decode(access)["type"] == "access" and codec.decode(refresh)["type"] == "refresh"
    assert access_token_from_request(request([(b"authorization", f"Bearer {access}".encode())])) == access
    assert access_token_from_request(request(cookie=f"access_token={access}")) == access
    with pytest.raises(HTTPException): access_token_from_request(request())
    error = identity_http_error("Denied", 403)
    assert (error.status_code, error.detail) == (403, "Denied")


class Users:
    def __init__(self, user): self.user = user
    async def find_one(self, query): return self.user  # type: ignore[no-untyped-def]


def test_repository_and_service_resolve_sanitized_identity():
    async def scenario() -> None:
        user_id = ObjectId()
        repository = MongoIdentityRepository(SimpleNamespace(users=Users({"_id": user_id, "password_hash": "x", "role": "user"})))
        user = await IdentityAccessService(repository).current_user({"sub": str(user_id), "type": "access"})
        assert user == {"_id": str(user_id), "role": "user"}
        with pytest.raises(InvalidUserIdentifier): await repository.find_user("invalid")
        with pytest.raises(InvalidAccessToken): await IdentityAccessService(repository).current_user({"type": "refresh"})
        missing = MongoIdentityRepository(SimpleNamespace(users=Users(None)))
        with pytest.raises(IdentityNotFound): await IdentityAccessService(missing).current_user({"sub": str(user_id), "type": "access"})
    asyncio.run(scenario())
