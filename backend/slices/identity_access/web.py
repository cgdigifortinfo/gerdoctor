"""HTTP request extraction and error creation for identity access."""
from typing import Any
from fastapi import HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from slices.identity_access.service import (
    DuplicateEmail, ExpiredResetToken, InvalidCredentials, InvalidResetToken, LoginLocked,
)

class UserRegister(BaseModel):
    email: EmailStr; password: str; name: str; survey_slug: str | None = None
class PartnerRegister(BaseModel):
    company_name: str = Field(min_length=2,max_length=160)
    contact_name: str = Field(min_length=2,max_length=160)
    email: EmailStr; password: str = Field(min_length=8); website: str | None = None
    description: str | None = ""; country: str = Field(default="DE",min_length=2,max_length=2)
class UserLogin(BaseModel): email: EmailStr; password: str
class ForgotPassword(BaseModel): email: EmailStr
class ResetPassword(BaseModel): token: str; new_password: str


class ProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    bio: str | None = None
    date_of_birth: str | None = None
    profile_image_id: str | None = None


class NotificationPreferences(BaseModel):
    email_on_step_enter: bool = True
    email_on_step_edit: bool = False
    email_on_step_leave: bool = True


def access_token_from_request(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        return authorization[7:]
    token = request.cookies.get("access_token")
    if token:
        return token
    raise HTTPException(status_code=401, detail="Not authenticated")


def identity_http_error(detail: str, status_code: int = 401) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)

def account_http_error(error: Exception) -> HTTPException:
    if isinstance(error, DuplicateEmail): return HTTPException(400, "Email already registered")
    if isinstance(error, LoginLocked): return HTTPException(429, "Too many failed attempts. Try again later.")
    if isinstance(error, InvalidCredentials): return HTTPException(401, "Invalid email or password")
    if isinstance(error, InvalidResetToken): return HTTPException(400, "Invalid or expired token")
    if isinstance(error, ExpiredResetToken): return HTTPException(400, "Token expired")
    return HTTPException(400, "Invalid account operation")
