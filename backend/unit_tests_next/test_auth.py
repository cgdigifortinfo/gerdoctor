"""Unit contracts for passwords, JWTs, and request authentication."""

from datetime import datetime, timezone
import asyncio

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

import auth

TOKEN_SECRET = "unit-test-token-secret-at-least-32-bytes-long"


class FakeUsers:
    def __init__(self, user=None):
        self.user = user
        self.last_query = None

    async def find_one(self, query):
        self.last_query = query
        return dict(self.user) if self.user else None


class FakeDb:
    def __init__(self, user=None):
        self.users = FakeUsers(user)


def request(*, authorization="", cookie=""):
    headers = []
    if authorization:
        headers.append((b"authorization", authorization.encode()))
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


class TestPasswords:
    def test_hash_is_salted_and_verifies(self):
        first = auth.hash_password("correct horse battery staple")
        second = auth.hash_password("correct horse battery staple")
        assert first != second
        assert auth.verify_password("correct horse battery staple", first) is True
        assert auth.verify_password("wrong", first) is False

    @pytest.mark.parametrize("stored", ["", "plain-text", "$2b$broken"])
    def test_malformed_stored_hash_is_a_failed_login_not_a_server_error(self, stored):
        assert auth.verify_password("password", stored) is False


class TestTokens:
    def test_access_token_has_expected_claims(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", TOKEN_SECRET)
        token = auth.create_access_token("507f1f77bcf86cd799439011", "user@example.org", "user")
        payload = jwt.decode(token, TOKEN_SECRET, algorithms=[auth.JWT_ALGORITHM])
        assert payload["sub"] == "507f1f77bcf86cd799439011"
        assert payload["email"] == "user@example.org"
        assert payload["role"] == "user"
        assert payload["type"] == "access"
        assert datetime.fromtimestamp(payload["exp"], timezone.utc) > datetime.now(timezone.utc)

    def test_refresh_token_cannot_be_used_as_access_token(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", TOKEN_SECRET)
        token = auth.create_refresh_token("507f1f77bcf86cd799439011")
        with pytest.raises(HTTPException) as exc:
            import asyncio
            asyncio.run(auth.get_current_user(request(authorization=f"Bearer {token}")))
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid token type"


class TestCurrentUser:
    def test_missing_credentials_are_rejected(self):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(auth.get_current_user(request()))
        assert (exc.value.status_code, exc.value.detail) == (401, "Not authenticated")

    def test_bearer_token_loads_user_and_removes_password_hash(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", TOKEN_SECRET)
        fake_db = FakeDb({
            "_id": "507f1f77bcf86cd799439011",
            "email": "user@example.org",
            "role": "user",
            "password_hash": "secret",
        })
        monkeypatch.setattr(auth, "db", fake_db)
        token = auth.create_access_token("507f1f77bcf86cd799439011", "user@example.org", "user")
        user = asyncio.run(auth.get_current_user(request(authorization=f"Bearer {token}")))
        assert user["_id"] == "507f1f77bcf86cd799439011"
        assert "password_hash" not in user

    def test_cookie_is_used_when_bearer_header_is_absent(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", TOKEN_SECRET)
        monkeypatch.setattr(auth, "db", FakeDb({"_id": "507f1f77bcf86cd799439011", "role": "user"}))
        token = auth.create_access_token("507f1f77bcf86cd799439011", "user@example.org", "user")
        user = asyncio.run(auth.get_current_user(request(cookie=f"access_token={token}")))
        assert user["role"] == "user"

    def test_invalid_subject_is_rejected_as_invalid_token(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", TOKEN_SECRET)
        token = jwt.encode({"sub": "not-an-object-id", "type": "access"}, TOKEN_SECRET, algorithm=auth.JWT_ALGORITHM)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(auth.get_current_user(request(authorization=f"Bearer {token}")))
        assert (exc.value.status_code, exc.value.detail) == (401, "Invalid token")

    def test_deleted_user_is_rejected(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", TOKEN_SECRET)
        monkeypatch.setattr(auth, "db", FakeDb())
        token = auth.create_access_token("507f1f77bcf86cd799439011", "user@example.org", "user")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(auth.get_current_user(request(authorization=f"Bearer {token}")))
        assert (exc.value.status_code, exc.value.detail) == (401, "User not found")
