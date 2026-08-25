"""Authentication utilities: JWT, password hashing, user extraction."""
import os
import jwt
from collections.abc import Awaitable, Callable
from typing import Any
from fastapi import HTTPException, Request
from database import db
from infrastructure.clock import system_utc_clock
from slices.identity_access.tokens import IdentityTokenCodec
from slices.identity_access.passwords import hash_password, verify_password
from slices.identity_access.web import access_token_from_request
from slices.identity_access.repository import InvalidUserIdentifier, MongoIdentityRepository
from slices.identity_access.service import IdentityAccessService, IdentityNotFound, InvalidAccessToken

JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

def _token_codec() -> IdentityTokenCodec:
    return IdentityTokenCodec(get_jwt_secret(), system_utc_clock, JWT_ALGORITHM)

def create_access_token(user_id: str, email: str, role: str) -> str:
    return _token_codec().access_token(user_id, email, role)

def create_refresh_token(user_id: str) -> str:
    return _token_codec().refresh_token(user_id)

async def get_current_user(request: Request) -> dict[str, Any]:
    token = access_token_from_request(request)
    try:
        payload = _token_codec().decode(token)
        return await IdentityAccessService(MongoIdentityRepository(db)).current_user(payload)
    except InvalidAccessToken:
        raise HTTPException(status_code=401, detail="Invalid token type")
    except IdentityNotFound:
        raise HTTPException(status_code=401, detail="User not found")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except (InvalidUserIdentifier, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*roles: str) -> Callable[[Request], Awaitable[dict[str, Any]]]:
    async def check_role(request: Request) -> dict[str, Any]:
        user = await get_current_user(request)
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role


def require_permission(permission: str, *roles: str) -> Callable[[Request], Awaitable[dict[str, Any]]]:
    async def check_permission(request: Request) -> dict[str, Any]:
        from slices.groups_permissions.permissions import has_permission

        user = await get_current_user(request)
        if roles and user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if not await has_permission(user, permission):
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return user
    return check_permission
