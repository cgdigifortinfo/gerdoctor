"""HTTP error mapping for administrative user management."""
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, Field
from slices.admin_user_management.domain import (
    ConflictingPermissionOverrides, InvalidPartnerAssignment, InvalidRole, PrimaryAdminProtected,
)
from slices.admin_user_management.service import DuplicateEmail, InvalidSurvey, UnknownPartner, UserNotFound

class BulkRoleUpdate(BaseModel): user_ids: list[str]; role: str
class AdminUserCreate(BaseModel):
    email: EmailStr; password: str; name: str; role: str = "user"
    partner_id: str | None = None; survey_id: str | None = None; group_ids: list[str] | None = None
class UserPermissionsUpdate(BaseModel):
    group_ids: list[str] = Field(default_factory=list)
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class AdminUserProgressUpdate(BaseModel):
    step_id: str
    status: str
    data: dict[str, Any] | None = None


def admin_user_http_error(error: Exception) -> HTTPException:
    if isinstance(error, UserNotFound): return HTTPException(404, "User not found")
    if isinstance(error, InvalidRole): return HTTPException(400, "Invalid role")
    if isinstance(error, InvalidPartnerAssignment): return HTTPException(400, "Only partner users can be assigned to a partner")
    if isinstance(error, UnknownPartner): return HTTPException(400, "Unknown partner id")
    if isinstance(error, InvalidSurvey): return HTTPException(400, "Invalid or inactive survey")
    if isinstance(error, DuplicateEmail): return HTTPException(400, "Email already registered")
    if isinstance(error, PrimaryAdminProtected): return HTTPException(400, "Primary admin account is protected")
    if isinstance(error, ConflictingPermissionOverrides): return HTTPException(400, "A permission cannot be both allowed and denied")
    return HTTPException(400, "Invalid user management operation")
