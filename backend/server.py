"""
IHCA API - Main application entry point.
Shared utilities are imported from database.py, models.py, auth.py, helpers.py.
Routes are organized by domain in this file.
"""
from dotenv import load_dotenv
load_dotenv()

import os
import logging
import secrets
import hashlib
import hmac
import json
import time
import uuid
import asyncio
import jwt
from pathlib import PurePath
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

# Shared modules
from database import db, client
from models import (
    UserRegister, PartnerRegister, UserLogin, ForgotPassword, ResetPassword, ProfileUpdate,
    PartnerCreate, PartnerUpdate, StepCreate, StepUpdate, StepReorder, StepFieldCreate,
    UserProgressUpdate, PartnerSubmissionCreate, MultiPartnerSubmission,
    CMSContentUpdate, NotificationPreferences, BulkRoleUpdate, AdminUserCreate, SiteSettingsUpdate,
    StepTemplateCreate, StepTemplateUpdate, PartnerSelfUpdate, PartnerBillingSettingsUpdate, StepLayoutBulk,
    SurveyCreate, SurveyUpdate, PartnerStepAction, EventConfigUpdate, StepResponse,
    PermissionGroupCreate, PermissionGroupUpdate, UserPermissionsUpdate,
)
from stripe_service import (
    SECRET_FIELDS, public_stripe_status, create_customer,
    create_checkout_session, checkout_session, create_customer_portal, list_customer_invoices,
    create_pending_invoice_item, retrieve_customer, find_customers_by_email,
    retrieve_subscription, list_customer_subscriptions,
)
from auth import (
    get_jwt_secret, JWT_ALGORITHM, hash_password, verify_password,
    create_access_token, create_refresh_token, get_current_user, require_role, require_permission
)
from helpers import (
    init_storage, put_object, get_object, APP_NAME,
    send_email_notification, create_audit_log, notify_partner_of_new_submission,
    notify_user_awaiting_partner, notify_user_milestone_completed,
    render_email, render_notification, send_rendered_email, _partner_deep_link,
    calculate_completion_pct, calculate_estimated_completion,
    calculate_users_metrics, calculate_metrics_from_loaded_context,
    apply_auto_completes, _get_step_context,
    apply_anerkennungsstatus_skips, _evaluate_condition,
)
from form_builder import (
    CONTENT_FIELD_TYPES, FORM_SCHEMA_VERSION,
    migrate_database_form_configs, normalize_step_field,
)
from permissions import (
    ALL_PERMISSION_KEYS, PERMISSION_CATALOG, default_group_id,
    effective_permissions, ensure_permission_groups, ensure_user_role_group, has_permission,
    normalize_permissions, permission_for_admin_request, permission_for_portal_request,
    permission_group_summaries, partner_is_awaiting_assignment,
)
from email_template_defaults import DEFAULT_TEMPLATES
from event_system import (
    ensure_event_configs, emit_domain_event, process_domain_event,
    retry_domain_event, serialize_event_document,
)

logger = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)

# ========================
# APP & ROUTERS
# ========================
app = FastAPI()


@app.middleware("http")
async def enforce_admin_permissions(request: Request, call_next):
    admin_permission = permission_for_admin_request(request.method, request.url.path)
    permission = admin_permission or permission_for_portal_request(request.method, request.url.path)
    if not permission:
        return await call_next(request)
    try:
        user = await get_current_user(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if (admin_permission and user.get("role") != "admin") or not await has_permission(user, permission):
        return JSONResponse(status_code=403, content={"detail": f"Missing permission: {permission}"})
    if path := request.url.path:
        own_settings_paths = {"/api/partner/profile", "/api/partner/partner-data"}
        pending_read_paths = {"/api/partner/other-users"}
        if path.startswith("/api/partner/") and path not in own_settings_paths and user.get("role") == "partner" and user.get("partner_id") and ObjectId.is_valid(user["partner_id"]):
            partner = await db.partners.find_one(
                {"_id": ObjectId(user["partner_id"])},
                {"registration_source": 1, "registration_status": 1, "is_active": 1, "survey_ids": 1, "billing_status": 1},
            )
            pending_read_allowed = request.method == "GET" and path in pending_read_paths
            if partner_is_awaiting_assignment(partner) and not pending_read_allowed:
                return JSONResponse(status_code=403, content={"detail": "Partner account is awaiting survey assignment"})
    request.state.current_user = user
    return await call_next(request)

api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
partner_router = APIRouter(prefix="/partners", tags=["partners"])
payment_router = APIRouter(prefix="/partner-payment", tags=["partner-payment"])
steps_router = APIRouter(prefix="/steps", tags=["steps"])
files_router = APIRouter(prefix="/files", tags=["files"])
cms_router = APIRouter(prefix="/cms", tags=["cms"])

DEFAULT_SURVEY_SLUG = "aerzte"
PFLEGE_SURVEY_SLUG = "pflege"
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
ALLOWED_UPLOAD_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "webp", "gif",
    "doc", "docx", "xls", "xlsx", "csv", "txt", "zip",
}
BLOCKED_UPLOAD_CONTENT_TYPES = {
    "text/html", "application/xhtml+xml", "image/svg+xml",
    "application/javascript", "text/javascript",
}

def _survey_payload(s: dict) -> dict:
    return {
        "id": str(s["_id"]),
        "name": s.get("name", ""),
        "slug": s.get("slug", ""),
        "description": s.get("description", ""),
        "audience": s.get("audience", ""),
        "is_active": s.get("is_active", True),
        "is_default": s.get("is_default", False),
        "theme": s.get("theme", {}),
        "created_at": s.get("created_at"),
        "updated_at": s.get("updated_at"),
    }

async def _get_default_survey() -> dict:
    survey = await db.surveys.find_one({"is_default": True})
    if not survey:
        survey = await db.surveys.find_one({"slug": DEFAULT_SURVEY_SLUG})
    if not survey:
        now = datetime.now(timezone.utc).isoformat()
        result = await db.surveys.insert_one({
            "name": "Ärzte Anerkennung",
            "slug": DEFAULT_SURVEY_SLUG,
            "description": "Anerkennungs- und Arbeitseinstiegsprozess fuer internationale Aerztinnen und Aerzte.",
            "audience": "Internationale Aerztinnen und Aerzte",
            "is_active": True,
            "is_default": True,
            "theme": {},
            "created_at": now,
            "updated_at": now,
        })
        survey = await db.surveys.find_one({"_id": result.inserted_id})
    return survey

async def _get_survey_by_slug(slug: Optional[str]) -> dict:
    if not slug:
        return await _get_default_survey()
    survey = await db.surveys.find_one({"slug": slug, "is_active": True})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey

async def _get_user_survey(user: dict, survey_slug: Optional[str] = None) -> dict:
    if survey_slug:
        return await _get_survey_by_slug(survey_slug)
    sid = user.get("survey_id")
    if sid:
        try:
            survey = await db.surveys.find_one({"_id": ObjectId(sid)})
            if survey:
                return survey
        except Exception:
            pass
    return await _get_default_survey()

def _step_query_for_survey(survey_id: str, active_only: bool = True) -> dict:
    query = {"survey_id": survey_id}
    if active_only:
        query["is_active"] = True
    return query


def _admin_step_payload(step: dict) -> dict:
    """Serialize a MongoDB step document into the public admin contract."""
    return {
        "id": str(step["_id"]),
        "survey_id": step.get("survey_id", ""),
        "title": step["title"],
        "description": step.get("description", ""),
        "order": step["order"],
        "step_type": step["step_type"],
        "fields": step.get("fields", []),
        "form_schema_version": step.get("form_schema_version", FORM_SCHEMA_VERSION),
        "filter_tag": step.get("filter_tag", ""),
        "partner_user_fee_cents": step.get("partner_user_fee_cents"),
        "skippable": step.get("skippable", False),
        "skip_label": step.get("skip_label", ""),
        "action_label": step.get("action_label", ""),
        "pending_message": step.get("pending_message", ""),
        "complete_message": step.get("complete_message", ""),
        "required_fields": step.get("required_fields", []),
        "required_uploads": step.get("required_uploads", []),
        "field_mappings": step.get("field_mappings", []),
        "conditions": step.get("conditions", []),
        "email_on_enter": step.get("email_on_enter", False),
        "email_on_edit": step.get("email_on_edit", False),
        "email_on_leave": step.get("email_on_leave", False),
        "email_subject_enter": step.get("email_subject_enter", ""),
        "email_body_enter": step.get("email_body_enter", ""),
        "email_subject_edit": step.get("email_subject_edit", ""),
        "email_body_edit": step.get("email_body_edit", ""),
        "email_subject_leave": step.get("email_subject_leave", ""),
        "email_body_leave": step.get("email_body_leave", ""),
        "is_active": step.get("is_active", True),
        "duration_value": step.get("duration_value", 0),
        "duration_unit": step.get("duration_unit", "days"),
        "translations": step.get("translations", {}),
        "flow_position": step.get("flow_position"),
    }

def _auth_cookie_kwargs(max_age: int) -> dict:
    frontend_url = os.environ.get("FRONTEND_URL", "")
    local_http = frontend_url.startswith("http://localhost") or frontend_url.startswith("http://127.0.0.1")
    return {
        "httponly": True,
        "secure": not local_http,
        "samesite": "lax" if local_http else "none",
        "max_age": max_age,
        "path": "/",
    }


async def _auth_user_payload(user: dict, access_token: str | None = None) -> dict:
    payload = {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "profile": user.get("profile", {}),
        "survey_id": user.get("survey_id"),
        "survey_slug": user.get("survey_slug"),
        "group_ids": user.get("group_ids", []),
        "permission_groups": await permission_group_summaries(user),
        "permission_overrides": user.get("permission_overrides", {"allow": [], "deny": []}),
        "permissions": await effective_permissions(user),
        "is_primary_admin": user.get("email") == os.environ.get("ADMIN_EMAIL", "admin@example.com"),
    }
    if user.get("role") == "partner" and user.get("partner_id") and ObjectId.is_valid(user["partner_id"]):
        partner = await db.partners.find_one({"_id": ObjectId(user["partner_id"])}, {
            "registration_status": 1, "registration_source": 1, "billing_status": 1,
            "access_unlocked": 1, "is_active": 1,
        })
        payload["partner_registration_status"] = (partner or {}).get("registration_status", "active")
        payload["partner_is_active"] = (partner or {}).get("is_active", True)
        payload["partner_billing_status"] = (partner or {}).get("billing_status", "pending")
        payload["partner_payment_required"] = (partner or {}).get("registration_source") == "self_service"
    if access_token:
        payload["access_token"] = access_token
    return payload

def _safe_object_id(value: str, label: str = "Invalid id") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail=label)
    return ObjectId(value)

def _safe_upload_extension(filename: str) -> str:
    basename = PurePath(filename or "").name
    ext = basename.rsplit(".", 1)[-1].lower() if "." in basename else ""
    if not ext or ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    return ext

async def _can_access_file(user: dict, file_doc: dict) -> bool:
    owner_id = file_doc.get("user_id")
    if not owner_id:
        return False
    if user.get("role") == "admin" or user.get("_id") == owner_id:
        return True
    if user.get("role") == "user" and await db.user_progress.find_one({
        "user_id": user.get("_id"),
        "$or": [
            {"data.partner_uploads.file_id": file_doc.get("id")},
            {"data.documents.file_id": file_doc.get("id")},
        ],
    }, {"_id": 1}):
        return True
    if user.get("role") != "partner" or not user.get("partner_id"):
        return False
    partner = await db.partners.find_one(
        {"_id": _safe_object_id(user["partner_id"], "Invalid partner id")},
        {"linked_user_ids": 1},
    )
    if owner_id in set((partner or {}).get("linked_user_ids", [])):
        return True
    return bool(await db.partner_submissions.find_one({
        "partner_id": user["partner_id"],
        "user_id": owner_id,
    }, {"_id": 1}))

# ========================
# AUTH ROUTES
# ========================

@auth_router.post("/register")
async def register(data: UserRegister, response: Response):
    email = data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    survey = await _get_survey_by_slug(data.survey_slug)
    survey_id = str(survey["_id"])
    group_id = await default_group_id("user")
    user_doc = {
        "email": email, "password_hash": hash_password(data.password),
        "name": data.name, "role": "user", "profile": {},
        "survey_id": survey_id, "survey_slug": survey.get("slug", DEFAULT_SURVEY_SLUG),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "group_ids": [group_id] if group_id else [],
        "permission_overrides": {"allow": [], "deny": []},
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    steps = await db.steps.find(_step_query_for_survey(survey_id)).sort("order", 1).to_list(100)
    now_iso = datetime.now(timezone.utc).isoformat()
    if steps:
        await db.user_progress.insert_many([{
            "user_id": user_id,
            "step_id": str(step["_id"]),
            "survey_id": survey_id,
            "step_order": step.get("order"),
            "status": "pending",
            "data": {},
            "created_at": now_iso,
            "updated_at": now_iso,
        } for step in steps])
    access_token = create_access_token(user_id, email, "user")
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="access_token", value=access_token, **_auth_cookie_kwargs(7200))
    response.set_cookie(key="refresh_token", value=refresh_token, **_auth_cookie_kwargs(604800))
    user_doc["_id"] = result.inserted_id
    return await _auth_user_payload(user_doc, access_token)


@api_router.get("/partner-registration/config")
async def partner_registration_config():
    return {"registration_enabled": True, "stripe": await public_stripe_status()}


@api_router.post("/partner-registration")
async def register_partner(data: PartnerRegister, response: Response):
    email = data.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    now = datetime.now(timezone.utc).isoformat()
    group_id = await default_group_id("partner")
    user_doc = {
        "email": email, "password_hash": hash_password(data.password),
        "name": data.contact_name, "role": "partner", "profile": {},
        "created_at": now, "group_ids": [group_id] if group_id else [],
        "permission_overrides": {"allow": [], "deny": []},
        "registration_source": "partner_self_service",
    }
    user_result = await db.users.insert_one(user_doc)
    user_id = str(user_result.inserted_id)
    partner_doc = {
        "name": data.company_name, "description": data.description or "",
        "website": data.website, "contact_email": email, "country": data.country.upper(),
        "category": "", "tags": [], "linked_user_ids": [], "survey_ids": [],
        "user_id": user_id, "is_active": False, "registration_status": "pending",
        "registration_source": "self_service", "registered_at": now, "created_at": now,
        "billing_status": "pending", "access_unlocked": False,
        "billing_settings": {"legal_name": data.company_name, "country": data.country.upper(), "default_currency": "eur"},
    }
    partner_result = await db.partners.insert_one(partner_doc)
    partner_id = str(partner_result.inserted_id)
    await db.users.update_one({"_id": user_result.inserted_id}, {"$set": {"partner_id": partner_id}})
    await create_audit_log(user_id, email, "partner_self_registration", "partner", partner_id, {"company_name": data.company_name})
    access_token = create_access_token(user_id, email, "partner")
    response.set_cookie(key="access_token", value=access_token, **_auth_cookie_kwargs(7200))
    response.set_cookie(key="refresh_token", value=create_refresh_token(user_id), **_auth_cookie_kwargs(604800))
    user_doc.update({"_id": user_result.inserted_id, "partner_id": partner_id})
    return {"user": await _auth_user_payload(user_doc, access_token), "partner_id": partner_id, "status": "pending"}

@auth_router.post("/login")
async def login(data: UserLogin, request: Request, response: Response):
    email = data.email.lower()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        lockout_until = attempt.get("lockout_until")
        if lockout_until and datetime.fromisoformat(lockout_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"lockout_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}},
            upsert=True
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": identifier})
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email, user["role"])
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="access_token", value=access_token, **_auth_cookie_kwargs(7200))
    response.set_cookie(key="refresh_token", value=refresh_token, **_auth_cookie_kwargs(604800))
    return await _auth_user_payload(user, access_token)

@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}

@auth_router.get("/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return await _auth_user_payload(user)

@auth_router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user_id = str(user["_id"])
        access_token = create_access_token(user_id, user["email"], user["role"])
        response.set_cookie(key="access_token", value=access_token, **_auth_cookie_kwargs(7200))
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@auth_router.post("/forgot-password")
async def forgot_password(data: ForgotPassword):
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    if not user:
        return {"message": "If an account exists, a reset link has been sent"}
    token = secrets.token_urlsafe(32)
    await db.password_reset_tokens.update_many(
        {"user_id": str(user["_id"]), "used": False},
        {"$set": {"used": True}},
    )
    await db.password_reset_tokens.insert_one({
        "user_id": str(user["_id"]), "token": token,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1), "used": False
    })
    reset_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3001')}/reset-password?token={token}"
    logger.info(f"Password reset link for {email}: {reset_link}")
    await send_rendered_email(email, "user_password_reset", {"reset_link": reset_link, "user_name": user.get("name", "")})
    return {"message": "If an account exists, a reset link has been sent"}

@auth_router.post("/reset-password")
async def reset_password(data: ResetPassword):
    token_doc = await db.password_reset_tokens.find_one({"token": data.token, "used": False})
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    expires_at = token_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    await db.users.update_one({"_id": ObjectId(token_doc["user_id"])}, {"$set": {"password_hash": hash_password(data.new_password)}})
    await db.password_reset_tokens.update_one({"token": data.token}, {"$set": {"used": True}})
    return {"message": "Password reset successful"}

@admin_router.post("/impersonate/{user_id}")
async def admin_impersonate_user(user_id: str, request: Request):
    admin_user = await require_role("admin")(request)
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target = await ensure_user_role_group(target)
    tid = str(target["_id"])
    access_token = create_access_token(tid, target["email"], target["role"])
    await create_audit_log(admin_user["_id"], admin_user["email"], "impersonate", "user", tid, {"target_email": target["email"]})
    return {"access_token": access_token, "user": await _auth_user_payload(target)}

# ========================
# USER PROFILE ROUTES
# ========================

@api_router.get("/surveys/public")
async def list_public_surveys():
    surveys = await db.surveys.find({"is_active": True}).sort("name", 1).to_list(100)
    return [_survey_payload(s) for s in surveys]

@api_router.get("/surveys/slug/{slug}")
async def get_public_survey(slug: str):
    survey = await _get_survey_by_slug(slug)
    return _survey_payload(survey)

@api_router.get("/profile")
async def get_profile(request: Request):
    user = await get_current_user(request)
    return {"profile": user.get("profile", {}), "name": user["name"], "email": user["email"]}

@api_router.put("/profile")
async def update_profile(data: ProfileUpdate, request: Request):
    user = await get_current_user(request)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "name" in update_data:
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"name": update_data.pop("name")}})
    if update_data:
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {f"profile.{k}": v for k, v in update_data.items()}})
    return {"message": "Profile updated"}

@api_router.get("/notifications/preferences")
async def get_notification_preferences(request: Request):
    user = await get_current_user(request)
    return user.get("notification_preferences", {"email_on_step_enter": True, "email_on_step_edit": False, "email_on_step_leave": True})

@api_router.put("/notifications/preferences")
async def update_notification_preferences(data: NotificationPreferences, request: Request):
    user = await get_current_user(request)
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"notification_preferences": data.model_dump()}})
    return {"message": "Notification preferences updated"}

# ========================
# STEPS ROUTES
# ========================

@steps_router.get("")
async def get_steps(request: Request, survey_slug: Optional[str] = Query(None)):
    user = await get_current_user(request)
    survey = await _get_user_survey(user, survey_slug)
    query = _step_query_for_survey(str(survey["_id"]))
    steps = await db.steps.find(query).sort("order", 1).to_list(100)
    return [{**{key: value for key, value in step.items() if key != "_id"}, "id": str(step["_id"])} for step in steps]

@steps_router.get("/progress")
async def get_user_progress(request: Request, survey_slug: Optional[str] = Query(None)):
    user = await get_current_user(request)
    survey = await _get_user_survey(user, survey_slug)
    return await db.user_progress.find({"user_id": user["_id"], "survey_id": str(survey["_id"])}, {"_id": 0}).to_list(100)

@steps_router.get("/all-data")
async def get_all_step_data(request: Request, survey_slug: Optional[str] = Query(None)):
    user = await get_current_user(request)
    survey = await _get_user_survey(user, survey_slug)
    steps = await db.steps.find(_step_query_for_survey(str(survey["_id"]))).sort("order", 1).to_list(100)
    progress = await db.user_progress.find({"user_id": user["_id"], "survey_id": str(survey["_id"])}, {"_id": 0}).to_list(100)
    progress_map = {p["step_id"]: p for p in progress}
    return [{
        "step_id": str(s["_id"]), "order": s["order"], "title": s["title"],
        "step_type": s["step_type"], "status": progress_map.get(str(s["_id"]), {}).get("status", "pending"),
        "data": progress_map.get(str(s["_id"]), {}).get("data", {}),
        "conditions": s.get("conditions", []), "field_mappings": s.get("field_mappings", []),
        "required_fields": s.get("required_fields", []), "required_uploads": s.get("required_uploads", [])
    } for s in steps]


def _document_workflow_state(steps: list[dict], progress: list[dict]) -> dict[str, dict]:
    """Resolve shared documents and immutable branch steps for decision blocks."""
    ordered = sorted(steps, key=lambda item: item.get("order", 0))
    progress_by_step = {row.get("step_id"): row for row in progress}
    order_map = {
        step.get("order"): {
            "data": (progress_by_step.get(str(step.get("_id") or step.get("id"))) or {}).get("data") or {},
            "status": (progress_by_step.get(str(step.get("_id") or step.get("id"))) or {}).get("status", "pending"),
        }
        for step in ordered
    }
    state: dict[str, dict] = {}
    decision = None
    branch_steps: list[dict] = []
    for step in ordered:
        if step.get("step_type") == "decision":
            decision, branch_steps = step, []
            continue
        if decision is None:
            continue
        if step.get("step_type") != "milestone":
            branch_steps.append(step)
            continue
        has_upload_branch = any(any(
            field.get("field_type") in {"file", "upload", "multiupload"}
            for field in branch.get("fields", [])
        ) for branch in branch_steps)
        has_partner_branch = any(
            branch.get("step_type") in {"partner_selection", "partner_multiselection"}
            for branch in branch_steps
        )
        if has_upload_branch and has_partner_branch:
            documents, seen_ids = [], set()
            for source in [*branch_steps, step]:
                source_id = str(source.get("_id") or source.get("id"))
                data = (progress_by_step.get(source_id) or {}).get("data") or {}
                for key, value in data.items():
                    if not isinstance(value, list):
                        continue
                    for entry in value:
                        if not isinstance(entry, dict) or not entry.get("file_id") or entry["file_id"] in seen_ids:
                            continue
                        seen_ids.add(entry["file_id"])
                        documents.append({
                            "file_id": entry["file_id"],
                            "filename": entry.get("filename") or "Dokument",
                            "document_type": entry.get("document_type") or "Dokument",
                            "uploaded_by": entry.get("uploaded_by") or ("partner" if key == "partner_uploads" else "user"),
                        })
            for locked_step in [decision, *branch_steps]:
                locked = any(
                    condition.get("action") == "read_only" and _evaluate_condition(condition, order_map)
                    for condition in locked_step.get("conditions", [])
                )
                state[str(locked_step.get("_id") or locked_step.get("id"))] = {"read_only": locked}
            state[str(step.get("_id") or step.get("id"))] = {
                "documents": documents,
                "documents_pending": not locked,
                "document_workflow": True,
            }
        decision, branch_steps = None, []
    return state


async def _migrate_document_workflow_titles() -> int:
    """Align titles and expose the workflow's immutable-state relations."""
    settings = await db.site_settings.find_one({"_key": "global"}, {"document_workflow_version": 1}) or {}
    current_version = settings.get("document_workflow_version", 0)
    if current_version >= 2:
        return 0
    changed = 0
    for survey_id in await db.steps.distinct("survey_id"):
        steps = await db.steps.find(_step_query_for_survey(survey_id)).sort("order", 1).to_list(100)
        decision, branches = None, []
        for step in steps:
            if step.get("step_type") == "decision":
                decision, branches = step, []
                continue
            if decision is None:
                continue
            if step.get("step_type") != "milestone":
                branches.append(step)
                continue
            upload_step = next((branch for branch in branches if any(
                field.get("field_type") in {"file", "upload", "multiupload"}
                for field in branch.get("fields", [])
            )), None)
            partner_step = next((branch for branch in branches if branch.get("step_type") in {"partner_selection", "partner_multiselection"}), None)
            if current_version < 1 and upload_step and partner_step and upload_step.get("title", "").startswith("Dokumente ") and step.get("title", "").startswith("Übersicht "):
                await db.steps.update_one({"_id": upload_step["_id"]}, {"$set": {"title": step["title"]}})
                await db.steps.update_one({"_id": step["_id"]}, {"$set": {"title": upload_step["title"]}})
                changed += 2
            if upload_step and partner_step:
                upload_field = next((field for field in upload_step.get("fields", []) if field.get("field_type") in {"file", "upload", "multiupload"}), None)
                lock_conditions = [
                    {"action": "read_only", "source_step_order": upload_step["order"], "field": upload_field["name"], "operator": "has_upload", "value": "", "message": "Nach dem Dokumenten-Upload ist dieser Schritt schreibgeschützt."},
                    {"action": "read_only", "source_step_order": step["order"], "field": "partner_uploads", "operator": "has_upload", "value": "", "message": "Nach dem Dokumenten-Upload ist dieser Schritt schreibgeschützt."},
                ]
                for target in (decision, upload_step, partner_step):
                    conditions = target.get("conditions") or []
                    existing_keys = {(c.get("action"), c.get("source_step_order"), c.get("field"), c.get("operator")) for c in conditions}
                    additions = [c for c in lock_conditions if (c["action"], c["source_step_order"], c["field"], c["operator"]) not in existing_keys]
                    if additions:
                        await db.steps.update_one({"_id": target["_id"]}, {"$set": {"conditions": [*conditions, *additions]}})
                        changed += len(additions)
            decision, branches = None, []
    await db.site_settings.update_one({"_key": "global"}, {"$set": {"document_workflow_version": 2}}, upsert=True)
    return changed


async def _assert_document_workflow_editable(user_id: str, step: dict) -> None:
    survey_id = step.get("survey_id")
    steps = await db.steps.find(_step_query_for_survey(survey_id)).sort("order", 1).to_list(100)
    progress = await db.user_progress.find({"user_id": user_id, "survey_id": survey_id}, {"_id": 0}).to_list(100)
    if _document_workflow_state(steps, progress).get(str(step.get("_id")), {}).get("read_only"):
        raise HTTPException(status_code=409, detail="Dieser Schritt ist nach dem Dokumenten-Upload schreibgeschützt.")


@steps_router.get("/bootstrap")
async def get_dashboard_bootstrap(request: Request, survey_slug: Optional[str] = Query(None)):
    """Single reload payload for the user dashboard."""
    user = await get_current_user(request)
    survey = await _get_user_survey(user, survey_slug)
    survey_id = str(survey["_id"])
    steps_task = db.steps.find(_step_query_for_survey(survey_id)).sort("order", 1).to_list(100)
    progress_task = db.user_progress.find(
        {"user_id": user["_id"], "survey_id": survey_id}, {"_id": 0}
    ).to_list(100)
    history_task = db.progress_history.find(
        {"user_id": user["_id"]}, {"_id": 0}
    ).sort("timestamp", -1).to_list(200)
    settings_task = db.site_settings.find_one({"_key": "global"}, {"_id": 0, "_key": 0})
    steps, progress, history, settings = await asyncio.gather(
        steps_task, progress_task, history_task, settings_task,
    )
    metrics = calculate_metrics_from_loaded_context(steps, progress)
    progress_map = {row["step_id"]: row for row in progress}
    serialized_steps = [
        {**{key: value for key, value in step.items() if key != "_id"}, "id": str(step["_id"])}
        for step in steps
    ]
    workflow_state = _document_workflow_state(steps, progress)
    serialized_steps = [{**step, **workflow_state.get(step["id"], {})} for step in serialized_steps]
    all_data = [{
        "step_id": str(step["_id"]), "order": step["order"], "title": step["title"],
        "step_type": step["step_type"],
        "status": progress_map.get(str(step["_id"]), {}).get("status", "pending"),
        "data": progress_map.get(str(step["_id"]), {}).get("data", {}),
        "conditions": step.get("conditions", []),
        "field_mappings": step.get("field_mappings", []),
        "required_fields": step.get("required_fields", []),
        "required_uploads": step.get("required_uploads", []),
    } for step in steps]
    return {
        "steps": serialized_steps,
        "progress": progress,
        "all_step_data": all_data,
        "notification_preferences": user.get("notification_preferences", {
            "email_on_step_enter": True,
            "email_on_step_edit": False,
            "email_on_step_leave": True,
        }),
        "history": history,
        "estimated_completion": metrics.get("estimated_completion"),
        "settings": settings or {},
    }

@steps_router.put("/progress")
async def update_user_progress(data: UserProgressUpdate, request: Request):
    user = await get_current_user(request)
    step = await db.steps.find_one({"_id": ObjectId(data.step_id)})
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    existing = await db.user_progress.find_one({"user_id": user["_id"], "step_id": data.step_id})
    await _assert_document_workflow_editable(user["_id"], step)

    if data.status == "completed" and not (data.data or {}).get("skipped"):
        required_fields = list(dict.fromkeys([
            *(step.get("required_fields", []) or []),
            *[
                field.get("name") for field in step.get("fields", [])
                if field.get("required")
                and field.get("field_type") not in CONTENT_FIELD_TYPES | {"multiupload"}
                and field.get("name")
            ],
        ]))
        submission_data = data.data or {}
        missing_fields = [rf for rf in required_fields if not submission_data.get(rf) or (isinstance(submission_data.get(rf), str) and not submission_data[rf].strip())]
        if missing_fields:
            field_labels = {f["name"]: f["label"] for f in step.get("fields", [])}
            labels = [field_labels.get(f, f) for f in missing_fields]
            raise HTTPException(status_code=400, detail=f"Pflichtfelder fehlen: {', '.join(labels)}")
        required_uploads = step.get("required_uploads", [])
        if required_uploads:
            uploaded_types = set()
            for field in step.get("fields", []):
                if field.get("field_type") == "multiupload":
                    for entry in submission_data.get(field["name"], []):
                        if isinstance(entry, dict) and entry.get("file_id") and entry.get("document_type"):
                            uploaded_types.add(entry["document_type"])
            missing_uploads = [u for u in required_uploads if u not in uploaded_types]
            if missing_uploads:
                raise HTTPException(status_code=400, detail=f"Erforderliche Dokumente fehlen: {', '.join(missing_uploads)}")
        # Safety net: any multiupload field with required=True must have at least one file entry
        for field in step.get("fields", []):
            if field.get("field_type") == "multiupload" and field.get("required"):
                entries = submission_data.get(field["name"]) or []
                if not (isinstance(entries, list) and any(
                    isinstance(e, dict) and e.get("file_id") for e in entries
                )):
                    label = field.get("label") or field.get("name")
                    raise HTTPException(status_code=400, detail=f"Mindestens ein Dokument für '{label}' ist erforderlich.")

    user_prefs = user.get("notification_preferences", {"email_on_step_enter": True, "email_on_step_edit": False, "email_on_step_leave": True})
    survey_id = step.get("survey_id") or user.get("survey_id") or str((await _get_default_survey())["_id"])
    total_steps = await db.steps.count_documents(_step_query_for_survey(survey_id))
    email_vars = {
        "user_name": user["name"], "user_email": user["email"],
        "step_title": step["title"], "step_order": step["order"],
        "step_description": step.get("description", ""),
        "total_steps": total_steps,
    }
    if existing and step.get("email_on_edit") and data.data and user_prefs.get("email_on_step_edit", False):
        await send_rendered_email(user["email"], "user_step_updated", email_vars,
                                   override_subject=step.get("email_subject_edit") or "",
                                   override_body=step.get("email_body_edit") or "")
    if not existing and step.get("email_on_enter") and user_prefs.get("email_on_step_enter", True):
        await send_rendered_email(user["email"], "user_step_entered", email_vars,
                                   override_subject=step.get("email_subject_enter") or "",
                                   override_body=step.get("email_body_enter") or "")
    if data.status == "completed" and step.get("email_on_leave") and user_prefs.get("email_on_step_leave", True):
        await send_rendered_email(user["email"], "user_step_completed", email_vars,
                                   override_subject=step.get("email_subject_leave") or "",
                                   override_body=step.get("email_body_leave") or "")

    now_iso = datetime.now(timezone.utc).isoformat()
    update_fields = {"status": data.status, "data": data.data or {}, "updated_at": now_iso}
    if (not existing or not existing.get("started_at")) and data.status in ("in_progress", "completed"):
        update_fields["started_at"] = now_iso
    if data.status == "completed":
        update_fields["completed_at"] = now_iso
    update_fields["survey_id"] = survey_id
    await db.user_progress.update_one({"user_id": user["_id"], "step_id": data.step_id}, {"$set": update_fields}, upsert=True)
    await db.progress_history.insert_one({"user_id": user["_id"], "step_id": data.step_id, "step_title": step["title"], "step_order": step["order"], "action": data.status, "timestamp": now_iso})
    # If this was the Stammdaten step (order=1), apply anerkennungsstatus-based block skips
    if step.get("order") == 1 and (data.data or {}).get("anerkennungsstatus"):
        await apply_anerkennungsstatus_skips(user["_id"], data.data["anerkennungsstatus"])
    # Trigger auto-completion for subsequent steps (e.g. milestones after upload decision)
    await apply_auto_completes(user["_id"])
    return {"message": "Progress updated"}

@steps_router.get("/history")
async def get_user_history(request: Request):
    user = await get_current_user(request)
    return await db.progress_history.find({"user_id": user["_id"]}, {"_id": 0}).sort("timestamp", -1).to_list(200)

@steps_router.get("/estimated-completion")
async def get_estimated_completion(request: Request):
    user = await get_current_user(request)
    return {"estimated_completion": await calculate_estimated_completion(user["_id"])}

@steps_router.get("/visibility")
async def get_step_visibility(request: Request):
    """Return hidden/blocked step ids based on conditions evaluated server-side.
    Used to filter steps in user/partner/admin views and to reflect the true step plan."""
    user = await get_current_user(request)
    _, _, hidden_ids, blocked_ids = await _get_step_context(user["_id"])
    return {"hidden_step_ids": list(hidden_ids), "blocked_step_ids": list(blocked_ids)}

# ========================
# PARTNERS ROUTES (Public)
# ========================

async def _validate_partner_selection_step(user: dict, step_id: str | None) -> dict | None:
    if not step_id or not ObjectId.is_valid(step_id):
        return None
    step = await db.steps.find_one({"_id": ObjectId(step_id)})
    if not step or step.get("step_type") not in {"partner_selection", "partner_multiselection"}:
        raise HTTPException(status_code=400, detail="Submission step is not a partner selection step")
    if user.get("survey_id") and step.get("survey_id") != user["survey_id"]:
        raise HTTPException(status_code=400, detail="Submission step belongs to another survey")
    await _assert_document_workflow_editable(user["_id"], step)
    return step


async def _persist_partner_selection_progress(user: dict, step: dict, selection_data: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.user_progress.update_one({"user_id": user["_id"], "step_id": str(step["_id"])}, {"$set": {
        "user_id": user["_id"], "step_id": str(step["_id"]), "survey_id": step.get("survey_id") or user.get("survey_id"),
        "step_order": step.get("order"), "status": "completed", "data": selection_data,
        "started_at": now, "completed_at": now, "updated_at": now,
    }}, upsert=True)


@partner_router.get("")
async def get_partners(tag: str = ""):
    query = {"is_active": True}
    if tag:
        query["tags"] = tag
    partners = await db.partners.find(query).to_list(100)
    return [{"id": str(p["_id"]), "name": p["name"], "description": p["description"], "logo_url": p.get("logo_url"), "website": p.get("website"), "category": p.get("category"), "tags": p.get("tags", [])} for p in partners]

@partner_router.get("/{partner_id}")
async def get_partner(partner_id: str):
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {"id": str(partner["_id"]), "name": partner["name"], "description": partner["description"], "logo_url": partner.get("logo_url"), "website": partner.get("website"), "contact_email": partner.get("contact_email"), "category": partner.get("category"), "tags": partner.get("tags", [])}

@partner_router.post("/submit")
async def submit_to_partner(data: PartnerSubmissionCreate, request: Request):
    user = await get_current_user(request)
    workflow_step_id = (data.data or {}).get("_step_id")
    workflow_step = await _validate_partner_selection_step(user, workflow_step_id)
    partner = await db.partners.find_one({"_id": ObjectId(data.partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    if workflow_step and workflow_step.get("filter_tag") not in (partner.get("tags") or []):
        raise HTTPException(status_code=400, detail="Partner is not offered in this selection step")
    selection_data = {k: v for k, v in (data.data or {}).items() if k != "_step_id"}
    if workflow_step:
        selection_data.update({"selected_partner_id": data.partner_id, "selected_partner_name": partner.get("name", "")})
        await db.partner_submissions.delete_many({"user_id": user["_id"], "step_id": workflow_step_id, "partner_id": {"$ne": data.partner_id}})
    existing = await db.partner_submissions.find_one({"user_id": user["_id"], "partner_id": data.partner_id, **({"step_id": workflow_step_id} if workflow_step else {})})
    if existing:
        await db.partner_submissions.update_one({"_id": existing["_id"]}, {"$set": {"step_id": workflow_step_id, "data": selection_data, "status": "submitted", "updated_at": datetime.now(timezone.utc).isoformat()}})
        if workflow_step:
            await _persist_partner_selection_progress(user, workflow_step, selection_data)
        return {"message": "Submission updated", "submission_id": existing["id"]}
    submission = {"id": str(uuid.uuid4()), "user_id": user["_id"], "user_email": user["email"], "user_name": user["name"], "partner_id": data.partner_id, "step_id": workflow_step_id, "data": selection_data, "status": "submitted", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.partner_submissions.insert_one(submission)
    if workflow_step:
        await _persist_partner_selection_progress(user, workflow_step, selection_data)
    # Fire-and-forget notifications (don't fail the request on mail errors)
    try:
        await notify_partner_of_new_submission(partner, user, data.data)
    except Exception as exc:
        logger.warning(f"notify_partner failed for {data.partner_id}: {exc}")
    try:
        await notify_user_awaiting_partner(user, partner)
    except Exception as exc:
        logger.warning(f"notify_user_awaiting_partner failed for {user.get('email')}: {exc}")
    return {"message": "Submission successful", "submission_id": submission["id"]}

@api_router.post("/partners/submit-multi")
async def submit_to_multiple_partners(data: MultiPartnerSubmission, request: Request):
    user = await get_current_user(request)
    workflow_step_id = (data.data or {}).get("_step_id")
    workflow_step = await _validate_partner_selection_step(user, workflow_step_id)
    if workflow_step and workflow_step.get("step_type") != "partner_multiselection":
        raise HTTPException(status_code=400, detail="Multiple partners require a multi-selection step")
    selected_names = []
    if workflow_step:
        await db.partner_submissions.delete_many({"user_id": user["_id"], "step_id": workflow_step_id, "partner_id": {"$nin": data.partner_ids}})
    results = []
    for pid in data.partner_ids:
        partner = await db.partners.find_one({"_id": ObjectId(pid)})
        if not partner:
            continue
        if workflow_step and workflow_step.get("filter_tag") not in (partner.get("tags") or []):
            continue
        selected_names.append(partner.get("name", ""))
        selection_data = {k: v for k, v in (data.data or {}).items() if k != "_step_id"}
        existing = await db.partner_submissions.find_one({"user_id": user["_id"], "partner_id": pid, **({"step_id": workflow_step_id} if workflow_step else {})})
        if existing:
            await db.partner_submissions.update_one({"_id": existing["_id"]}, {"$set": {"step_id": workflow_step_id, "data": selection_data, "status": "submitted", "updated_at": datetime.now(timezone.utc).isoformat()}})
            results.append(existing["id"])
        else:
            sub = {"id": str(uuid.uuid4()), "user_id": user["_id"], "user_email": user["email"], "user_name": user["name"], "partner_id": pid, "step_id": workflow_step_id, "data": selection_data, "status": "submitted", "created_at": datetime.now(timezone.utc).isoformat()}
            await db.partner_submissions.insert_one(sub)
            results.append(sub["id"])
            try:
                await notify_partner_of_new_submission(partner, user, data.data or {})
            except Exception as exc:
                logger.warning(f"notify_partner (multi) failed for {pid}: {exc}")
            try:
                await notify_user_awaiting_partner(user, partner)
            except Exception as exc:
                logger.warning(f"notify_user_awaiting_partner (multi) failed for {pid}: {exc}")
    if workflow_step:
        await _persist_partner_selection_progress(user, workflow_step, {
            "selected_partner_ids": data.partner_ids, "selected_partner_names": ", ".join(selected_names),
        })
    return {"message": f"Submitted to {len(results)} partners", "submission_ids": results}

# ========================
# FILES ROUTES
# ========================

@files_router.post("/upload")
async def upload_file(file: UploadFile = File(...), request: Request = None):
    user = await get_current_user(request)
    ext = _safe_upload_extension(file.filename)
    content_type = file.content_type or "application/octet-stream"
    if content_type.lower() in BLOCKED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{user['_id']}/{file_id}.{ext}"
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    original_filename = PurePath(file.filename or f"{file_id}.{ext}").name
    result = put_object(path, data, content_type)
    file_doc = {
        "id": file_id,
        "user_id": user["_id"],
        "storage_path": result["path"],
        "original_filename": original_filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.files.insert_one(file_doc)
    return {"id": file_id, "filename": original_filename, "path": result["path"]}

@files_router.get("/{file_id}")
async def get_file(file_id: str, request: Request, auth: str = Query(None)):
    if auth:
        request.scope["headers"] = list(request.scope.get("headers", [])) + [(b"authorization", f"Bearer {auth}".encode())]
    try:
        user = await get_current_user(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Not authenticated")
    file_doc = await db.files.find_one({"id": file_id, "is_deleted": False})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    if not await _can_access_file(user, file_doc):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data, content_type = get_object(file_doc["storage_path"])
    from fastapi.responses import Response as FastAPIResponse
    return FastAPIResponse(content=data, media_type=file_doc.get("content_type", content_type))

# ========================
# ADMIN ROUTES
# ========================

def _permission_group_payload(group: dict, member_count: int = 0) -> dict:
    return {
        "id": str(group["_id"]),
        "key": group.get("key", ""),
        "name": group.get("name", ""),
        "description": group.get("description", ""),
        "role": group.get("role", "user"),
        "permissions": group.get("permissions", []),
        "is_system": group.get("is_system", False),
        "member_count": member_count,
        "created_at": group.get("created_at"),
        "updated_at": group.get("updated_at"),
    }


def _validated_permission_keys(values: list[str], role: str) -> list[str]:
    allowed = set(ALL_PERMISSION_KEYS)
    if role == "admin":
        allowed.add("*")
    unknown = sorted(set(values or []) - allowed)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown permission(s): {', '.join(unknown)}")
    return normalize_permissions(values, allow_wildcard=role == "admin")


async def _validated_group_ids(group_ids: list[str], role: str) -> list[str]:
    valid_ids = []
    for group_id in dict.fromkeys(group_ids or []):
        if not ObjectId.is_valid(group_id):
            raise HTTPException(status_code=400, detail="Invalid permission group id")
        group = await db.permission_groups.find_one({"_id": ObjectId(group_id)})
        if not group:
            raise HTTPException(status_code=400, detail="Permission group not found")
        if group.get("role") != role:
            raise HTTPException(status_code=400, detail="Permission group does not match the user's portal role")
        valid_ids.append(group_id)
    return valid_ids


@admin_router.get("/permission-catalog")
async def admin_permission_catalog(request: Request):
    await require_role("admin")(request)
    return {"categories": PERMISSION_CATALOG, "all_permissions": list(ALL_PERMISSION_KEYS)}


@admin_router.get("/permission-groups")
async def admin_list_permission_groups(request: Request):
    await require_role("admin")(request)
    groups = await db.permission_groups.find({}).sort([("role", 1), ("name", 1)]).to_list(500)
    result = []
    for group in groups:
        result.append(_permission_group_payload(
            group,
            await db.users.count_documents({"group_ids": str(group["_id"])}),
        ))
    return result


@admin_router.post("/permission-groups")
async def admin_create_permission_group(data: PermissionGroupCreate, request: Request):
    admin_user = await require_role("admin")(request)
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")
    if data.role not in {"user", "partner", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid portal role")
    if await db.permission_groups.find_one({"name_key": name.casefold()}):
        raise HTTPException(status_code=400, detail="A group with this name already exists")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "key": f"custom_{uuid.uuid4().hex}",
        "name": name,
        "name_key": name.casefold(),
        "description": (data.description or "").strip(),
        "role": data.role,
        "permissions": _validated_permission_keys(data.permissions, data.role),
        "is_system": False,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.permission_groups.insert_one(doc)
    await create_audit_log(admin_user["_id"], admin_user["email"], "permission_group_create", "permission_group", str(result.inserted_id), {"name": name, "role": data.role})
    doc["_id"] = result.inserted_id
    return _permission_group_payload(doc)


@admin_router.put("/permission-groups/{group_id}")
async def admin_update_permission_group(group_id: str, data: PermissionGroupUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    if not ObjectId.is_valid(group_id):
        raise HTTPException(status_code=400, detail="Invalid permission group id")
    group = await db.permission_groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Permission group not found")
    update = {}
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Group name is required")
        duplicate = await db.permission_groups.find_one({"name_key": name.casefold(), "_id": {"$ne": group["_id"]}})
        if duplicate:
            raise HTTPException(status_code=400, detail="A group with this name already exists")
        update.update({"name": name, "name_key": name.casefold()})
    role = data.role if data.role is not None else group.get("role", "user")
    if role not in {"user", "partner", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid portal role")
    if data.role is not None and data.role != group.get("role"):
        if group.get("is_system"):
            raise HTTPException(status_code=400, detail="System group role cannot be changed")
        if await db.users.count_documents({"group_ids": group_id}):
            raise HTTPException(status_code=400, detail="Group role cannot be changed while users are assigned")
    if data.role is not None:
        update["role"] = data.role
    if data.description is not None:
        update["description"] = data.description.strip()
    if data.permissions is not None:
        update["permissions"] = _validated_permission_keys(data.permissions, role)
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.permission_groups.update_one({"_id": group["_id"]}, {"$set": update})
    await create_audit_log(admin_user["_id"], admin_user["email"], "permission_group_update", "permission_group", group_id, {"fields": list(update.keys())})
    saved = await db.permission_groups.find_one({"_id": group["_id"]})
    return _permission_group_payload(saved, await db.users.count_documents({"group_ids": group_id}))


@admin_router.delete("/permission-groups/{group_id}")
async def admin_delete_permission_group(group_id: str, request: Request):
    admin_user = await require_role("admin")(request)
    if not ObjectId.is_valid(group_id):
        raise HTTPException(status_code=400, detail="Invalid permission group id")
    group = await db.permission_groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Permission group not found")
    if group.get("is_system"):
        raise HTTPException(status_code=400, detail="System groups cannot be deleted")
    member_count = await db.users.count_documents({"group_ids": group_id})
    if member_count:
        raise HTTPException(status_code=400, detail="Permission group is still assigned to users")
    await db.permission_groups.delete_one({"_id": group["_id"]})
    await create_audit_log(admin_user["_id"], admin_user["email"], "permission_group_delete", "permission_group", group_id, {"name": group.get("name")})
    return {"message": "Permission group deleted"}


@admin_router.get("/users")
async def admin_get_users(request: Request):
    user = await require_role("admin")(request)
    users = await db.users.find({}, {"password_hash": 0}).to_list(1000)
    permission_group_docs = await db.permission_groups.find({}, {"name": 1, "role": 1}).to_list(500)
    permission_group_by_id = {str(group["_id"]): group for group in permission_group_docs}

    # Preload partners into a lookup {id_str: name}
    partner_docs = await db.partners.find({}, {"name": 1, "linked_user_ids": 1, "registration_status": 1, "is_active": 1}).to_list(1000)
    partner_name_by_id = {str(p["_id"]): p.get("name", "") for p in partner_docs}
    partner_name_by_key = {
        p.get("name", "").strip().casefold(): p.get("name", "")
        for p in partner_docs if p.get("name", "").strip()
    }
    # linked_user_id -> list[partner_name]
    partners_by_linked_user: dict[str, list[str]] = {}
    for p in partner_docs:
        pname = p.get("name", "")
        for uid in (p.get("linked_user_ids") or []):
            partners_by_linked_user.setdefault(uid, []).append(pname)

    # Preload partner_selection steps so we know which step_ids carry a partner choice
    partner_step_ids = set()
    async for s in db.steps.find(
        {"step_type": {"$in": ["partner_selection", "partner_multiselection"]}},
        {"_id": 1},
    ):
        partner_step_ids.add(str(s["_id"]))

    partner_progress_by_user: dict[str, list[dict]] = {}
    if partner_step_ids:
        async for row in db.user_progress.find(
            {"step_id": {"$in": list(partner_step_ids)}},
            {"user_id": 1, "data": 1},
        ):
            partner_progress_by_user.setdefault(row.get("user_id"), []).append(row)
    all_submissions = await db.partner_submissions.find(
        {}, {"user_id": 1, "partner_id": 1}
    ).to_list(20000)
    submissions_by_partner: dict[str, list[dict]] = {}
    partner_ids_by_user: dict[str, set[str]] = {}
    for submission in all_submissions:
        pid, uid = submission.get("partner_id"), submission.get("user_id")
        if pid:
            submissions_by_partner.setdefault(pid, []).append(submission)
        if pid and uid:
            partner_ids_by_user.setdefault(uid, set()).add(pid)

    # Precompute "Anmeldungen" count per partner_id: number of users that would
    # appear in the partner's "My Users" tab (partner_work_completed == False).
    # Mirrors the logic of /api/partner/submissions exactly.
    pending_by_partner: dict[str, int] = {}
    for p in partner_docs:
        pid = str(p["_id"])
        pname = p.get("name", "")
        submissions = submissions_by_partner.get(pid, [])
        candidate_ids = {s["user_id"] for s in submissions if s.get("user_id")}
        candidate_ids.update(p.get("linked_user_ids") or [])
        statuses = await _partner_work_status_for_users(list(candidate_ids), pid, pname)
        pending_by_partner[pid] = sum(
            1 for candidate_uid in candidate_ids
            if not statuses.get(candidate_uid, {}).get("completed", False)
        )

    metrics_by_user = await calculate_users_metrics([
        str(row["_id"]) for row in users if row.get("role") == "user"
    ])
    result = []
    for u in users:
        uid = str(u["_id"])
        partner_names: list[str] = []
        orphaned_partner_references: list[dict[str, str]] = []
        # 1) Partner-role users: resolve their own partner_id → org name
        if u.get("role") == "partner" and u.get("partner_id"):
            pname = partner_name_by_id.get(u["partner_id"])
            if pname:
                partner_names.append(pname)
            else:
                orphaned_partner_references.append({"type": "partner_id", "value": str(u["partner_id"])})
        # 2) Any user: partners that explicitly linked this user
        for pname in partners_by_linked_user.get(uid, []):
            if pname and pname not in partner_names:
                partner_names.append(pname)
        # 3) role=user: partners chosen via partner_selection progress data
        if u.get("role") == "user" and partner_step_ids:
            for pr in partner_progress_by_user.get(uid, []):
                data = pr.get("data") or {}
                selected_pid = data.get("selected_partner_id")
                selected_pids = data.get("selected_partner_ids") or []
                if selected_pid:
                    if partner_name_by_id.get(selected_pid):
                        name = partner_name_by_id[selected_pid]
                        if name not in partner_names:
                            partner_names.append(name)
                    else:
                        orphaned_partner_references.append({"type": "partner_id", "value": str(selected_pid)})
                for selected_multi_pid in selected_pids:
                    if partner_name_by_id.get(selected_multi_pid):
                        name = partner_name_by_id[selected_multi_pid]
                        if name not in partner_names:
                            partner_names.append(name)
                    else:
                        orphaned_partner_references.append({"type": "partner_id", "value": str(selected_multi_pid)})
                # Legacy/demo rows sometimes stored only a name. Resolve it
                # only when a current partner matches; never present arbitrary
                # historic text as a real partner assignment.
                pname = data.get("selected_partner_name")
                if pname and not selected_pid and not selected_pids:
                    canonical_name = partner_name_by_key.get(str(pname).strip().casefold())
                    if canonical_name:
                        if canonical_name not in partner_names:
                            partner_names.append(canonical_name)
                    else:
                        orphaned_partner_references.append({"type": "legacy_name", "value": str(pname)})

        # "Anmeldungen" count:
        #  - partner role: pending count for their own partner org
        #  - user role: sum of pending counts across all partners the user is linked with
        #               (their partner-submissions that are still open)
        #  - admin: None
        pending_registrations = None
        if u.get("role") == "partner" and u.get("partner_id"):
            pending_registrations = pending_by_partner.get(u["partner_id"], 0)
        elif u.get("role") == "user":
            # Collect all partner IDs this user submitted to via partner_submissions
            user_partner_ids = partner_ids_by_user.get(uid, set())
            if user_partner_ids:
                pending_registrations = sum(
                    pending_by_partner.get(pid, 0) for pid in user_partner_ids
                )

        metrics = metrics_by_user.get(uid, {
            "completion_pct": 0, "estimated_completion": None,
        })
        result.append({
            "id": uid, "email": u["email"], "name": u["name"], "role": u["role"],
            "created_at": u.get("created_at"),
            "survey_id": u.get("survey_id"),
            "survey_slug": u.get("survey_slug"),
            "completion_pct": metrics["completion_pct"],
            "estimated_completion": metrics["estimated_completion"],
            "partner_names": partner_names,
            "orphaned_partner_references": list({
                (item["type"], item["value"]): item for item in orphaned_partner_references
            }.values()),
            "pending_registrations": pending_registrations,
            "group_ids": u.get("group_ids", []),
            "permission_groups": [
                {"id": group_id, "name": permission_group_by_id[group_id].get("name", ""), "role": permission_group_by_id[group_id].get("role", "user")}
                for group_id in u.get("group_ids", []) if group_id in permission_group_by_id
            ],
            "permission_overrides": u.get("permission_overrides", {"allow": [], "deny": []}),
            "partner_registration_status": next((p.get("registration_status", "active") for p in partner_docs if str(p["_id"]) == u.get("partner_id")), None),
            "partner_is_active": next((p.get("is_active", True) for p in partner_docs if str(p["_id"]) == u.get("partner_id")), None),
        })
    return result

@admin_router.get("/users/search")
async def admin_search_users(request: Request, q: str = "", role: str = ""):
    await require_role("admin")(request)
    query = {}
    if q:
        query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]
    if role and role != "all":
        query["role"] = role
    users = await db.users.find(query, {"password_hash": 0}).to_list(1000)
    return [{"id": str(u["_id"]), "email": u["email"], "name": u["name"], "role": u["role"], "created_at": u.get("created_at"), "partner_id": u.get("partner_id"), "group_ids": u.get("group_ids", [])} for u in users]

@admin_router.post("/users")
async def admin_create_user(data: AdminUserCreate, request: Request):
    admin_user = await require_role("admin")(request)
    if data.role not in {"user", "partner", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    partner = None
    if data.partner_id:
        if data.role != "partner":
            raise HTTPException(status_code=400, detail="Only partner users can be assigned to a partner")
        if not ObjectId.is_valid(data.partner_id):
            raise HTTPException(status_code=400, detail="Invalid partner id")
        partner = await db.partners.find_one({"_id": ObjectId(data.partner_id)})
        if not partner:
            raise HTTPException(status_code=400, detail="Unknown partner id")
    if (data.role == "admin" or data.group_ids) and not await has_permission(admin_user, "users.permissions.manage"):
        raise HTTPException(status_code=403, detail="Missing permission: users.permissions.manage")
    email = data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    survey = None
    if data.role == "user":
        if data.survey_id:
            try:
                survey = await db.surveys.find_one({"_id": ObjectId(data.survey_id), "is_active": True})
            except Exception:
                survey = None
            if not survey:
                raise HTTPException(status_code=400, detail="Invalid or inactive survey")
        else:
            survey = await _get_default_survey()

    now = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "email": email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": data.role,
        "profile": {},
        "created_at": now,
        "permission_overrides": {"allow": [], "deny": []},
    }
    if data.group_ids:
        user_doc["group_ids"] = await _validated_group_ids(data.group_ids, data.role)
    else:
        initial_group_id = await default_group_id(data.role)
        user_doc["group_ids"] = [initial_group_id] if initial_group_id else []
    if survey:
        user_doc["survey_id"] = str(survey["_id"])
        user_doc["survey_slug"] = survey.get("slug", DEFAULT_SURVEY_SLUG)
    if data.partner_id:
        user_doc["partner_id"] = data.partner_id
    result = await db.users.insert_one(user_doc)
    uid = str(result.inserted_id)
    if survey:
        steps = await db.steps.find(_step_query_for_survey(str(survey["_id"]))).sort("order", 1).to_list(100)
        if steps:
            await db.user_progress.insert_many([{
                "user_id": uid,
                "step_id": str(step["_id"]),
                "survey_id": str(survey["_id"]),
                "step_order": step.get("order"),
                "status": "pending",
                "data": {},
                "created_at": now,
                "updated_at": now,
            } for step in steps])
    if partner:
        await db.partners.update_one({"_id": partner["_id"]}, {"$set": {"user_id": uid}})
    await create_audit_log(admin_user["_id"], admin_user["email"], "user_create", "user", uid, {
        "email": email, "role": data.role, "survey_id": str(survey["_id"]) if survey else None,
    })
    return {
        "id": uid,
        "survey_id": str(survey["_id"]) if survey else None,
        "survey_slug": survey.get("slug") if survey else None,
        "message": "User created",
    }

@admin_router.get("/users/{user_id}")
async def admin_get_user(user_id: str, request: Request):
    await require_role("admin")(request)
    user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    submissions = await db.partner_submissions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    history = await db.progress_history.find({"user_id": user_id}, {"_id": 0}).sort("timestamp", -1).to_list(200)
    return {"id": str(user["_id"]), "email": user["email"], "name": user["name"], "role": user["role"], "profile": user.get("profile", {}), "survey_id": user.get("survey_id"), "survey_slug": user.get("survey_slug"), "created_at": user.get("created_at"), "progress": progress, "submissions": submissions, "history": history, "completion_pct": await calculate_completion_pct(user_id), "group_ids": user.get("group_ids", []), "permission_groups": await permission_group_summaries(user), "permission_overrides": user.get("permission_overrides", {"allow": [], "deny": []}), "effective_permissions": await effective_permissions(user), "is_primary_admin": user.get("email") == os.environ.get("ADMIN_EMAIL", "admin@example.com")}


@admin_router.put("/users/{user_id}/permissions")
async def admin_update_user_permissions(user_id: str, data: UserPermissionsUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user id")
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("email") == os.environ.get("ADMIN_EMAIL", "admin@example.com"):
        raise HTTPException(status_code=400, detail="Primary admin permissions cannot be overridden")
    group_ids = await _validated_group_ids(data.group_ids, target.get("role", "user"))
    allow = _validated_permission_keys(data.allow, "user")
    deny = _validated_permission_keys(data.deny, "user")
    if set(allow) & set(deny):
        raise HTTPException(status_code=400, detail="A permission cannot be both allowed and denied")
    overrides = {"allow": allow, "deny": deny}
    await db.users.update_one(
        {"_id": target["_id"]},
        {"$set": {"group_ids": group_ids, "permission_overrides": overrides, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    saved = await db.users.find_one({"_id": target["_id"]})
    await create_audit_log(admin_user["_id"], admin_user["email"], "user_permissions_update", "user", user_id, {"group_ids": group_ids, **overrides})
    return {"message": "User permissions updated", "group_ids": group_ids, "permission_overrides": overrides, "effective_permissions": await effective_permissions(saved)}

@admin_router.put("/users/{user_id}/progress")
async def admin_update_user_progress(user_id: str, data: UserProgressUpdate, request: Request):
    await require_role("admin")(request)
    step = await db.steps.find_one({"_id": ObjectId(data.step_id)})
    await db.user_progress.update_one({"user_id": user_id, "step_id": data.step_id}, {"$set": {"status": data.status, "data": data.data or {}, "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    if step and step.get("order") == 1 and (data.data or {}).get("anerkennungsstatus"):
        await apply_anerkennungsstatus_skips(user_id, data.data["anerkennungsstatus"])
    await apply_auto_completes(user_id)
    return {"message": "User progress updated"}

@admin_router.put("/users/bulk-role")
async def admin_bulk_update_role(data: BulkRoleUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    if data.role not in ["user", "admin", "partner"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    if data.role == "admin" and not await has_permission(admin_user, "users.permissions.manage"):
        raise HTTPException(status_code=403, detail="Missing permission: users.permissions.manage")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    role_group_id = await default_group_id(data.role)
    updated = 0
    for uid in data.user_ids:
        try:
            target = await db.users.find_one({"_id": ObjectId(uid)})
            if target and target["email"] == admin_email and data.role != "admin":
                continue
            result = await db.users.update_one({"_id": ObjectId(uid)}, {"$set": {"role": data.role, "group_ids": [role_group_id] if role_group_id else [], "permission_overrides": {"allow": [], "deny": []}}})
            if result.modified_count:
                updated += 1
        except Exception:
            continue
    return {"message": f"{updated} users updated to {data.role}"}

@admin_router.get("/export/users")
async def admin_export_users_csv(request: Request):
    await require_role("admin")(request)
    users = await db.users.find({}, {"password_hash": 0}).to_list(10000)
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Role", "Created At"] + [s["title"] for s in steps])
    for u in users:
        progress = await db.user_progress.find({"user_id": str(u["_id"])}, {"_id": 0}).to_list(100)
        progress_map = {p["step_id"]: p["status"] for p in progress}
        writer.writerow([u.get("name", ""), u.get("email", ""), u.get("role", ""), u.get("created_at", "")] + [progress_map.get(str(s["_id"]), "not_started") for s in steps])
    from fastapi.responses import Response as RawResponse
    return RawResponse(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=users_export.csv"})

@admin_router.put("/users/{user_id}/role")
async def admin_update_user_role(user_id: str, role: str, request: Request):
    admin_user = await require_role("admin")(request)
    if role not in ["user", "admin", "partner"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    if role == "admin" and not await has_permission(admin_user, "users.permissions.manage"):
        raise HTTPException(status_code=403, detail="Missing permission: users.permissions.manage")
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if target and target["email"] == os.environ.get("ADMIN_EMAIL", "admin@example.com") and role != "admin":
        raise HTTPException(status_code=400, detail="Cannot change the primary admin's role")
    role_group_id = await default_group_id(role)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": role, "group_ids": [role_group_id] if role_group_id else [], "permission_overrides": {"allow": [], "deny": []}}})
    await create_audit_log(admin_user["_id"], admin_user["email"], "role_change", "user", user_id, {"new_role": role})
    return {"message": "User role updated"}

@admin_router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, request: Request):
    admin_user = await require_role("admin")(request)
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["email"] == os.environ.get("ADMIN_EMAIL", "admin@example.com"):
        raise HTTPException(status_code=400, detail="Cannot delete the primary admin account")
    await db.user_progress.delete_many({"user_id": user_id})
    await db.partner_submissions.delete_many({"user_id": user_id})
    await db.progress_history.delete_many({"user_id": user_id})
    await db.files.delete_many({"user_id": user_id})
    # Unlink from partner (1:1 dashboard access)
    if target.get("partner_id"):
        await db.partners.update_one({"_id": ObjectId(target["partner_id"])}, {"$unset": {"user_id": ""}})
    # Remove from any partner's linked_user_ids (m:n)
    await db.partners.update_many({"linked_user_ids": user_id}, {"$pull": {"linked_user_ids": user_id}})
    await db.users.delete_one({"_id": ObjectId(user_id)})
    await create_audit_log(admin_user["_id"], admin_user["email"], "user_delete", "user", user_id, {"email": target["email"]})
    return {"message": "User deleted"}

# Admin Surveys
@admin_router.get("/surveys")
async def admin_list_surveys(request: Request):
    await require_role("admin")(request)
    surveys = await db.surveys.find().sort("name", 1).to_list(100)
    return [_survey_payload(s) for s in surveys]

@admin_router.post("/surveys")
async def admin_create_survey(data: SurveyCreate, request: Request):
    admin_user = await require_role("admin")(request)
    slug = data.slug.strip().lower().replace(" ", "-")
    if not slug:
        raise HTTPException(status_code=400, detail="Slug is required")
    if await db.surveys.find_one({"slug": slug}):
        raise HTTPException(status_code=400, detail="Survey slug already exists")
    now = datetime.now(timezone.utc).isoformat()
    if data.is_default:
        await db.surveys.update_many({}, {"$set": {"is_default": False}})
    doc = {
        "name": data.name,
        "slug": slug,
        "description": data.description or "",
        "audience": data.audience or "",
        "is_active": data.is_active,
        "is_default": data.is_default,
        "theme": data.theme or {},
        "created_at": now,
        "updated_at": now,
    }
    result = await db.surveys.insert_one(doc)
    await create_audit_log(admin_user["_id"], admin_user["email"], "survey_create", "survey", str(result.inserted_id), {"name": data.name, "slug": slug})
    return {"id": str(result.inserted_id), "message": "Survey created"}

@admin_router.put("/surveys/{survey_id}")
async def admin_update_survey(survey_id: str, data: SurveyUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    existing = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Survey not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "slug" in update_data:
        update_data["slug"] = update_data["slug"].strip().lower().replace(" ", "-")
        duplicate = await db.surveys.find_one({"slug": update_data["slug"], "_id": {"$ne": ObjectId(survey_id)}})
        if duplicate:
            raise HTTPException(status_code=400, detail="Survey slug already exists")
    if update_data.get("is_default"):
        await db.surveys.update_many({"_id": {"$ne": ObjectId(survey_id)}}, {"$set": {"is_default": False}})
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.surveys.update_one({"_id": ObjectId(survey_id)}, {"$set": update_data})
    await create_audit_log(admin_user["_id"], admin_user["email"], "survey_update", "survey", survey_id, {"fields_changed": list(update_data.keys())})
    return {"message": "Survey updated"}

# Admin Steps
@admin_router.get("/steps", response_model=List[StepResponse])
async def admin_get_steps(request: Request, survey_id: Optional[str] = Query(None), survey_slug: Optional[str] = Query(None)):
    await require_role("admin")(request)
    query = {}
    if survey_slug:
        survey = await _get_survey_by_slug(survey_slug)
        query["survey_id"] = str(survey["_id"])
    elif survey_id:
        query["survey_id"] = survey_id
    steps = await db.steps.find(query).sort("order", 1).to_list(100)
    return [_admin_step_payload(step) for step in steps]

@admin_router.post("/steps")
async def admin_create_step(data: StepCreate, request: Request):
    await require_role("admin")(request)
    survey_id = data.survey_id or str((await _get_default_survey())["_id"])
    fields = [
        normalize_step_field(field.model_dump(exclude_none=True), index)
        for index, field in enumerate(data.fields or [])
    ]
    inferred_required = [
        field["name"] for field in fields
        if field.get("required") and field.get("field_type") not in CONTENT_FIELD_TYPES | {"multiupload"}
    ]
    required_fields = list(dict.fromkeys([*(data.required_fields or []), *inferred_required]))
    step_doc = {"survey_id": survey_id, "title": data.title, "description": data.description, "order": data.order, "step_type": data.step_type, "fields": fields, "form_schema_version": FORM_SCHEMA_VERSION, "filter_tag": data.filter_tag or "", "skippable": data.skippable, "skip_label": data.skip_label or "", "action_label": data.action_label or "", "pending_message": data.pending_message or "", "complete_message": data.complete_message or "", "required_fields": required_fields, "required_uploads": data.required_uploads or [], "field_mappings": [mapping.model_dump(exclude_none=True) for mapping in data.field_mappings or []], "conditions": [condition.model_dump(exclude_none=True) for condition in data.conditions or []], "email_on_enter": data.email_on_enter, "email_on_edit": data.email_on_edit, "email_on_leave": data.email_on_leave, "email_subject_enter": data.email_subject_enter or "", "email_body_enter": data.email_body_enter or "", "email_subject_edit": data.email_subject_edit or "", "email_body_edit": data.email_body_edit or "", "email_subject_leave": data.email_subject_leave or "", "email_body_leave": data.email_body_leave or "", "duration_value": data.duration_value, "duration_unit": data.duration_unit, "translations": data.translations or {}, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
    step_doc["partner_user_fee_cents"] = data.partner_user_fee_cents
    result = await db.steps.insert_one(step_doc)
    admin_user = await get_current_user(request)
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_create", "step", str(result.inserted_id), {"title": data.title})
    return {"id": str(result.inserted_id), "message": "Step created"}

@admin_router.put("/steps/reorder")
async def admin_reorder_steps(data: StepReorder, request: Request):
    admin_user = await require_role("admin")(request)
    for idx, step_id in enumerate(data.step_ids):
        query = {"_id": ObjectId(step_id)}
        if data.survey_id:
            query["survey_id"] = data.survey_id
        await db.steps.update_one(query, {"$set": {"order": idx + 1}})
    await create_audit_log(admin_user["_id"], admin_user["email"], "steps_reorder", "step", "", {"new_order": data.step_ids})
    return {"message": "Steps reordered"}

@admin_router.put("/steps/layout-bulk")
async def admin_save_step_layout_bulk(data: StepLayoutBulk, request: Request):
    """Persist flow_position for many steps at once."""
    admin_user = await require_role("admin")(request)
    updated = 0
    for sid, pos in data.positions.items():
        try:
            await db.steps.update_one(
                {"_id": ObjectId(sid)},
                {"$set": {"flow_position": {"x": pos.x, "y": pos.y},
                           "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            updated += 1
        except Exception:
            pass
    await create_audit_log(admin_user["_id"], admin_user["email"], "steps_layout_saved",
                            "step", "", {"count": updated})
    return {"message": "Layout saved", "updated": updated}

@admin_router.put("/steps/{step_id}")
async def admin_update_step(step_id: str, data: StepUpdate, request: Request):
    await require_role("admin")(request)
    clear_partner_price = "partner_user_fee_cents" in data.model_fields_set and data.partner_user_fee_cents is None
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "fields" in update_data:
        update_data["fields"] = [
            normalize_step_field(field if isinstance(field, dict) else field.model_dump(exclude_none=True), index)
            for index, field in enumerate(update_data["fields"] or [])
        ]
        update_data["form_schema_version"] = FORM_SCHEMA_VERSION
        inferred_required = [
            field["name"] for field in update_data["fields"]
            if field.get("required") and field.get("field_type") not in CONTENT_FIELD_TYPES | {"multiupload"}
        ]
        if "required_fields" in update_data:
            update_data["required_fields"] = list(dict.fromkeys([
                *(update_data.get("required_fields") or []), *inferred_required,
            ]))
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_operation = {"$set": update_data}
    if clear_partner_price:
        update_operation["$unset"] = {"partner_user_fee_cents": ""}
    await db.steps.update_one({"_id": ObjectId(step_id)}, update_operation)
    admin_user = await get_current_user(request)
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_update", "step", step_id, {"fields_changed": list(update_data.keys())})
    return {"message": "Step updated"}

@admin_router.delete("/steps/{step_id}")
async def admin_delete_step(step_id: str, request: Request):
    admin_user = await require_role("admin")(request)
    step = await db.steps.find_one({"_id": ObjectId(step_id)})
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    # Cascade: remove all progress records for this step
    await db.user_progress.delete_many({"step_id": step_id})
    await db.progress_history.delete_many({"step_id": step_id})
    await db.steps.delete_one({"_id": ObjectId(step_id)})
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_delete", "step", step_id, {"title": step["title"]})
    return {"message": "Step deleted"}

# Admin Partners
@admin_router.get("/partners")
async def admin_get_partners(request: Request):
    await require_role("admin")(request)
    partners = await db.partners.find().to_list(1000)
    partners.sort(key=lambda partner: (partner.get("name") or "").casefold())
    all_users = await db.users.find(
        {}, {"password_hash": 0}
    ).to_list(2000)
    user_by_id = {str(row["_id"]): row for row in all_users}
    dashboard_user_by_partner = {
        row.get("partner_id"): row for row in all_users
        if row.get("role") == "partner" and row.get("partner_id")
    }
    all_submissions = await db.partner_submissions.find(
        {}, {"partner_id": 1, "user_id": 1}
    ).to_list(20000)
    submissions_by_partner: dict[str, list[dict]] = {}
    for submission in all_submissions:
        submissions_by_partner.setdefault(submission.get("partner_id"), []).append(submission)

    # Precompute pending_registrations per partner org (matches /partner/submissions logic)
    pending_by_partner: dict[str, int] = {}
    for p in partners:
        pid = str(p["_id"])
        pname = p.get("name", "")
        submissions = submissions_by_partner.get(pid, [])
        candidate_ids = {s["user_id"] for s in submissions if s.get("user_id")}
        candidate_ids.update(p.get("linked_user_ids") or [])
        statuses = await _partner_work_status_for_users(list(candidate_ids), pid, pname)
        pending_by_partner[pid] = sum(
            1 for candidate_uid in candidate_ids
            if not statuses.get(candidate_uid, {}).get("completed", False)
        )

    service_steps = await db.steps.find({
        "step_type": {"$in": ["partner_selection", "partner_multiselection"]}, "is_active": True,
    }, {"title": 1, "order": 1, "survey_id": 1, "filter_tag": 1, "partner_user_fee_cents": 1}).sort("order", 1).to_list(1000)
    result = []
    for p in partners:
        pid = str(p["_id"])
        dashboard_user = dashboard_user_by_partner.get(pid)
        linked_ids = p.get("linked_user_ids", [])
        linked_users = []
        for uid in linked_ids:
            u = user_by_id.get(uid)
            if u:
                linked_users.append({"id": uid, "name": u["name"], "email": u["email"]})
        if dashboard_user:
            du_id = str(dashboard_user["_id"])
            if du_id not in linked_ids:
                linked_users.insert(0, {"id": du_id, "name": dashboard_user["name"], "email": dashboard_user["email"]})
        result.append({
            "id": pid, "name": p["name"], "description": p.get("description", ""),
            "logo_url": p.get("logo_url"), "website": p.get("website"),
            "contact_email": p.get("contact_email"), "category": p.get("category"),
            "tags": p.get("tags", []), "is_active": p.get("is_active", True),
            "user_id": p.get("user_id"), "linked_users": linked_users,
            "linked_user_ids": linked_ids,
            "pending_registrations": pending_by_partner.get(pid, 0),
            "survey_ids": p.get("survey_ids", []),
            "registration_status": p.get("registration_status", "active" if p.get("is_active", True) else "pending"),
            "registration_source": p.get("registration_source", "admin"),
            "registered_at": p.get("registered_at", p.get("created_at")),
            "stripe_account_id": p.get("stripe_account_id"),
            "stripe_onboarding_complete": p.get("stripe_onboarding_complete", False),
            "stripe_customer_id": p.get("stripe_customer_id", ""),
            "stripe_subscription_id": p.get("stripe_subscription_id", ""),
            "billing_status": p.get("billing_status", ""),
            "step_user_fee_cents": p.get("step_user_fee_cents", {}),
            "service_steps": [{
                "id": str(step["_id"]), "title": step.get("title", ""), "order": step.get("order", 0),
                "survey_id": step.get("survey_id"), "filter_tag": step.get("filter_tag", ""),
                "step_user_fee_cents": step.get("partner_user_fee_cents"),
            } for step in service_steps if (
                step.get("filter_tag") in (p.get("tags") or [])
                and (not p.get("survey_ids") or step.get("survey_id") in p.get("survey_ids", []))
            )],
        })
    return result

@admin_router.post("/partners")
async def admin_create_partner(data: PartnerCreate, request: Request):
    admin_user = await require_role("admin")(request)
    survey_ids = data.survey_ids or []
    partner_doc = {"name": data.name, "description": data.description, "logo_url": data.logo_url, "website": data.website, "contact_email": data.contact_email, "category": data.category, "tags": data.tags or [], "linked_user_ids": data.linked_user_ids or [], "survey_ids": survey_ids, "step_user_fee_cents": data.step_user_fee_cents or {}, "stripe_customer_id": data.stripe_customer_id, "stripe_subscription_id": data.stripe_subscription_id, "billing_status": data.billing_status or "pending", "is_active": bool(survey_ids) if data.survey_ids is not None else True, "registration_status": "active", "registration_source": "admin", "created_at": datetime.now(timezone.utc).isoformat()}
    result = await db.partners.insert_one(partner_doc)
    await create_audit_log(admin_user["_id"], admin_user["email"], "partner_create", "partner", str(result.inserted_id), {"name": data.name})
    return {"id": str(result.inserted_id), "message": "Partner created"}

@admin_router.put("/partners/{partner_id}")
async def admin_update_partner(partner_id: str, data: PartnerUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None and k != 'linked_user_ids'}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if data.linked_user_ids is not None:
        update_data["linked_user_ids"] = data.linked_user_ids
    if data.survey_ids is not None:
        valid_surveys = await db.surveys.count_documents({"_id": {"$in": [_safe_object_id(sid, "Invalid survey id") for sid in data.survey_ids]}})
        if valid_surveys != len(set(data.survey_ids)):
            raise HTTPException(status_code=400, detail="Unknown survey id")
        update_data["survey_ids"] = list(dict.fromkeys(data.survey_ids))
        update_data["is_active"] = bool(update_data["survey_ids"])
        update_data["registration_status"] = "active" if update_data["is_active"] else "pending"
    if data.step_user_fee_cents is not None:
        step_ids = list(data.step_user_fee_cents)
        valid = await db.steps.count_documents({
            "_id": {"$in": [_safe_object_id(sid, "Invalid step id") for sid in step_ids]},
            "step_type": {"$in": ["partner_selection", "partner_multiselection"]},
        }) if step_ids else 0
        if valid != len(step_ids):
            raise HTTPException(status_code=400, detail="Partner prices may only reference partner selection steps")
    if data.billing_status is not None:
        update_data["access_unlocked"] = data.billing_status in {"active", "trialing", "paid"}
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$set": update_data})
    updated_partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if updated_partner and updated_partner.get("stripe_customer_id") and updated_partner.get("stripe_subscription_id"):
        await _sync_pending_partner_usage_charges(updated_partner)
    await create_audit_log(admin_user["_id"], admin_user["email"], "partner_update", "partner", partner_id, {"fields_changed": list(update_data.keys())})
    return {"message": "Partner updated"}

@admin_router.delete("/partners/{partner_id}")
async def admin_delete_partner(partner_id: str, request: Request):
    admin_user = await require_role("admin")(request)
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    # Cascade: unlink partner-role users (set back to "user")
    partner_users = await db.users.find({"partner_id": partner_id}).to_list(100)
    user_group_id = await default_group_id("user")
    for pu in partner_users:
        await db.users.update_one(
            {"_id": pu["_id"]},
            {"$set": {"role": "user", "group_ids": [user_group_id] if user_group_id else [], "permission_overrides": {"allow": [], "deny": []}}, "$unset": {"partner_id": ""}},
        )
    # Cascade: remove all submissions to this partner
    await db.partner_submissions.delete_many({"partner_id": partner_id})
    await db.partners.delete_one({"_id": ObjectId(partner_id)})
    await create_audit_log(admin_user["_id"], admin_user["email"], "partner_delete", "partner", partner_id, {"name": partner["name"]})
    return {"message": "Partner deleted"}

@admin_router.put("/partners/{partner_id}/link-user")
async def admin_link_partner_user(partner_id: str, user_id: str, request: Request):
    await require_role("admin")(request)
    target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    old_user_id = partner.get("user_id")
    if old_user_id:
        user_group_id = await default_group_id("user")
        await db.users.update_one({"_id": ObjectId(old_user_id)}, {"$set": {"role": "user", "group_ids": [user_group_id] if user_group_id else [], "permission_overrides": {"allow": [], "deny": []}}, "$unset": {"partner_id": ""}})
    partner_group_id = await default_group_id("partner")
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$set": {"user_id": user_id}})
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": "partner", "partner_id": partner_id, "group_ids": [partner_group_id] if partner_group_id else [], "permission_overrides": {"allow": [], "deny": []}}})
    return {"message": "Partner linked to user", "user_name": target_user["name"]}

@admin_router.put("/partners/{partner_id}/unlink-user")
async def admin_unlink_partner_user(partner_id: str, request: Request):
    await require_role("admin")(request)
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    old_user_id = partner.get("user_id")
    if old_user_id:
        user_group_id = await default_group_id("user")
        await db.users.update_one({"_id": ObjectId(old_user_id)}, {"$set": {"role": "user", "group_ids": [user_group_id] if user_group_id else [], "permission_overrides": {"allow": [], "deny": []}}, "$unset": {"partner_id": ""}})
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$unset": {"user_id": ""}})
    return {"message": "Partner unlinked from user"}

# Admin Analytics
@admin_router.get("/analytics")
async def admin_get_analytics(request: Request):
    await require_role("admin")(request)
    total_users = await db.users.count_documents({"role": "user"})
    total_partners = await db.partners.count_documents({"is_active": True})
    total_submissions = await db.partner_submissions.count_documents({})
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    step_analytics = []
    for step in steps:
        sid = str(step["_id"])
        total = await db.user_progress.count_documents({"step_id": sid})
        completed = await db.user_progress.count_documents({"step_id": sid, "status": "completed"})
        in_progress = await db.user_progress.count_documents({"step_id": sid, "status": "in_progress"})
        step_analytics.append({"step_id": sid, "title": step["title"], "order": step["order"], "total": total, "completed": completed, "in_progress": in_progress, "completion_rate": round((completed / total * 100) if total > 0 else 0, 1)})
    return {"total_users": total_users, "total_partners": total_partners, "total_submissions": total_submissions, "admin_count": await db.users.count_documents({"role": "admin"}), "partner_count": await db.users.count_documents({"role": "partner"}), "recent_registrations": await db.users.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}}), "step_analytics": step_analytics}


@admin_router.get("/billing")
async def admin_billing_summary(request: Request):
    await require_role("admin")(request)
    partners = await db.partners.find({}, {"name": 1, "stripe_customer_id": 1, "billing_status": 1}).sort("name", 1).to_list(1000)
    result = []
    for partner in partners:
        partner_id = str(partner["_id"])
        invoices = []
        if partner.get("stripe_customer_id"):
            try:
                payload = await list_customer_invoices(partner["stripe_customer_id"])
                invoices = [_invoice_view(invoice) for invoice in payload.get("data", [])]
            except HTTPException:
                invoices = []
        result.append({
            "partner_id": partner_id, "partner_name": partner.get("name", ""),
            "billing_status": partner.get("billing_status", "pending"),
            "usage": await _usage_billing_stats(partner_id), "invoices": invoices,
        })
    return {"partners": result, "totals": {
        "pending_users": sum(item["usage"]["pending_users"] for item in result),
        "pending_amount": sum(item["usage"]["pending_amount"] for item in result),
        "billed_users": sum(item["usage"]["billed_users"] for item in result),
        "billed_amount": sum(item["usage"]["billed_amount"] for item in result),
    }}


async def _stripe_connection_report(partner: dict) -> dict:
    partner_id = str(partner["_id"])
    user = await db.users.find_one({"$or": [{"partner_id": partner_id}, {"_id": ObjectId(partner["user_id"])}]}) if partner.get("user_id") and ObjectId.is_valid(partner["user_id"]) else await db.users.find_one({"partner_id": partner_id})
    emails = list(dict.fromkeys(email.strip().lower() for email in [partner.get("contact_email"), (user or {}).get("email")] if email and email.strip()))
    current_customer = partner.get("stripe_customer_id") or ""
    current_subscription = partner.get("stripe_subscription_id") or ""
    issues, customer, customer_candidates = [], None, []
    if current_customer:
        try:
            candidate = await retrieve_customer(current_customer)
            if not candidate.get("deleted"):
                customer = candidate
            else:
                issues.append("Der gespeicherte Stripe-Kunde wurde gelöscht.")
        except HTTPException:
            issues.append("Die gespeicherte Stripe-Customer-ID ist ungültig oder nicht erreichbar.")
    else:
        issues.append("Stripe-Customer-ID fehlt.")
    if not customer:
        by_id = {}
        for email in emails:
            try:
                for candidate in (await find_customers_by_email(email)).get("data", []):
                    if not candidate.get("deleted"):
                        by_id[candidate["id"]] = candidate
            except HTTPException:
                pass
        customer_candidates = list(by_id.values())
        if len(customer_candidates) == 1:
            customer = customer_candidates[0]
        elif len(customer_candidates) > 1:
            issues.append(f"Mehrdeutige Zuordnung: {len(customer_candidates)} Stripe-Kunden passen zur E-Mail-Adresse.")
        else:
            issues.append("Kein Stripe-Kunde zur Partner-E-Mail gefunden.")

    subscription, subscription_candidates = None, []
    if current_subscription:
        try:
            candidate = await retrieve_subscription(current_subscription)
            if customer and candidate.get("customer") != customer.get("id"):
                issues.append("Die gespeicherte Subscription gehört zu einem anderen Stripe-Kunden.")
            else:
                subscription = candidate
        except HTTPException:
            issues.append("Die gespeicherte Stripe-Subscription-ID ist ungültig oder nicht erreichbar.")
    else:
        issues.append("Stripe-Subscription-ID fehlt.")
    if customer and not subscription:
        try:
            subscriptions = (await list_customer_subscriptions(customer["id"])).get("data", [])
            usable = [item for item in subscriptions if item.get("status") in {"active", "trialing", "past_due", "unpaid", "incomplete"}]
            subscription_candidates = usable or [item for item in subscriptions if item.get("status") != "canceled"]
            if len(subscription_candidates) == 1:
                subscription = subscription_candidates[0]
            elif len(subscription_candidates) > 1:
                issues.append(f"Mehrdeutige Zuordnung: {len(subscription_candidates)} Stripe-Abonnements sind verwendbar.")
            else:
                issues.append("Kein verwendbares Stripe-Abonnement gefunden.")
        except HTTPException:
            issues.append("Stripe-Abonnements konnten nicht geprüft werden.")

    proposed_status = (subscription or {}).get("status") or partner.get("billing_status") or "pending"
    status_ok = partner.get("billing_status") in ({"paid", "active"} if proposed_status == "active" else {proposed_status})
    if subscription and not status_ok:
        issues.append(f"Lokaler Zahlungsstatus passt nicht zum Stripe-Status „{proposed_status}“.")
    proposed_customer = (customer or {}).get("id", "")
    proposed_subscription = (subscription or {}).get("id", "")
    needs_repair = bool(issues) or current_customer != proposed_customer or current_subscription != proposed_subscription
    repairable = bool(needs_repair and proposed_customer and proposed_subscription and len(customer_candidates) <= 1 and len(subscription_candidates) <= 1)
    return {
        "partner_id": partner_id, "partner_name": partner.get("name", ""), "emails": emails,
        "current_customer_id": current_customer, "current_subscription_id": current_subscription,
        "current_billing_status": partner.get("billing_status", ""), "issues": list(dict.fromkeys(issues)),
        "proposed_customer_id": proposed_customer, "proposed_subscription_id": proposed_subscription,
        "proposed_billing_status": proposed_status, "repairable": repairable,
    }


async def _repair_stripe_connection(partner: dict, report: dict) -> bool:
    if not report.get("repairable"):
        return False
    status = report["proposed_billing_status"]
    await db.partners.update_one({"_id": partner["_id"]}, {"$set": {
        "stripe_customer_id": report["proposed_customer_id"],
        "stripe_subscription_id": report["proposed_subscription_id"],
        "billing_status": status,
        "access_unlocked": status in {"active", "trialing", "paid"},
        "stripe_connection_repaired_at": datetime.now(timezone.utc).isoformat(),
    }})
    updated = {**partner, "stripe_customer_id": report["proposed_customer_id"], "stripe_subscription_id": report["proposed_subscription_id"]}
    await _sync_pending_partner_usage_charges(updated)
    return True


@admin_router.get("/billing/connection-audit")
async def admin_stripe_connection_audit(request: Request):
    await require_role("admin")(request)
    partners = await db.partners.find({"registration_source": "self_service"}).sort("name", 1).to_list(1000)
    reports = []
    for partner in partners:
        report = await _stripe_connection_report(partner)
        if report["issues"] or report["repairable"]:
            reports.append(report)
    return {"entries": reports, "defective": len(reports), "repairable": sum(1 for item in reports if item["repairable"])}


@admin_router.post("/billing/connection-repairs/all")
async def admin_repair_all_stripe_connections(request: Request):
    admin_user = await require_role("admin")(request)
    partners = await db.partners.find({"registration_source": "self_service"}).sort("name", 1).to_list(1000)
    repaired, skipped = [], []
    for partner in partners:
        report = await _stripe_connection_report(partner)
        if await _repair_stripe_connection(partner, report):
            repaired.append(str(partner["_id"]))
        elif report["issues"]:
            skipped.append(str(partner["_id"]))
    await create_audit_log(admin_user["_id"], admin_user["email"], "stripe_connections_repair_all", "partner", "", {"repaired": repaired, "skipped": skipped})
    return {"repaired": len(repaired), "skipped": len(skipped), "repaired_partner_ids": repaired}


@admin_router.post("/billing/connection-repairs/{partner_id}")
async def admin_repair_stripe_connection(partner_id: str, request: Request):
    admin_user = await require_role("admin")(request)
    partner = await db.partners.find_one({"_id": _safe_object_id(partner_id, "Invalid partner id")})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    report = await _stripe_connection_report(partner)
    if not await _repair_stripe_connection(partner, report):
        raise HTTPException(status_code=409, detail="Die Stripe-Verbindung ist nicht eindeutig automatisch reparierbar")
    await create_audit_log(admin_user["_id"], admin_user["email"], "stripe_connection_repair", "partner", partner_id, {"customer_id": report["proposed_customer_id"], "subscription_id": report["proposed_subscription_id"]})
    return {"message": "Stripe-Verbindung repariert", "partner_id": partner_id}

@admin_router.get("/audit-log")
async def admin_get_audit_log(request: Request, limit: int = 100, skip: int = 0, action: str = "", date_from: str = "", date_to: str = ""):
    await require_role("admin")(request)
    query = {}
    if action:
        query["action"] = action
    if date_from:
        query.setdefault("timestamp", {})["$gte"] = date_from
    if date_to:
        query.setdefault("timestamp", {})["$lte"] = date_to
    total = await db.audit_logs.count_documents(query)
    cursor = db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(max(skip, 0))
    if limit > 0:
        logs = await cursor.limit(limit).to_list(limit)
    else:
        logs = await cursor.to_list(total)
    return {"logs": logs, "total": total, "action_types": await db.audit_logs.distinct("action")}

# ========================
# PARTNER DASHBOARD ROUTES
# ========================

@api_router.get("/partner/profile")
async def get_partner_profile(request: Request):
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        return {"name": user["name"], "email": user["email"], "partner_name": None, "partner_id": None}
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        return {"name": user["name"], "email": user["email"], "partner_name": None, "partner_id": partner_id}
    return {
        "name": user["name"], "email": user["email"],
        "partner_name": partner.get("name"),
        "partner_id": partner_id,
        "description": partner.get("description", ""),
        "category": partner.get("category", ""),
        "tags": partner.get("tags", []),
        "logo_url": partner.get("logo_url", ""),
        "survey_ids": partner.get("survey_ids", []),
        "registration_status": partner.get("registration_status", "active"),
        "registration_source": partner.get("registration_source", "admin"),
        "is_active": partner.get("is_active", True),
    }


async def _own_partner(request: Request) -> tuple[dict, dict]:
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id or not ObjectId.is_valid(partner_id):
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return user, partner


def _invoice_view(invoice: dict) -> dict:
    return {k: invoice.get(k) for k in (
        "id", "number", "status", "amount_due", "amount_paid", "currency",
        "created", "period_start", "period_end", "invoice_pdf", "hosted_invoice_url", "livemode",
    )}


async def _usage_billing_stats(partner_id: str) -> dict:
    rows = await db.partner_usage_charges.find({"partner_id": partner_id}, {"_id": 0}).to_list(10000)
    open_rows = [row for row in rows if row.get("status") != "billed"]
    billed_rows = [row for row in rows if row.get("status") == "billed"]
    return {
        "pending_users": len(open_rows),
        "pending_amount": sum(int(row.get("amount", 0)) for row in open_rows),
        "billed_users": len(billed_rows),
        "billed_amount": sum(int(row.get("amount", 0)) for row in billed_rows),
        "currency": next((row.get("currency") for row in reversed(rows) if row.get("currency")), "eur"),
        "pending": open_rows,
    }


def _effective_partner_user_fee(settings: dict, service_step: dict | None, partner: dict) -> tuple[int, str]:
    amount = int(settings.get("stripe_partner_user_fee_cents") or 0)
    source = "global"
    if service_step and service_step.get("partner_user_fee_cents") is not None:
        amount, source = int(service_step["partner_user_fee_cents"]), "step"
    step_id = str((service_step or {}).get("id") or (service_step or {}).get("_id") or "")
    partner_prices = partner.get("step_user_fee_cents") or {}
    if step_id and partner_prices.get(step_id) is not None:
        amount, source = int(partner_prices[step_id]), "partner_step"
    return amount, source


def _service_step_for_partner_action(steps: list, progress: list, action_step: dict, partner: dict) -> dict | None:
    progress_by_step = {row.get("step_id"): row for row in progress}
    partner_id, partner_name = str(partner["_id"]), partner.get("name", "")
    candidates = []
    for step in steps:
        if step.get("step_type") not in {"partner_selection", "partner_multiselection"} or step.get("order", 0) > action_step.get("order", 0):
            continue
        data = (progress_by_step.get(step["id"]) or {}).get("data") or {}
        selected = {str(value) for value in (data.get("selected_partner_ids") or [])}
        if data.get("selected_partner_id"):
            selected.add(str(data["selected_partner_id"]))
        if partner_id in selected or (partner_name and data.get("selected_partner_name") == partner_name):
            candidates.append(step)
    return max(candidates, key=lambda item: item.get("order", 0), default=None)


async def _record_partner_user_charge(partner: dict, target_user: dict, upload: dict, service_step: dict | None = None) -> dict:
    """Create one charge per partner/candidate/service step and queue it for the next invoice."""
    partner_id, user_id = str(partner["_id"]), str(target_user["_id"])
    service_step_id = str((service_step or {}).get("id") or (service_step or {}).get("_id") or "")
    charge_key = {"partner_id": partner_id, "user_id": user_id, "service_step_id": service_step_id}
    existing = await db.partner_usage_charges.find_one(charge_key)
    if existing:
        return existing
    settings = await db.site_settings.find_one({"_key": "global"}) or {}
    amount, price_source = _effective_partner_user_fee(settings, service_step, partner)
    currency = (settings.get("stripe_partner_user_fee_currency") or (partner.get("billing_settings") or {}).get("default_currency") or "eur").lower()
    now = datetime.now(timezone.utc).isoformat()
    charge_id = str(uuid.uuid4())
    document = {
        "id": charge_id, "partner_id": partner_id, "partner_name": partner.get("name", ""),
        "user_id": user_id, "user_name": target_user.get("name", ""),
        "amount": amount, "currency": currency, "status": "pending",
        "service_step_id": service_step_id,
        "service_step_title": (service_step or {}).get("title", ""), "price_source": price_source,
        "first_upload_file_id": upload.get("file_id"), "created_at": now,
    }
    try:
        await db.partner_usage_charges.insert_one(document)
    except DuplicateKeyError:
        return await db.partner_usage_charges.find_one(charge_key) or document
    customer_id, subscription_id = partner.get("stripe_customer_id"), partner.get("stripe_subscription_id")
    if amount <= 0 or not customer_id or not subscription_id:
        reason = "Nutzergebühr nicht konfiguriert" if amount <= 0 else "Stripe-Kunde oder Abonnement fehlt"
        await db.partner_usage_charges.update_one({"id": charge_id}, {"$set": {"sync_error": reason}})
        return document
    try:
        item = await create_pending_invoice_item(
            customer_id, subscription_id, amount, currency,
            f"Nutzergebühr – {target_user.get('name') or user_id}",
            {"partner_id": partner_id, "user_id": user_id, "service_step_id": service_step_id, "usage_charge_id": charge_id},
        )
        await db.partner_usage_charges.update_one({"id": charge_id}, {"$set": {
            "status": "queued", "stripe_invoice_item_id": item.get("id"), "queued_at": datetime.now(timezone.utc).isoformat(), "sync_error": "",
        }})
    except HTTPException as exc:
        await db.partner_usage_charges.update_one({"id": charge_id}, {"$set": {"sync_error": str(exc.detail)}})
    return document


async def _sync_pending_partner_usage_charges(partner: dict) -> int:
    """Queue unsynced ledger rows once the partner has an active Stripe subscription."""
    customer_id, subscription_id = partner.get("stripe_customer_id"), partner.get("stripe_subscription_id")
    if not customer_id or not subscription_id:
        return 0
    partner_id = str(partner["_id"])
    rows = await db.partner_usage_charges.find({
        "partner_id": partner_id,
        "status": "pending",
        "stripe_invoice_item_id": {"$exists": False},
        "amount": {"$gt": 0},
    }, {"_id": 0}).to_list(10000)
    synced = 0
    for row in rows:
        try:
            item = await create_pending_invoice_item(
                customer_id, subscription_id, int(row["amount"]), row.get("currency", "eur"),
                f"Nutzergebühr – {row.get('user_name') or row['user_id']}",
                {"partner_id": partner_id, "user_id": row["user_id"], "service_step_id": row.get("service_step_id", ""), "usage_charge_id": row["id"]},
            )
            await db.partner_usage_charges.update_one({"id": row["id"], "status": "pending"}, {"$set": {
                "status": "queued", "stripe_invoice_item_id": item.get("id"),
                "queued_at": datetime.now(timezone.utc).isoformat(), "sync_error": "",
            }})
            synced += 1
        except HTTPException as exc:
            await db.partner_usage_charges.update_one({"id": row["id"]}, {"$set": {"sync_error": str(exc.detail)}})
    return synced


@payment_router.get("/settings")
async def get_partner_billing(request: Request):
    _, partner = await _own_partner(request)
    site = await db.site_settings.find_one({"_key": "global"}) or {}
    step_query = {"step_type": {"$in": ["partner_selection", "partner_multiselection"]}, "is_active": True, "filter_tag": {"$in": partner.get("tags") or []}}
    if partner.get("survey_ids"):
        step_query["survey_id"] = {"$in": partner["survey_ids"]}
    service_steps = await db.steps.find(step_query).sort([("survey_id", 1), ("order", 1)]).to_list(1000)
    pricing = []
    for step in service_steps:
        view = {**step, "id": str(step["_id"])}
        amount, source = _effective_partner_user_fee(site, view, partner)
        pricing.append({"step_id": view["id"], "step_title": step.get("title", ""), "step_order": step.get("order", 0), "amount": amount, "currency": (site.get("stripe_partner_user_fee_currency") or "eur").lower(), "source": source})
    return {"settings": partner.get("billing_settings", {}), "stripe": await public_stripe_status(), "billing_status": partner.get("billing_status", "paid"), "payment_configured": bool(site.get("stripe_partner_price_id")), "usage": await _usage_billing_stats(str(partner["_id"])), "pricing": pricing}


@payment_router.get("/status")
async def partner_payment_status(request: Request, session_id: Optional[str] = None):
    _, partner = await _own_partner(request)
    if session_id:
        session = await checkout_session(session_id)
        if session.get("client_reference_id") != str(partner["_id"]):
            raise HTTPException(status_code=403, detail="Checkout session does not belong to this partner")
        if session.get("payment_status") == "paid":
            subscription = session.get("subscription")
            await db.partners.update_one({"_id": partner["_id"]}, {"$set": {
                "billing_status": "paid", "access_unlocked": True,
                "stripe_customer_id": session.get("customer"),
                "stripe_subscription_id": subscription.get("id") if isinstance(subscription, dict) else subscription,
                "paid_at": datetime.now(timezone.utc).isoformat(),
            }})
            partner["billing_status"] = "paid"
    return {"billing_status": partner.get("billing_status", "paid"), "access_unlocked": partner.get("registration_source") != "self_service" or partner.get("billing_status") in {"paid", "active", "trialing"}}


@payment_router.post("/checkout")
async def partner_payment_checkout(request: Request):
    user, partner = await _own_partner(request)
    settings = await db.site_settings.find_one({"_key": "global"}) or {}
    price_id = settings.get("stripe_partner_price_id")
    if not price_id:
        raise HTTPException(status_code=503, detail="Der Partnerpreis wurde im Adminbereich noch nicht konfiguriert")
    customer_id = partner.get("stripe_customer_id")
    if not customer_id:
        customer = await create_customer(user["email"], partner.get("name", user["name"]), str(partner["_id"]))
        customer_id = customer["id"]
        await db.partners.update_one({"_id": partner["_id"]}, {"$set": {"stripe_customer_id": customer_id}})
    base = os.environ.get("FRONTEND_URL", "http://localhost:3001").rstrip("/")
    session = await create_checkout_session(
        customer_id, price_id, str(partner["_id"]),
        f"{base}/partner-payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        f"{base}/partner-payment/cancelled",
        "subscription",
        settings.get("stripe_automatic_tax", False), settings.get("stripe_allow_promotion_codes", False),
    )
    return {"url": session["url"]}


@payment_router.post("/portal")
async def partner_payment_portal(request: Request):
    _, partner = await _own_partner(request)
    if not partner.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="Noch kein Stripe-Kundenkonto vorhanden")
    base = os.environ.get("FRONTEND_URL", "http://localhost:3001").rstrip("/")
    return {"url": (await create_customer_portal(partner["stripe_customer_id"], f"{base}/partner-dashboard?tab=billing"))["url"]}


@payment_router.put("/settings")
async def update_partner_billing(data: PartnerBillingSettingsUpdate, request: Request):
    user, partner = await _own_partner(request)
    update = {k: (v.lower() if k in {"country", "default_currency"} and v else v) for k, v in data.model_dump(exclude_none=True).items()}
    await db.partners.update_one({"_id": partner["_id"]}, {"$set": {f"billing_settings.{k}": v for k, v in update.items()}})
    await create_audit_log(user["_id"], user["email"], "partner_billing_update", "partner", str(partner["_id"]), {"fields": list(update)})
    return {"message": "Billing settings updated"}


@payment_router.get("/stripe-status")
async def partner_stripe_status(request: Request):
    _, partner = await _own_partner(request)
    return {**(await public_stripe_status()), "billing_status": partner.get("billing_status", "paid"), "customer_created": bool(partner.get("stripe_customer_id"))}


@payment_router.get("/invoices")
async def partner_stripe_invoices(request: Request):
    _, partner = await _own_partner(request)
    if not partner.get("stripe_customer_id"):
        return []
    payload = await list_customer_invoices(partner["stripe_customer_id"])
    return [_invoice_view(invoice) for invoice in payload.get("data", [])]


@payment_router.post("/webhook")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("stripe-signature", "")
    settings = await db.site_settings.find_one({"_key": "global"}) or {}
    prefix = "test" if settings.get("stripe_sandbox_mode", True) else "live"
    secret = settings.get(f"stripe_{prefix}_webhook_secret", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured")
    parts = dict(item.split("=", 1) for item in signature.split(",") if "=" in item)
    timestamp, supplied = parts.get("t"), parts.get("v1")
    if not timestamp or not supplied or abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    event = json.loads(body)
    obj = event.get("data", {}).get("object", {})
    event_type = event.get("type", "")
    customer_id = obj.get("customer")
    partner_id = obj.get("metadata", {}).get("partner_id") or obj.get("client_reference_id")
    query = {"_id": ObjectId(partner_id)} if partner_id and ObjectId.is_valid(partner_id) else {"stripe_customer_id": customer_id}
    if event_type in {"invoice.created", "invoice.finalized", "invoice.paid"}:
        for line in (obj.get("lines") or {}).get("data", []):
            metadata = line.get("metadata") or {}
            charge_id = metadata.get("usage_charge_id")
            if not charge_id:
                parent = line.get("parent") or {}
                metadata = (parent.get("invoice_item_details") or {}).get("metadata") or metadata
                charge_id = metadata.get("usage_charge_id")
            if charge_id:
                update = {"stripe_invoice_id": obj.get("id"), "invoice_number": obj.get("number")}
                if event_type == "invoice.paid":
                    update.update({"status": "billed", "billed_at": datetime.now(timezone.utc).isoformat()})
                await db.partner_usage_charges.update_one({"id": charge_id}, {"$set": update})
    if event_type == "checkout.session.completed" and obj.get("payment_status") == "paid":
        await db.partners.update_one(query, {"$set": {"billing_status": "paid", "access_unlocked": True, "stripe_customer_id": customer_id, "stripe_subscription_id": obj.get("subscription"), "paid_at": datetime.now(timezone.utc).isoformat()}})
        updated_partner = await db.partners.find_one(query)
        if updated_partner:
            await _sync_pending_partner_usage_charges(updated_partner)
    elif event_type in {"invoice.paid", "customer.subscription.updated"}:
        status = obj.get("status")
        if event_type == "invoice.paid" or status in {"active", "trialing"}:
            await db.partners.update_one(query, {"$set": {"billing_status": "active", "access_unlocked": True}})
    elif event_type in {"invoice.payment_failed", "customer.subscription.deleted"}:
        await db.partners.update_one(query, {"$set": {"billing_status": "past_due" if event_type == "invoice.payment_failed" else "cancelled", "access_unlocked": False}})
    return {"received": True}

@api_router.put("/partner/profile")
async def update_partner_profile(data: ProfileUpdate, request: Request):
    user = await require_role("partner")(request)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "name" in update_data:
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"name": update_data.pop("name")}})
    if update_data:
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {f"profile.{k}": v for k, v in update_data.items()}})
    return {"message": "Profile updated"}


@api_router.put("/partner/partner-data")
async def update_own_partner_data(data: PartnerSelfUpdate, request: Request):
    """Allow a partner user to edit their own Partner record (description + tags only,
    name/category/logo remain admin-controlled)."""
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if "tags" in update:
        # dedupe + strip empty
        update["tags"] = sorted({t.strip() for t in update["tags"] if isinstance(t, str) and t.strip()})
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$set": update})
    await create_audit_log(user["_id"], user["email"], "partner_self_update",
                            "partner", partner_id, {"fields": list(update.keys())})
    return {"message": "Partner data updated"}


@api_router.get("/partner/insights")
async def get_partner_insights(request: Request):
    """Return a compact analytics payload for the partner's dashboard.

    Numbers are derived from the actual partner_submissions documents so they
    line up with what the partner sees in My-/Completed-Users tabs:
      - new_submissions_7d / _30d  → submissions whose `created_at` falls in
        the window (the canonical "submission timestamp" — this codebase
        never writes a separate `submitted_at`).
      - by_fachrichtung / by_bundesland → step-1 profile facets across all
        target users (submissions ∪ linked_user_ids).
      - conversion_funnel:
          received  = total submissions
          accepted  = submissions linked to a user that has at least one
                      progress entry beyond Stammdaten (i.e. the partner's
                      offer was acted on)
          completed = submissions where partner_work_completed=True
      - timeline_30d → daily counts of newly created submissions.
    """
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    now = datetime.now(timezone.utc)
    now_ts = now.isoformat()
    cutoff_7 = (now - timedelta(days=7)).isoformat()
    timeline_start = datetime.combine((now - timedelta(days=29)).date(), datetime.min.time(), tzinfo=timezone.utc)
    cutoff_30 = timeline_start.isoformat()

    partner_doc = await db.partners.find_one({"_id": ObjectId(partner_id)})
    linked_user_ids = set((partner_doc or {}).get("linked_user_ids", []))
    submissions = await db.partner_submissions.find({"partner_id": partner_id}, {"_id": 0}).to_list(5000)

    def _ts(s: dict) -> str:
        # canonical timestamp = created_at; fall back to legacy `submitted_at`
        return s.get("created_at") or s.get("submitted_at") or ""

    target_user_ids = set(s.get("user_id") for s in submissions if s.get("user_id")) | linked_user_ids

    new_7 = sum(1 for s in submissions if cutoff_7 <= _ts(s) <= now_ts)
    new_30 = sum(1 for s in submissions if cutoff_30 <= _ts(s) <= now_ts)

    by_fach: dict[str, int] = {}
    by_bl: dict[str, int] = {}

    # "Accepted" = partner submission's user has at least one non-Stammdaten
    # step in `completed` or `in_progress` — the user actually progressed
    # past initial profile after picking the partner.
    accepted_user_ids: set[str] = set()
    if target_user_ids:
        async for prog in db.user_progress.find({
            "user_id": {"$in": list(target_user_ids)},
            "status": {"$in": ["completed", "in_progress"]},
            "step_order": {"$gt": 1},
        }, {"user_id": 1}):
            accepted_user_ids.add(prog["user_id"])

    profiles_by_user = {}
    if target_user_ids:
        async for row in db.user_progress.find({
            "user_id": {"$in": list(target_user_ids)}, "step_order": 1,
        }, {"user_id": 1, "data": 1}):
            profiles_by_user[row["user_id"]] = row.get("data") or {}
    for uid in target_user_ids:
        profile = profiles_by_user.get(uid, {})
        fach = profile.get("fachrichtung_gewuenscht") or profile.get("fachrichtung_praktiziert") or profile.get("field_of_study") or "Unbekannt"
        bl = profile.get("anerkennungsverfahren_bundesland") or "Unbekannt"
        by_fach[fach] = by_fach.get(fach, 0) + 1
        by_bl[bl] = by_bl.get(bl, 0) + 1

    funnel = {"received": 0, "accepted": 0, "completed": 0}
    timeline: dict[str, int] = {}
    for s in submissions:
        funnel["received"] += 1
        uid = s.get("user_id")
        if uid in accepted_user_ids:
            funnel["accepted"] += 1
        # `partner_work_completed` is the canonical "this partner finished
        # their part" flag; legacy code also looked at status=='completed'.
        if s.get("partner_work_completed") is True or s.get("status") == "completed":
            funnel["completed"] += 1
        ts = _ts(s)
        if cutoff_30 <= ts <= now_ts:
            day = ts[:10]
            timeline[day] = timeline.get(day, 0) + 1

    # 30 day continuous timeline
    timeline_series = []
    for i in range(29, -1, -1):
        d = (now - timedelta(days=i)).date().isoformat()
        timeline_series.append({"date": d, "count": timeline.get(d, 0)})

    total_users = len(target_user_ids)
    conversion_rate = round((funnel["accepted"] / funnel["received"]) * 100) if funnel["received"] else 0

    return {
        "new_submissions_7d": new_7,
        "new_submissions_30d": new_30,
        "total_linked_users": total_users,
        "by_fachrichtung": sorted(
            [{"label": k, "count": v} for k, v in by_fach.items()],
            key=lambda x: x["count"], reverse=True)[:10],
        "by_bundesland": sorted(
            [{"label": k, "count": v} for k, v in by_bl.items()],
            key=lambda x: x["count"], reverse=True)[:10],
        "conversion_funnel": funnel,
        "conversion_rate_pct": conversion_rate,
        "timeline_30d": timeline_series,
    }


async def _partner_work_status_for_user(user_id: str, partner_id: str, partner_name: str) -> dict:
    """Return { completed: bool, completed_at: str|None, milestone_step_id: str|None }.

    `completed` = every milestone associated with this partner's picks for the user
    is in status 'completed'. `completed_at` = the latest such milestone's
    completed_at timestamp (for the Partner Dashboard "Completed On" column).
    `milestone_step_id` = the most recent managed milestone (used for Re-open).
    """
    statuses = await _partner_work_status_for_users([user_id], partner_id, partner_name)
    return statuses.get(user_id, {
        "completed": False, "completed_at": None, "milestone_step_id": None,
    })


def _partner_work_status_from_context(
    all_steps: list[dict], progs: list[dict], partner_id: str, partner_name: str,
) -> dict:
    prog_by_step = {p.get("step_id"): p for p in progs}

    managed_milestone_ids: list[str] = []
    for idx, s in enumerate(all_steps):
        if s.get("step_type") not in ("partner_selection", "partner_multiselection"):
            continue
        sid = str(s["_id"])
        pr = prog_by_step.get(sid) or {}
        d = pr.get("data") or {}
        picks = set()
        if d.get("selected_partner_id"):
            picks.add(str(d["selected_partner_id"]))
        for pid in (d.get("selected_partner_ids") or []):
            picks.add(str(pid))
        name_match = bool(partner_name) and d.get("selected_partner_name") == partner_name
        if partner_id not in picks and not name_match:
            continue
        for nxt in all_steps[idx + 1:]:
            if nxt.get("step_type") == "decision":
                break
            if nxt.get("step_type") == "milestone":
                managed_milestone_ids.append(str(nxt["_id"]))
                break

    if not managed_milestone_ids:
        return {"completed": False, "completed_at": None, "milestone_step_id": None}

    all_done = all((prog_by_step.get(mid) or {}).get("status") == "completed"
                   for mid in managed_milestone_ids)
    # Latest completed_at among managed milestones
    latest = None
    for mid in managed_milestone_ids:
        ts = (prog_by_step.get(mid) or {}).get("completed_at")
        if ts and (latest is None or ts > latest):
            latest = ts
    return {
        "completed": all_done,
        "completed_at": latest,
        "milestone_step_id": managed_milestone_ids[-1],
    }


async def _partner_work_status_for_users(
    user_ids: list[str], partner_id: str, partner_name: str,
) -> dict[str, dict]:
    """Bulk partner milestone state with three queries regardless of user count."""
    unique_ids = list(dict.fromkeys(uid for uid in user_ids if uid))
    if not unique_ids:
        return {}
    object_ids = [ObjectId(uid) for uid in unique_ids if ObjectId.is_valid(uid)]
    users = await db.users.find(
        {"_id": {"$in": object_ids}}, {"survey_id": 1}
    ).to_list(len(object_ids) or 1)
    survey_by_user = {str(user["_id"]): user.get("survey_id") for user in users}
    survey_ids = {sid for sid in survey_by_user.values() if sid}
    steps = await db.steps.find(
        {"is_active": True, "survey_id": {"$in": list(survey_ids)}},
        {"_id": 1, "survey_id": 1, "order": 1, "step_type": 1},
    ).sort([("survey_id", 1), ("order", 1)]).to_list(1000)
    steps_by_survey: dict[str, list[dict]] = {}
    for step in steps:
        steps_by_survey.setdefault(step.get("survey_id"), []).append(step)
    progress = await db.user_progress.find(
        {"user_id": {"$in": unique_ids}}, {"_id": 0}
    ).to_list(max(1000, len(unique_ids) * 100))
    progress_by_user: dict[str, list[dict]] = {}
    for row in progress:
        progress_by_user.setdefault(row.get("user_id"), []).append(row)
    return {
        uid: _partner_work_status_from_context(
            steps_by_survey.get(survey_by_user.get(uid), []),
            progress_by_user.get(uid, []),
            partner_id,
            partner_name,
        )
        for uid in unique_ids
    }


PARTNER_EMAIL_PAYMENT_NOTICE = "Bitte authorisieren Sie ihre Zahlung"
PAID_PARTNER_BILLING_STATUSES = {"paid", "active", "trialing"}


async def _partner_user_email_value(partner_user: dict, partner: dict | None, email: str) -> str:
    """Return PII only when RBAC and the partner's payment entitlement allow it."""
    can_view_by_group = await has_permission(partner_user, "partner.users.email.view")
    payment_allows_email = (
        (partner or {}).get("registration_source") != "self_service"
        or (partner or {}).get("billing_status") in PAID_PARTNER_BILLING_STATUSES
    )
    return email if can_view_by_group and payment_allows_email else PARTNER_EMAIL_PAYMENT_NOTICE


@api_router.get("/partner/submissions")
async def get_partner_submissions(request: Request):
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    visible_email = lambda email: _partner_user_email_value(user, partner, email)
    partner_name = (partner or {}).get("name") or ""
    linked_user_ids = set(partner.get("linked_user_ids", [])) if partner else set()
    submissions = await db.partner_submissions.find({"partner_id": partner_id}, {"_id": 0}).to_list(1000)
    seen_user_ids = {sub.get("user_id") for sub in submissions if sub.get("user_id")}
    target_user_ids = seen_user_ids | linked_user_ids
    metrics_by_user = await calculate_users_metrics(list(target_user_ids))
    work_by_user = await _partner_work_status_for_users(
        list(target_user_ids), partner_id, partner_name,
    )
    step1_by_user = {}
    if target_user_ids:
        async for row in db.user_progress.find({
            "user_id": {"$in": list(target_user_ids)},
            "step_order": 1,
        }, {"user_id": 1, "data": 1}):
            step1_by_user[row["user_id"]] = row.get("data") or {}
    for sub in submissions:
        sub["user_email"] = await visible_email(sub.get("user_email", ""))
        uid = sub.get("user_id")
        if uid:
            metrics = metrics_by_user.get(uid, {})
            sub["estimated_completion"] = metrics.get("estimated_completion")
            sub["completion_pct"] = metrics.get("completion_pct", 0)
            ws = work_by_user.get(uid, {})
            sub["partner_work_completed"] = ws["completed"]
            sub["partner_work_completed_at"] = ws["completed_at"]
            sub["partner_milestone_step_id"] = ws["milestone_step_id"]
            s1data = step1_by_user.get(uid, {})
            sub["field_of_study"] = s1data.get("fachrichtung_gewuenscht") or s1data.get("fachrichtung_praktiziert") or s1data.get("field_of_study", "")
            sub["bundesland"] = s1data.get("anerkennungsverfahren_bundesland", "")
    missing_linked_ids = linked_user_ids - seen_user_ids
    linked_users_by_id = {}
    if missing_linked_ids:
        object_ids = [ObjectId(uid) for uid in missing_linked_ids if ObjectId.is_valid(uid)]
        linked_users = await db.users.find(
            {"_id": {"$in": object_ids}, "role": "user"}, {"password_hash": 0}
        ).to_list(len(object_ids) or 1)
        linked_users_by_id = {str(row["_id"]): row for row in linked_users}
    for uid in missing_linked_ids:
        if uid in seen_user_ids:
            continue
        u = linked_users_by_id.get(uid)
        if not u:
            continue
        s1data = step1_by_user.get(uid, {})
        field_of_study = s1data.get("fachrichtung_gewuenscht") or s1data.get("fachrichtung_praktiziert") or s1data.get("field_of_study", "")
        bundesland = s1data.get("anerkennungsverfahren_bundesland", "")
        ws = work_by_user.get(uid, {})
        metrics = metrics_by_user.get(uid, {})
        submissions.append({
            "user_id": uid, "user_name": u["name"], "user_email": await visible_email(u["email"]),
            "partner_id": partner_id, "data": {"source": "linked"}, "status": "linked",
            "completion_pct": metrics.get("completion_pct", 0),
            "estimated_completion": metrics.get("estimated_completion"),
            "field_of_study": field_of_study, "bundesland": bundesland,
            "partner_work_completed": ws["completed"],
            "partner_work_completed_at": ws["completed_at"],
            "partner_milestone_step_id": ws["milestone_step_id"],
        })
        seen_user_ids.add(uid)
    return submissions


@api_router.put("/partner/users/{user_id}/reopen")
async def partner_reopen_milestone(user_id: str, request: Request):
    """Re-open the partner's managed milestone for a user: move status back to
    'in_progress' and clear completed_at, so the user reappears in 'My Users'.
    """
    partner_user = await require_role("partner")(request)
    partner_id = partner_user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    partner_name = (partner or {}).get("name") or ""
    ws = await _partner_work_status_for_user(user_id, partner_id, partner_name)
    msid = ws.get("milestone_step_id")
    if not msid:
        raise HTTPException(status_code=400, detail="No managed milestone found for this user")
    now = datetime.now(timezone.utc).isoformat()
    await db.user_progress.update_one(
        {"user_id": user_id, "step_id": msid},
        {"$set": {"status": "in_progress", "updated_at": now},
         "$unset": {"completed_at": ""}},
    )
    # Audit trail: log the re-open action in progress_history if the collection exists
    try:
        await db.progress_history.insert_one({
            "user_id": user_id, "step_id": msid,
            "action": "reopened_by_partner",
            "partner_id": partner_id, "partner_name": partner_name,
            "actor": partner_user["email"],
            "created_at": now,
        })
    except Exception:
        pass
    return {"message": "Milestone re-opened", "step_id": msid}

@api_router.get("/partner/other-users")
async def get_partner_other_users(request: Request):
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    linked_user_ids = set(partner.get("linked_user_ids", [])) if partner else set()
    submissions = await db.partner_submissions.find({"partner_id": partner_id}, {"user_id": 1}).to_list(1000)
    my_user_ids = {sub["user_id"] for sub in submissions} | linked_user_ids
    all_users = await db.users.find({"role": "user"}, {"password_hash": 0}).to_list(1000)
    other_users = [u for u in all_users if str(u["_id"]) not in my_user_ids]
    other_ids = [str(u["_id"]) for u in other_users]
    metrics_by_user = await calculate_users_metrics(other_ids)
    step1_by_user = {}
    if other_ids:
        async for row in db.user_progress.find({
            "user_id": {"$in": other_ids}, "step_order": 1,
        }, {"user_id": 1, "data": 1}):
            step1_by_user[row["user_id"]] = row.get("data") or {}
    result = []
    for u in other_users:
        uid = str(u["_id"])
        s1data = step1_by_user.get(uid, {})
        metrics = metrics_by_user.get(uid, {})
        result.append({"user_id": uid, "user_name": u["name"], "user_email": await _partner_user_email_value(user, partner, u["email"]), "completion_pct": metrics.get("completion_pct", 0), "estimated_completion": metrics.get("estimated_completion"), "field_of_study": s1data.get("fachrichtung_gewuenscht") or s1data.get("fachrichtung_praktiziert") or s1data.get("field_of_study", ""), "bundesland": s1data.get("anerkennungsverfahren_bundesland", ""), "created_at": u.get("created_at", "")})
    return result


def _compute_partner_managed_step_ids(all_steps: list, progress: list, partner_id: str, partner_name: str) -> list[str]:
    """Return only steps this user explicitly assigned to the current partner."""
    progress_by_step_id = {p.get("step_id"): p for p in progress}
    managed: list[str] = []
    for step in all_steps:
        if step.get("step_type") not in ("partner_selection", "partner_multiselection"):
            continue
        step_data = (progress_by_step_id.get(step["id"]) or {}).get("data") or {}
        selected_ids = set()
        if step_data.get("selected_partner_id"):
            selected_ids.add(str(step_data["selected_partner_id"]))
        selected_ids.update(str(value) for value in (step_data.get("selected_partner_ids") or []))
        name_match = bool(partner_name) and step_data.get("selected_partner_name") == partner_name
        if str(partner_id) not in selected_ids and not name_match:
            continue
        managed.append(step["id"])
        for next_step in all_steps:
            if next_step["order"] <= step["order"]:
                continue
            if next_step.get("step_type") == "milestone":
                managed.append(next_step["id"])
                break
            if next_step.get("step_type") == "decision":
                break
    return list(dict.fromkeys(managed))

@api_router.get("/partner/users/{user_id}")
async def get_partner_user_detail(user_id: str, request: Request):
    partner_user = await require_role("partner")(request)
    partner_id = partner_user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    partner_doc = await db.partners.find_one({"_id": ObjectId(partner_id)})
    target_user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    step_query = {"is_active": True}
    if target_user.get("survey_id"):
        step_query["survey_id"] = target_user["survey_id"]
    all_steps = []
    async for s in db.steps.find(step_query).sort("order", 1):
        all_steps.append({**{k: v for k, v in s.items() if k != "_id"}, "id": str(s["_id"])})
    partner_step_id = None
    partner_tags = set(partner_doc.get("tags", [])) if partner_doc else set()
    for s in all_steps:
        if s.get("step_type") in ("partner_selection", "partner_multiselection") and s.get("filter_tag") in partner_tags:
            partner_step_id = s["id"]
            break

    # ---- Compute partner_managed_step_ids ----
    # All partner_selection/partner_multiselection steps where this user picked THIS partner,
    # PLUS the next milestone step in the same block (by order).
    partner_name = (partner_doc or {}).get("name") or ""
    managed = _compute_partner_managed_step_ids(all_steps, progress, partner_id, partner_name)

    sanitized_progress = []
    for p in progress:
        step = next((s for s in all_steps if s["id"] == p.get("step_id")), None)
        if step and step.get("step_type") in ("partner_selection", "partner_multiselection"):
            data = p.get("data", {})
            if data.get("selected_partner_id") and data["selected_partner_id"] != partner_id:
                sanitized_progress.append({**p, "data": {}})
                continue
        sanitized_progress.append(p)
    return {
        "id": str(target_user["_id"]), "email": await _partner_user_email_value(partner_user, partner_doc, target_user["email"]),
        "name": target_user["name"], "progress": sanitized_progress,
        "steps": all_steps,
        "completion_pct": await calculate_completion_pct(user_id),
        "partner_step_id": partner_step_id,
        "partner_managed_step_ids": managed,
    }


async def _partner_step_action_context(user_id: str, partner_id: str, partner_doc: dict | None) -> tuple[dict, list, list, list[str]]:
    target_user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    progress_query = {"user_id": user_id}
    step_query = {"is_active": True}
    if target_user.get("survey_id"):
        progress_query["survey_id"] = target_user["survey_id"]
        step_query["survey_id"] = target_user["survey_id"]
    progress = await db.user_progress.find(progress_query, {"_id": 0}).to_list(500)
    step_docs = await db.steps.find(step_query).sort("order", 1).to_list(200)
    steps = [{**{k: v for k, v in step.items() if k != "_id"}, "id": str(step["_id"])} for step in step_docs]
    partner_name = (partner_doc or {}).get("name") or ""
    managed = _compute_partner_managed_step_ids(steps, progress, partner_id, partner_name)
    return target_user, progress, steps, managed


@api_router.post("/partner/users/{user_id}/steps/{step_id}/action")
async def partner_step_action(user_id: str, step_id: str, payload: PartnerStepAction, request: Request):
    """Approve or reject a step that is explicitly managed by this partner."""
    partner_user = await require_role("partner")(request)
    partner_id = partner_user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    if payload.action not in ("complete", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'complete' or 'reject'")
    if payload.action == "reject" and not (payload.reason or "").strip():
        raise HTTPException(status_code=422, detail="A rejection reason is required")

    partner_doc = await db.partners.find_one({"_id": ObjectId(partner_id)})
    target_user, progress, steps, managed = await _partner_step_action_context(user_id, partner_id, partner_doc)
    if step_id not in managed:
        raise HTTPException(status_code=403, detail="This step is not managed by your partner organization")
    step = next((item for item in steps if item["id"] == step_id), None)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    existing = next((item for item in progress if item.get("step_id") == step_id), {})
    existing_data = existing.get("data") or {}
    merged_data = {**existing_data, **(payload.data or {})}
    partner_name = (partner_doc or {}).get("name") or partner_user.get("name") or "Partner"
    actor = {
        "id": str(partner_user.get("_id") or ""),
        "email": partner_user.get("email", ""),
        "role": "partner",
        "partner_id": partner_id,
        "partner_name": partner_name,
    }
    base_event_payload = {
        "user_id": user_id,
        "user_name": target_user.get("name", ""),
        "user_email": target_user.get("email", ""),
        "user_email_notifications_enabled": (target_user.get("notification_preferences") or {}).get("email_on_step_leave", True),
        "partner_id": partner_id,
        "partner_name": partner_name,
        "step_id": step_id,
        "step_title": step.get("title", ""),
        "milestone_title": step.get("title", ""),
        "step_order": step.get("order", 0),
        "step_description": step.get("description", ""),
    }

    old_upload_ids = {
        entry.get("file_id") for entry in (existing_data.get("partner_uploads") or [])
        if isinstance(entry, dict) and entry.get("file_id")
    }
    new_uploads = [
        entry for entry in (merged_data.get("partner_uploads") or [])
        if isinstance(entry, dict) and entry.get("file_id") not in old_upload_ids
    ]
    emitted_events = []
    for upload in new_uploads:
        emitted_events.append(await emit_domain_event(
            "partner.document.uploaded",
            {**base_event_payload, "file_id": upload.get("file_id"), "filename": upload.get("filename", "")},
            actor,
        ))
    if new_uploads and partner_doc:
        service_step = _service_step_for_partner_action(steps, progress, step, partner_doc)
        await _record_partner_user_charge(partner_doc, target_user, new_uploads[0], service_step)

    if payload.action == "complete":
        was_rejected = bool(existing_data.get("partner_rejection"))
        merged_data.pop("partner_rejection", None)
        await db.user_progress.update_one(
            {"user_id": user_id, "step_id": step_id},
            {"$set": {
                "user_id": user_id,
                "step_id": step_id,
                "survey_id": target_user.get("survey_id"),
                "step_order": step.get("order", 0),
                "status": "completed",
                "data": merged_data,
                "started_at": existing.get("started_at") or now_iso,
                "updated_at": now_iso,
                "completed_at": now_iso,
            }},
            upsert=True,
        )
        if was_rejected:
            _, _, hidden_ids_before_completion, _ = await _get_step_context(user_id)
            previous_steps = [item for item in steps if item["order"] < step["order"] and item["id"] not in hidden_ids_before_completion]
            corrected_step = previous_steps[-1] if previous_steps else None
            if corrected_step:
                corrected_progress = await db.user_progress.find_one({"user_id": user_id, "step_id": corrected_step["id"]})
                await db.user_progress.update_one(
                    {"user_id": user_id, "step_id": corrected_step["id"]},
                    {"$set": {
                        "status": "completed",
                        "started_at": (corrected_progress or {}).get("started_at") or now_iso,
                        "completed_at": now_iso,
                        "updated_at": now_iso,
                    }},
                    upsert=True,
                )
        await apply_auto_completes(user_id)
        _, _, hidden_ids, _ = await _get_step_context(user_id)
        next_step = next((item for item in steps if item["order"] > step["order"] and item["id"] not in hidden_ids), None)
        if next_step:
            next_progress = await db.user_progress.find_one({"user_id": user_id, "step_id": next_step["id"]})
            if not next_progress or next_progress.get("status") != "completed":
                await db.user_progress.update_one(
                    {"user_id": user_id, "step_id": next_step["id"]},
                    {"$set": {
                        "user_id": user_id,
                        "step_id": next_step["id"],
                        "survey_id": target_user.get("survey_id"),
                        "step_order": next_step.get("order", 0),
                        "status": "in_progress",
                        "started_at": (next_progress or {}).get("started_at") or now_iso,
                        "updated_at": now_iso,
                    }},
                    upsert=True,
                )
        event = await emit_domain_event("partner.step.completed", base_event_payload, actor)
        emitted_events.append(event)
        history_action = "completed_by_partner"
        reopened_step = None
    else:
        _, _, hidden_ids, _ = await _get_step_context(user_id)
        previous_steps = [item for item in steps if item["order"] < step["order"] and item["id"] not in hidden_ids]
        reopened_step = previous_steps[-1] if previous_steps else None
        rejection = {
            "reason": payload.reason.strip(),
            "partner_id": partner_id,
            "partner_name": partner_name,
            "rejected_at": now_iso,
        }
        merged_data["partner_rejection"] = rejection
        await db.user_progress.update_one(
            {"user_id": user_id, "step_id": step_id},
            {"$set": {
                "user_id": user_id,
                "step_id": step_id,
                "survey_id": target_user.get("survey_id"),
                "step_order": step.get("order", 0),
                "status": "pending",
                "data": merged_data,
                "updated_at": now_iso,
            }, "$unset": {"completed_at": ""}},
            upsert=True,
        )
        if reopened_step:
            await db.user_progress.update_one(
                {"user_id": user_id, "step_id": reopened_step["id"]},
                {"$set": {
                    "user_id": user_id,
                    "step_id": reopened_step["id"],
                    "survey_id": target_user.get("survey_id"),
                    "step_order": reopened_step.get("order", 0),
                    "status": "in_progress",
                    "updated_at": now_iso,
                }, "$unset": {"completed_at": ""}},
                upsert=True,
            )
        event_payload = {
            **base_event_payload,
            "rejection_reason": payload.reason.strip(),
            "reopened_step_id": reopened_step["id"] if reopened_step else "",
            "reopened_step_title": reopened_step.get("title", "") if reopened_step else "",
            "reopened_step_order": reopened_step.get("order", "") if reopened_step else "",
        }
        event = await emit_domain_event("partner.step.rejected", event_payload, actor)
        emitted_events.append(event)
        history_action = "rejected_by_partner"

    await db.progress_history.insert_one({
        "user_id": user_id,
        "step_id": step_id,
        "step_title": step.get("title", ""),
        "step_order": step.get("order", 0),
        "action": history_action,
        "reason": payload.reason or "",
        "changed_by": partner_user.get("email", ""),
        "partner_id": partner_id,
        "timestamp": now_iso,
    })
    await create_audit_log(
        str(partner_user.get("_id") or ""), partner_user.get("email", ""), history_action,
        "user_step", step_id,
        {"user_id": user_id, "step_order": step.get("order"), "reason": payload.reason or ""},
    )
    return {
        "message": "Step completed" if payload.action == "complete" else "Step rejected",
        "step_id": step_id,
        "status": "completed" if payload.action == "complete" else "pending",
        "reopened_step": reopened_step,
        "events": emitted_events,
    }

@api_router.put("/partner/users/{user_id}/progress")
async def partner_update_user_progress(user_id: str, data: UserProgressUpdate, request: Request):
    partner_user = await require_role("partner")(request)
    partner_id = partner_user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    partner_doc = await db.partners.find_one({"_id": ObjectId(partner_id)})
    step = await db.steps.find_one({"_id": ObjectId(data.step_id)})
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    target_user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    _, _, _, managed = await _partner_step_action_context(user_id, partner_id, partner_doc)
    if data.step_id not in managed:
        raise HTTPException(status_code=403, detail="This step is not managed by your partner organization")
    now_iso = datetime.now(timezone.utc).isoformat()
    existing = await db.user_progress.find_one({"user_id": user_id, "step_id": data.step_id})
    update_fields = {"status": data.status, "updated_at": now_iso}
    if data.data:
        update_fields["data"] = data.data
    elif existing and existing.get("data"):
        update_fields["data"] = existing["data"]
    else:
        update_fields["data"] = {}
    if not existing or not existing.get("started_at"):
        update_fields["started_at"] = now_iso
    if data.status == "completed":
        update_fields["completed_at"] = now_iso
    await db.user_progress.update_one({"user_id": user_id, "step_id": data.step_id}, {"$set": update_fields}, upsert=True)
    await db.progress_history.insert_one({"user_id": user_id, "step_id": data.step_id, "step_title": step.get("title", ""), "step_order": step.get("order", 0), "action": data.status, "changed_by": partner_user["email"], "timestamp": now_iso})
    # Trigger auto-completion for subsequent steps
    await apply_auto_completes(user_id)
    if data.status == "completed":
        user_prefs = target_user.get("notification_preferences", {"email_on_step_enter": True, "email_on_step_edit": False, "email_on_step_leave": True})
        partner_name = partner_doc.get("name", "") if partner_doc else ""
        total_steps = await db.steps.count_documents({"is_active": True})
        email_vars = {
            "user_name": target_user["name"], "user_email": target_user["email"],
            "step_title": step["title"], "step_order": step["order"],
            "step_description": step.get("description", ""),
            "partner_name": partner_name,
            "milestone_title": step["title"],
            "total_steps": total_steps,
        }
        # 1) Milestone-completed notification to the user (partner closed their milestone)
        if user_prefs.get("email_on_step_leave", True):
            try:
                await notify_user_milestone_completed(target_user, partner_doc or {}, step)
                logger.info(f"Milestone completion email sent to {target_user['email']} for step '{step['title']}' by partner {partner_name}")
            except Exception as exc:
                logger.warning(f"notify_user_milestone_completed failed: {exc}")
        # Legacy: fire generic step-completed if the step itself has email_on_leave set
        if step.get("email_on_leave") and user_prefs.get("email_on_step_leave", True):
            await send_rendered_email(target_user["email"], "user_step_completed", email_vars,
                                       override_subject=step.get("email_subject_leave") or "",
                                       override_body=step.get("email_body_leave") or "")
        all_steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
        next_step = None
        for s in all_steps:
            if s["order"] > step.get("order", 0):
                next_step = s
                break
        if next_step:
            next_sid = str(next_step["_id"])
            next_prog = await db.user_progress.find_one({"user_id": user_id, "step_id": next_sid})
            if not next_prog or next_prog.get("status") == "pending":
                await db.user_progress.update_one({"user_id": user_id, "step_id": next_sid}, {"$set": {"status": "in_progress", "started_at": now_iso, "updated_at": now_iso}}, upsert=True)
                if user_prefs.get("email_on_step_enter", True):
                    next_vars = {
                        **email_vars,
                        "step_title": next_step["title"],
                        "step_order": next_step["order"],
                        "step_description": next_step.get("description", ""),
                    }
                    await send_rendered_email(target_user["email"], "user_next_step_unlocked", next_vars,
                                               override_subject=next_step.get("email_subject_enter") or "",
                                               override_body=next_step.get("email_body_enter") or "")
    return {"message": "User progress updated"}

@api_router.get("/users/{user_id}/estimated-completion")
async def get_user_estimated_completion(user_id: str, request: Request):
    await require_role("admin", "partner")(request)
    return {"estimated_completion": await calculate_estimated_completion(user_id)}

# ========================
# CMS ROUTES
# ========================

def _normalize_cms_payload(content: dict | None, translations: dict | None) -> tuple[dict, dict]:
    """Flatten legacy response-shaped CMS data accidentally written into content."""
    normalized_content = content if isinstance(content, dict) else {}
    normalized_translations = translations if isinstance(translations, dict) else {}
    while isinstance(normalized_content.get("content"), dict):
        wrapper = normalized_content
        nested_content = wrapper["content"]
        outer_content = {
            key: value for key, value in wrapper.items()
            if key not in {"content", "translations", "section"}
        }
        normalized_content = {**nested_content, **outer_content}
        nested_translations = wrapper.get("translations")
        if isinstance(nested_translations, dict):
            normalized_translations = {**nested_translations, **normalized_translations}
    return normalized_content, normalized_translations

@cms_router.get("")
async def get_cms_content():
    content = await db.cms_content.find({}, {"_id": 0}).to_list(100)
    return {
        c["section"]: dict(zip(("content", "translations"), _normalize_cms_payload(c.get("content"), c.get("translations"))))
        for c in content
    }

@cms_router.get("/{section}")
async def get_cms_section(section: str):
    content = await db.cms_content.find_one({"section": section}, {"_id": 0})
    if not content:
        return {"content": {}, "translations": {}}
    normalized_content, normalized_translations = _normalize_cms_payload(content.get("content"), content.get("translations"))
    return {"content": normalized_content, "translations": normalized_translations}

@cms_router.put("/{section}")
async def update_cms_content(section: str, data: CMSContentUpdate, request: Request):
    admin_user = await require_permission("cms.manage", "admin")(request)
    normalized_content, normalized_translations = _normalize_cms_payload(data.content, data.translations)
    update_fields = {"section": section, "content": normalized_content, "updated_at": datetime.now(timezone.utc).isoformat()}
    if data.translations is not None:
        update_fields["translations"] = normalized_translations
    await db.cms_content.update_one({"section": section}, {"$set": update_fields}, upsert=True)
    await create_audit_log(admin_user["_id"], admin_user["email"], "cms_update", "cms", section, {"section": section})
    return {"message": "Content updated"}

# ========================
# STEP TEMPLATES (Admin)
# ========================

def _sanitize_template_config(cfg: dict) -> dict:
    """Strip fields that shouldn't be re-used (order, is_active, created_at, _id, id)."""
    if not isinstance(cfg, dict):
        return {}
    ignore = {"_id", "id", "order", "is_active", "created_at", "updated_at"}
    return {k: v for k, v in cfg.items() if k not in ignore}


@admin_router.get("/step-templates")
async def admin_list_step_templates(request: Request):
    await require_role("admin")(request)
    tpls = await db.step_templates.find().sort("created_at", -1).to_list(200)
    return [{
        "id": str(t["_id"]), "name": t.get("name", ""),
        "description": t.get("description", ""),
        "config": t.get("config", {}),
        "created_at": t.get("created_at"),
    } for t in tpls]


@admin_router.post("/step-templates")
async def admin_create_step_template(data: StepTemplateCreate, request: Request):
    admin_user = await require_role("admin")(request)
    doc = {
        "name": data.name,
        "description": data.description or "",
        "config": _sanitize_template_config(data.config or {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.step_templates.insert_one(doc)
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_template_create",
                            "step_template", str(result.inserted_id), {"name": data.name})
    return {"id": str(result.inserted_id), "message": "Template created"}


@admin_router.put("/step-templates/{template_id}")
async def admin_update_step_template(template_id: str, data: StepTemplateUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if "config" in update:
        update["config"] = _sanitize_template_config(update["config"])
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.step_templates.update_one({"_id": ObjectId(template_id)}, {"$set": update})
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_template_update",
                            "step_template", template_id, {"fields": list(update.keys())})
    return {"message": "Template updated"}


@admin_router.delete("/step-templates/{template_id}")
async def admin_delete_step_template(template_id: str, request: Request):
    admin_user = await require_role("admin")(request)
    tpl = await db.step_templates.find_one({"_id": ObjectId(template_id)})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.step_templates.delete_one({"_id": ObjectId(template_id)})
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_template_delete",
                            "step_template", template_id, {"name": tpl.get("name", "")})
    return {"message": "Template deleted"}


@admin_router.post("/step-templates/from-step/{step_id}")
async def admin_save_step_as_template(step_id: str, request: Request, name: str = Query(...), description: str = Query("")):
    admin_user = await require_role("admin")(request)
    step = await db.steps.find_one({"_id": ObjectId(step_id)})
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    cfg = {k: v for k, v in step.items() if k != "_id"}
    doc = {
        "name": name,
        "description": description,
        "config": _sanitize_template_config(cfg),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.step_templates.insert_one(doc)
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_template_create",
                            "step_template", str(result.inserted_id), {"from_step": step_id, "name": name})
    return {"id": str(result.inserted_id), "message": "Template saved from step"}


@admin_router.post("/step-templates/{template_id}/apply")
async def admin_apply_template(template_id: str, request: Request, order: int = Query(...), survey_id: Optional[str] = Query(None)):
    """Instantiate a new step from a template at the given order.
    All existing steps with order >= given are shifted by +1 to make room."""
    admin_user = await require_role("admin")(request)
    tpl = await db.step_templates.find_one({"_id": ObjectId(template_id)})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    target_survey_id = survey_id or str((await _get_default_survey())["_id"])
    # Shift existing steps only inside the target survey.
    await db.steps.update_many({"survey_id": target_survey_id, "order": {"$gte": order}}, {"$inc": {"order": 1}})
    cfg = _sanitize_template_config(tpl.get("config", {}))
    cfg["survey_id"] = target_survey_id
    cfg["order"] = order
    cfg["is_active"] = True
    cfg["created_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.steps.insert_one(cfg)
    new_sid = str(result.inserted_id)
    # Create pending progress entries for all users (upsert to avoid duplicates)
    users = await db.users.find({"role": "user", "survey_id": target_survey_id}, {"_id": 1}).to_list(1000)
    for u in users:
        await db.user_progress.update_one(
            {"user_id": str(u["_id"]), "step_id": new_sid},
            {"$setOnInsert": {
                "user_id": str(u["_id"]), "step_id": new_sid, "survey_id": target_survey_id,
                "status": "pending", "data": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_template_apply",
                            "step", new_sid, {"template_id": template_id, "order": order})
    return {"id": new_sid, "message": "Template applied as new step"}


# ========================
# SITE SETTINGS
# ========================

@admin_router.get("/settings")
async def admin_get_settings(request: Request):
    await require_role("admin")(request)
    settings = await db.site_settings.find_one({"_key": "global"}, {"_id": 0, "_key": 0})
    settings = settings or {}
    for field in SECRET_FIELDS:
        if settings.get(field):
            settings[field] = "••••••••"
    settings["stripe"] = await public_stripe_status()
    return settings

@admin_router.put("/settings")
async def admin_update_settings(data: SiteSettingsUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None and v != "••••••••"}
    if update_data:
        await db.site_settings.update_one({"_key": "global"}, {"$set": update_data}, upsert=True)
    await create_audit_log(admin_user["_id"], admin_user["email"], "settings_update", "settings", "", {"fields": list(update_data)})
    return {"message": "Settings updated"}

@api_router.get("/settings/public")
async def get_public_settings():
    settings = await db.site_settings.find_one({"_key": "global"}, {"_id": 0, "_key": 0})
    settings = settings or {}
    for field in SECRET_FIELDS | {"stripe_test_publishable_key", "stripe_live_publishable_key"}:
        settings.pop(field, None)
    settings["stripe"] = await public_stripe_status()
    return settings

# ========================
# DOMAIN EVENTS (Admin)
# ========================

@admin_router.get("/event-configs")
async def admin_list_event_configs(request: Request):
    await require_role("admin")(request)
    await ensure_event_configs()
    configs = await db.event_configs.find({}, {"_id": 0}).sort("event_type", 1).to_list(100)
    return configs


@admin_router.put("/event-configs/{event_type}")
async def admin_update_event_config(event_type: str, payload: EventConfigUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    await ensure_event_configs()
    existing = await db.event_configs.find_one({"event_type": event_type})
    if not existing:
        raise HTTPException(status_code=404, detail="Event type not found")
    update = payload.model_dump(exclude_none=True)
    if "handlers" in update:
        normalized_handlers = []
        for index, handler in enumerate(update["handlers"]):
            handler_type = handler.get("type")
            if handler_type not in ("email", "notification"):
                raise HTTPException(status_code=422, detail="Only email and notification handlers are currently supported")
            normalized = {
                "id": handler.get("id") or f"handler-{index + 1}",
                "type": handler_type,
                "label": handler.get("label") or ("E-Mail senden" if handler_type == "email" else "Browser/App Notification"),
                "enabled": handler.get("enabled", True),
                "recipient": handler.get("recipient") or "user",
                "template_key": handler.get("template_key") or "",
            }
            if handler_type == "notification":
                normalized["channels"] = [
                    channel for channel in (handler.get("channels") or [])
                    if channel in ("browser", "app")
                ]
                normalized["provider"] = handler.get("provider") or "unconfigured"
            normalized_handlers.append(normalized)
        update["handlers"] = normalized_handlers
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.event_configs.update_one({"event_type": event_type}, {"$set": update})
    await create_audit_log(
        str(admin_user.get("_id") or ""), admin_user.get("email", ""), "event_config_update",
        "event_config", event_type, {"fields": list(update.keys())},
    )
    return await db.event_configs.find_one({"event_type": event_type}, {"_id": 0})


@admin_router.get("/events")
async def admin_list_domain_events(
    request: Request,
    limit: int = Query(default=100, ge=0, le=1000),
    skip: int = Query(default=0, ge=0),
    event_type: str = "",
    status: str = "",
):
    await require_role("admin")(request)
    query = {}
    if event_type:
        query["event_type"] = event_type
    if status:
        query["status"] = status
    total = await db.domain_events.count_documents(query)
    cursor = db.domain_events.find(query).sort("created_at", -1).skip(skip)
    documents = await (cursor.limit(limit).to_list(limit) if limit > 0 else cursor.to_list(total))
    return {"events": [serialize_event_document(document) for document in documents], "total": total}


@admin_router.post("/events/{event_id}/retry")
async def admin_retry_domain_event(event_id: str, request: Request):
    admin_user = await require_role("admin")(request)
    try:
        event = await retry_domain_event(event_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Event not found")
    await create_audit_log(
        str(admin_user.get("_id") or ""), admin_user.get("email", ""), "event_retry",
        "domain_event", event_id, {},
    )
    return event

# ========================
# EMAIL TEMPLATES (Admin)
# ========================
# Curated set of variables per category — exposed to the Admin UI as a
# reference panel. Categories mirror the `category` field on seeded templates.
_EMAIL_TEMPLATE_VARIABLES = {
    "layout":  ["app_url"],
    "partner": ["partner_name", "user_name", "user_email", "field_of_study",
                "bundesland", "step_order", "open_user_link", "app_url"],
    "user":    ["user_name", "partner_name", "milestone_title", "step_title",
                "rejection_reason", "reopened_step_title", "reset_link", "app_url"],
    "step":    ["user_name", "step_title", "step_order", "step_description",
                "total_steps", "partner_name", "app_url"],
}


@admin_router.get("/email-templates")
async def admin_list_email_templates(request: Request):
    await require_role("admin")(request)
    docs = await db.email_templates.find({}, {"_id": 0}).to_list(200)
    # Stable order: layout first, then grouped by category
    order = {"layout": 0, "partner": 1, "user": 2, "step": 3}
    docs.sort(key=lambda d: (order.get(d.get("category", "user"), 99), d.get("key", "")))
    return {"templates": docs, "variables": _EMAIL_TEMPLATE_VARIABLES}


@admin_router.get("/email-templates/{key}")
async def admin_get_email_template(key: str, request: Request):
    await require_role("admin")(request)
    doc = await db.email_templates.find_one({"key": key}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return doc


@admin_router.put("/email-templates/{key}")
async def admin_update_email_template(key: str, payload: dict, request: Request):
    admin_user = await require_role("admin")(request)
    existing = await db.email_templates.find_one({"key": key})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    allowed = {
        k: v for k, v in (payload or {}).items()
        if k in ("subject", "body_html", "notification_title", "notification_body", "description")
    }
    if not allowed:
        raise HTTPException(status_code=400, detail="No editable fields provided")
    allowed["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.email_templates.update_one({"key": key}, {"$set": allowed})
    await create_audit_log(admin_user["_id"], admin_user["email"], "email_template_update",
                           "email_template", key, {"fields": list(allowed.keys())})
    updated = await db.email_templates.find_one({"key": key}, {"_id": 0})
    return updated


@admin_router.post("/email-templates/{key}/reset")
async def admin_reset_email_template(key: str, request: Request):
    """Reset a single template back to the seeded default. Re-runs the seed
    logic for this specific key only."""
    admin_user = await require_role("admin")(request)
    if key not in DEFAULT_TEMPLATES:
        raise HTTPException(status_code=404, detail="No default for this template key")
    tpl = DEFAULT_TEMPLATES[key]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "key": key,
        "category": tpl.get("category", "user"),
        "subject": tpl["subject"],
        "body_html": tpl["body_html"],
        "notification_title": tpl.get("notification_title", ""),
        "notification_body": tpl.get("notification_body", ""),
        "description": tpl["description"],
        "updated_at": now,
    }
    await db.email_templates.update_one({"key": key}, {"$set": doc}, upsert=True)
    await create_audit_log(admin_user["_id"], admin_user["email"], "email_template_reset",
                           "email_template", key, {})
    return await db.email_templates.find_one({"key": key}, {"_id": 0})


class _EmailPreviewPayload(BaseModel):
    subject: Optional[str] = ""
    body_html: Optional[str] = ""
    variables: Optional[Dict[str, Any]] = None


class _NotificationPreviewPayload(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None


class _EmailTestSendPayload(BaseModel):
    subject: Optional[str] = ""
    body_html: Optional[str] = ""
    variables: Optional[Dict[str, Any]] = None
    recipients: List[str] = []


@admin_router.post("/email-templates/{key}/preview")
async def admin_preview_email_template(key: str, payload: _EmailPreviewPayload, request: Request):
    """Render header + body + footer with the supplied variables. The admin UI
    can send edited (unsaved) HTML/subject via `subject`/`body_html` overrides
    to see the live preview without persisting."""
    await require_role("admin")(request)
    rendered = await render_email(
        key,
        payload.variables or {},
        override_subject=payload.subject or "",
        override_body=payload.body_html or "",
    )
    if not rendered:
        raise HTTPException(status_code=404, detail="Template not found")
    return rendered


@admin_router.post("/email-templates/{key}/notification-preview")
async def admin_preview_notification(key: str, payload: _NotificationPreviewPayload, request: Request):
    """Render Browser/App copy independently from the email subject and HTML."""
    await require_role("admin")(request)
    rendered = await render_notification(
        key,
        payload.variables or {},
        override_title=payload.title,
        override_body=payload.body,
    )
    if not rendered:
        raise HTTPException(status_code=404, detail="Notification content not found")
    return rendered


@admin_router.post("/email-templates/{key}/send-test")
async def admin_send_test_email(key: str, payload: _EmailTestSendPayload, request: Request):
    """Render the template (with unsaved subject/body_html overrides + vars) and
    send to the admin's own email + any additional recipients supplied. Returns
    {sent:int, failed:list[{email,error}], recipients:list[str]}.

    SMTP may be unconfigured in preview envs — in that case send_email_sync
    returns {'status':'skipped'} and we count those as NOT sent so the admin
    sees a clear 'Mailgun not configured' toast."""
    admin_user = await require_role("admin")(request)
    rendered = await render_email(
        key,
        payload.variables or {},
        override_subject=payload.subject or "",
        override_body=payload.body_html or "",
    )
    if not rendered:
        raise HTTPException(status_code=404, detail="Template not found")

    # Build recipient list: admin's own email + comma-separated extras.
    recipients: list[str] = []
    seen: set[str] = set()
    admin_email = (admin_user.get("email") or "").strip()
    if admin_email:
        recipients.append(admin_email)
        seen.add(admin_email.lower())
    for r in payload.recipients or []:
        email = (r or "").strip()
        if not email or "@" not in email:
            continue
        if email.lower() in seen:
            continue
        seen.add(email.lower())
        recipients.append(email)

    if not recipients:
        raise HTTPException(status_code=400, detail="No valid recipients")

    sent, failed, skipped = 0, [], 0
    for r in recipients:
        try:
            result = await send_email_notification(r, rendered["subject"], rendered["html"])
            status = (result or {}).get("status")
            if status == "success":
                sent += 1
            elif status == "skipped":
                skipped += 1
            else:
                failed.append({"email": r, "error": (result or {}).get("error", "unknown")})
        except Exception as exc:
            failed.append({"email": r, "error": str(exc)})

    await create_audit_log(admin_user["_id"], admin_user["email"], "email_template_test_send",
                           "email_template", key,
                           {"recipients": recipients, "sent": sent, "failed": len(failed),
                            "skipped": skipped})
    return {
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "recipients": recipients,
        "smtp_configured": skipped == 0 or sent > 0 or len(failed) > 0,
    }

# ========================
# ROUTER ASSEMBLY
# ========================

api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(partner_router)
api_router.include_router(payment_router)
api_router.include_router(steps_router)
api_router.include_router(files_router)
api_router.include_router(cms_router)

@api_router.get("/")
async def root():
    return {"message": "IHCA API"}

app.include_router(api_router)

# CORS
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
cors_origins = [
    frontend_url,
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
if frontend_url.startswith("https://"):
    cors_origins.append(frontend_url.replace("https://", "http://"))
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ========================
# STARTUP / SHUTDOWN
# ========================

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.surveys.create_index("slug", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    # Reload hotpaths: all dashboard lists and metrics use these compound keys.
    await db.users.create_index([("role", 1), ("survey_id", 1)])
    await db.users.create_index("partner_id")
    await db.users.create_index([("role", 1), ("created_at", -1)])
    await db.surveys.create_index([("is_active", 1), ("is_default", 1)])
    await db.permission_groups.create_index("key", unique=True)
    await db.permission_groups.create_index("name_key", unique=True)
    await db.steps.create_index([("survey_id", 1), ("is_active", 1), ("order", 1)])
    await db.steps.create_index([("is_active", 1), ("order", 1)])
    await db.user_progress.create_index([("user_id", 1), ("step_id", 1)], unique=True)
    await db.user_progress.create_index([("user_id", 1), ("survey_id", 1)])
    await db.user_progress.create_index([("user_id", 1), ("step_order", 1)])
    await db.user_progress.create_index([("step_id", 1), ("status", 1)])
    await db.user_progress.create_index([("user_id", 1), ("status", 1), ("step_order", 1)])
    await db.partner_submissions.create_index([("partner_id", 1), ("user_id", 1)])
    await db.partner_submissions.create_index([("user_id", 1), ("partner_id", 1)])
    await db.partner_submissions.create_index([("user_id", 1), ("step_id", 1), ("partner_id", 1)], unique=True)
    await db.partner_submissions.create_index([("partner_id", 1), ("created_at", -1)])
    usage_indexes = await db.partner_usage_charges.index_information()
    legacy_usage_index = next((name for name, spec in usage_indexes.items() if spec.get("key") == [("partner_id", 1), ("user_id", 1)]), None)
    if legacy_usage_index:
        await db.partner_usage_charges.drop_index(legacy_usage_index)
    await db.partner_usage_charges.create_index([("partner_id", 1), ("user_id", 1), ("service_step_id", 1)], unique=True)
    await db.partner_usage_charges.create_index([("partner_id", 1), ("status", 1), ("created_at", -1)])
    await db.files.create_index("id", unique=True)
    await db.files.create_index([("user_id", 1), ("created_at", -1)])
    await db.partners.create_index("name")
    await db.partners.create_index([("is_active", 1), ("tags", 1)])
    await db.partners.create_index([("registration_status", 1), ("registered_at", -1)])
    await db.progress_history.create_index([("user_id", 1), ("timestamp", -1)])
    await db.audit_logs.create_index([("timestamp", -1)])
    try:
        init_storage()
    except Exception as e:
        logger.warning(f"Storage init failed: {e}")
    now = datetime.now(timezone.utc).isoformat()
    # Seed surveys and backfill existing single-survey data. The current medical
    # flow remains the default; Pflege is prepared for URL-scoped rollout.
    default_survey = await _get_default_survey()
    default_survey_id = str(default_survey["_id"])
    await db.cms_content.update_one(
        {"section": "landing_pages", "content.pages": {"$elemMatch": {"survey_slug": "aerzte", "path": "/"}}},
        {"$set": {"content.pages.$[page].path": "/aerzte"}},
        array_filters=[{"page.survey_slug": "aerzte", "page.path": "/"}],
    )
    if not await db.surveys.find_one({"slug": PFLEGE_SURVEY_SLUG}):
        await db.surveys.insert_one({
            "name": "FSP Pflege",
            "slug": PFLEGE_SURVEY_SLUG,
            "description": "Anerkennung, Fachsprache und Arbeitseinstieg fuer internationale Pflegekraefte in Deutschland.",
            "audience": "Internationale Pflegekraefte, Altenpflege, Gesundheits- und Krankenpflege",
            "is_active": True,
            "is_default": False,
            "theme": {
                "primary": "#004856",
                "secondary": "#7ed9c6",
                "accent": "#ff6b6b",
                "font_heading": "system-ui",
                "font_body": "system-ui",
                "logo_url": "/assets/gerdoctor-logo.svg",
                "icon_url": "/assets/gerdoctor-logo.svg",
            },
            "created_at": now,
            "updated_at": now,
        })
    await db.steps.update_many({"survey_id": {"$exists": False}}, {"$set": {"survey_id": default_survey_id}})
    await db.users.update_many({"role": "user", "survey_id": {"$exists": False}}, {"$set": {"survey_id": default_survey_id, "survey_slug": DEFAULT_SURVEY_SLUG}})
    await db.user_progress.update_many({"survey_id": {"$exists": False}}, {"$set": {"survey_id": default_survey_id}})
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_password), "name": "Admin", "role": "admin", "created_at": datetime.now(timezone.utc).isoformat()})
        await db.login_attempts.delete_many({"identifier": {"$regex": f":{admin_email}$"}})
        logger.info(f"Admin user created: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password), "role": "admin"}})
        await db.login_attempts.delete_many({"identifier": {"$regex": f":{admin_email}$"}})
        logger.info("Admin password updated")
    elif existing.get("role") != "admin":
        await db.users.update_one({"email": admin_email}, {"$set": {"role": "admin"}})
        logger.info("Admin role restored")
    created_permission_groups = await ensure_permission_groups()
    if created_permission_groups:
        logger.info("Created %s default permission group(s)", created_permission_groups)
    # Seed default steps if none
    if await db.steps.count_documents({}) == 0:
        doc_types = ["Visum", "Antrag auf Approbation", "Approbation", "Eingangsbescheinigung bei zustaendiger Behoerde", "Kenntnisspruefung"]
        default_steps = [
            {"title": "Persoenliche Daten", "description": "Fuellen Sie Ihre persoenlichen Informationen aus", "order": 1, "step_type": "form", "fields": [{"name": "name", "field_type": "text", "label": "Name", "placeholder": "Ihr Nachname", "required": True}, {"name": "first_name", "field_type": "text", "label": "Vorname", "placeholder": "Ihr Vorname", "required": True}, {"name": "phone", "field_type": "phone", "label": "Telefon", "placeholder": "+49 (0) 123 456 789", "required": True}, {"name": "address", "field_type": "text", "label": "Adresse", "placeholder": "Strasse und Hausnummer", "required": True}, {"name": "field_of_study", "field_type": "selectbox", "label": "Fachgebiet", "options": ["Allgemeinmedizin", "Innere Medizin", "Chirurgie", "Paediatrie", "Zahnmedizin", "HNO", "Dermatologie", "Neurologie", "Orthopaedie", "Gynaekologie", "Augenheilkunde", "Anaesthesiologie", "Radiologie", "Psychiatrie", "Urologie"], "required": True}, {"name": "documents", "field_type": "multiupload", "label": "Dokumente", "options": doc_types, "required": False}], "required_fields": ["name", "first_name", "phone", "address", "field_of_study"], "duration_value": 0, "duration_unit": "days", "email_on_leave": True, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"title": "Antragstellung Approbation", "description": "Waehlen Sie einen Partner fuer die Antragstellung", "order": 2, "step_type": "partner_selection", "fields": [], "filter_tag": "Antragstellung", "duration_value": 0, "duration_unit": "days", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"title": "Uebersicht Antragstellung Approbation", "description": "Status Ihrer Antragstellung", "order": 3, "step_type": "milestone", "fields": [], "duration_value": 4, "duration_unit": "weeks", "email_on_leave": True, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"title": "FaMed", "description": "Weiter zur FaMed-Pruefung", "order": 4, "step_type": "display", "fields": [], "action_label": "zur FaMed", "link_url": "https://famed-test.de/", "link_label": "famed-test.de besuchen", "duration_value": 0, "duration_unit": "days", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"title": "Service Kenntnisspruefung", "description": "Waehlen Sie einen Partner", "order": 5, "step_type": "partner_selection", "fields": [], "filter_tag": "Kenntnisspruefung", "duration_value": 0, "duration_unit": "days", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"title": "Meilenstein Kenntnisspruefung", "description": "Status Ihrer Kenntnisspruefung", "order": 6, "step_type": "milestone", "fields": [], "duration_value": 3, "duration_unit": "months", "email_on_leave": True, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"title": "Service Weiterbildung", "description": "Waehlen Sie einen Partner", "order": 7, "step_type": "partner_selection", "fields": [], "filter_tag": "Weiterbildung", "skippable": True, "skip_label": "Vorerst ueberspringen", "duration_value": 0, "duration_unit": "days", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"title": "Meilenstein Job finden", "description": "Hier koennen wir Ihnen helfen!", "order": 8, "step_type": "display", "fields": [], "duration_value": 2, "duration_unit": "weeks", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
        ]
        for step in default_steps:
            step["survey_id"] = default_survey_id
        await db.steps.insert_many(default_steps)
        logger.info("Default steps created")
    migrated_form_steps = await migrate_database_form_configs(db)
    if migrated_form_steps:
        logger.info("Form-builder schema applied to %s step(s)", migrated_form_steps)
    migrated_document_titles = await _migrate_document_workflow_titles()
    if migrated_document_titles:
        logger.info("Aligned %s document-workflow step title(s)", migrated_document_titles)
    # Seed partners if none
    if await db.partners.count_documents({}) == 0:
        await db.partners.insert_many([
            {"name": "ILS", "description": "Wir helfen bei allen Antraegen", "category": "Antragstellung", "tags": ["Antragstellung"], "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"name": "ILS2", "description": "Wir helfen bei Kenntnisspruefungen", "category": "Kenntnisspruefung", "tags": ["Kenntnisspruefung"], "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"name": "ILS3", "description": "Wir helfen bei Weiterbildungen", "category": "Weiterbildung", "tags": ["Weiterbildung"], "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
        ])
        logger.info("Sample partners created")
    # Seed CMS
    _default_cms = {
        "home": {
            "hero_title": "IHCA - dein persoenlicher Weg zum Facharzt in Deutschland",
            "hero_subtitle": "Von der Vorbereitung bis zum Arbeitseinstieg unterstuetzen wir vollumfaenglich",
            "hero_cta": "Jetzt starten",
            "box1_title": "Begleitetes Onboarding",
            "box1_description": "Schritt-für-Schritt durch den Anerkennungsprozess mit individueller Begleitung.",
            "box2_title": "Partner-Netzwerk",
            "box2_description": "Zugang zu geprüften Partnern für Approbation, Fachsprachenprüfung, Kenntnisprüfung und Weiterbildung.",
            "box3_title": "Fortschritts-Tracking",
            "box3_description": "Behalte jederzeit den Überblick - Meilensteine, Fristen und voraussichtliches Approbationsdatum.",
        },
        "about": {
            "title": "Ueber uns",
            "description": "Erhalte die Arbeitserlaubnis zum Praktizieren in Deutschland.",
            "mission": "Der einfache Weg zur deutschen Approbation",
        },
        "partners": {
            "title": "Unsere Partner unterstuetzen dich",
            "description": "Arbeiten Sie mit branchenfuehrenden Partnern zusammen.",
        },
        "landing_pages": {
            "pages": [
                {
                    "id": "aerzte",
                    "title": "Ärzte Anerkennung",
                    "path": "/aerzte",
                    "survey_slug": "aerzte",
                    "partner_tags": "Antragstellung,Kenntnisprüfung,Weiterbildung",
                    "eyebrow": "Praktizieren in Deutschland",
                    "hero_title": "IHCA - dein persoenlicher Weg zum Facharzt in Deutschland",
                    "hero_subtitle": "Von der Vorbereitung bis zum Arbeitseinstieg unterstuetzen wir vollumfaenglich",
                    "hero_cta": "Jetzt starten",
                    "learn_more_label": "Mehr erfahren",
                    "hero_image_url": "/assets/hero-journey.svg",
                    "stat_value": "100%",
                    "stat_label": "Der schnellste Weg zur Approbation",
                    "box1_title": "Begleitetes Onboarding",
                    "box1_description": "Schritt-für-Schritt durch den Anerkennungsprozess mit individueller Begleitung.",
                    "box2_title": "Partner-Netzwerk",
                    "box2_description": "Zugang zu geprüften Partnern für Approbation, Fachsprachenprüfung, Kenntnisprüfung und Weiterbildung.",
                    "box3_title": "Fortschritts-Tracking",
                    "box3_description": "Behalte jederzeit den Überblick - Meilensteine, Fristen und voraussichtliches Approbationsdatum.",
                    "about_eyebrow": "Who We Are",
                    "about_title": "Ueber uns",
                    "about_description": "Erhalte die Arbeitserlaubnis zum Praktizieren in Deutschland.",
                    "about_mission": "Der einfache Weg zur deutschen Approbation",
                    "partners_eyebrow": "Our Network",
                    "partners_title": "Unsere Partner unterstuetzen dich",
                    "partners_description": "Arbeiten Sie mit branchenfuehrenden Partnern zusammen.",
                    "cta_title": "Ready to Start Your Journey?",
                    "cta_description": "Create your account and follow a guided recognition process.",
                    "footer_text": "© 2026 FSP Pflege. Alle Rechte vorbehalten.",
                },
                {
                    "id": "pflege",
                    "title": "FSP Pflege",
                    "path": "/pflege",
                    "survey_slug": "pflege",
                    "partner_tags": "Pflege Sprachschulung,Pflege Anerkennung,Pflege Arbeitgeber",
                    "eyebrow": "Pflege in Deutschland",
                    "hero_title": "Anerkennung als Pflegefachkraft in Deutschland",
                    "hero_subtitle": "Wir begleiten internationale Pflegekräfte von Registrierung, Fachsprache und Anerkennung bis zum Arbeitseinstieg in Deutschland.",
                    "hero_cta": "Jetzt registrieren",
                    "learn_more_label": "Mehr zur Pflege-Anerkennung",
                    "hero_image_url": "/assets/hero-journey.svg",
                    "stat_value": "100%",
                    "stat_label": "Von der Anerkennung bis zum Pflegejob",
                    "box1_title": "Geführte Anerkennung",
                    "box1_description": "Alle Schritte von Unterlagen, Sprache und Bescheid bleiben sichtbar.",
                    "box2_title": "Partner für Sprache und Einstieg",
                    "box2_description": "Sprachschulen, Vorbereitungspartner und Arbeitgeber können passend eingebunden werden.",
                    "box3_title": "Planbarer Fortschritt",
                    "box3_description": "Nutzer sehen, was erledigt ist und welcher Schritt als nächstes ansteht.",
                    "about_eyebrow": "Für internationale Pflegekräfte",
                    "about_title": "Ihr Weg in die Pflege in Deutschland",
                    "about_description": "Die Plattform begleitet Pflegekräfte aus dem Ausland bei Registrierung, Fachsprache, Dokumenten und passenden nächsten Schritten.",
                    "about_mission": "Unser Ziel: ein verständlicher, planbarer und digital begleiteter Einstieg in den deutschen Pflegeberuf.",
                    "partners_eyebrow": "Partner & Vorbereitung",
                    "partners_title": "Unterstützung für Prüfung, Anerkennung und Einstieg",
                    "partners_description": "Pflege-Surveys können eigene Partner, Prüfungsorte und Vorbereitungsschritte erhalten.",
                    "cta_title": "Bereit für Ihren Pflegeweg in Deutschland?",
                    "cta_description": "Registrieren Sie sich und starten Sie den passenden Prozess für Anerkennung, Fachsprache und Arbeitseinstieg.",
                    "footer_text": "© 2026 FSP Pflege. Alle Rechte vorbehalten.",
                },
            ],
        },
    }
    _default_cms_en = {
        "home": {
            "hero_title": "IHCA - your personal path to becoming a medical specialist in Germany",
            "hero_subtitle": "From preparation to starting your career, we provide comprehensive support.",
            "hero_cta": "Get Started",
            "box1_title": "Guided Onboarding",
            "box1_description": "Step-by-step through the recognition process with personalised guidance.",
            "box2_title": "Partner Network",
            "box2_description": "Access to vetted partners for Approbation, language exam, knowledge exam and further training.",
            "box3_title": "Progress Tracking",
            "box3_description": "Stay on top of every milestone — deadlines and your expected Approbation date.",
        },
    }
    for section, defaults in _default_cms.items():
        existing = await db.cms_content.find_one({"section": section})
        if not existing:
            doc = {"section": section, "content": defaults, "created_at": datetime.now(timezone.utc).isoformat()}
            if section in _default_cms_en:
                doc["translations"] = {"en": _default_cms_en[section]}
            await db.cms_content.insert_one(doc)
        else:
            # Back-fill any missing keys so existing installs get new feature boxes
            content, translations = _normalize_cms_payload(
                existing.get("content"), existing.get("translations")
            )
            added = {k: v for k, v in defaults.items() if k not in content}
            update = {}
            if added or content != (existing.get("content") or {}):
                update["content"] = {**content, **added}
            if section in _default_cms_en:
                trans = translations
                en = trans.get("en") or {}
                added_en = {k: v for k, v in _default_cms_en[section].items() if k not in en}
                if added_en or trans != (existing.get("translations") or {}):
                    update["translations"] = {**trans, "en": {**en, **added_en}}
            if update:
                await db.cms_content.update_one({"section": section}, {"$set": update})
    # Seed site settings
    if not await db.site_settings.find_one({"_key": "global"}):
        await db.site_settings.insert_one({"_key": "global", "site_title": "IHCA", "logo_text": "IHCA", "logo_bold_part": "IH", "logo_light_part": "CA", "contact_email": "", "footer_text": "", "primary_color": "#114f55", "meta_description": "IHCA — international health connect association. Praktizieren in Deutschland.", "created_at": datetime.now(timezone.utc).isoformat()})
    # Seed email templates (idempotent — won't overwrite admin edits)
    try:
        _now = datetime.now(timezone.utc).isoformat()
        for _key, _tpl in DEFAULT_TEMPLATES.items():
            _existing = await db.email_templates.find_one({"key": _key})
            _doc = {
                "key": _key,
                "category": _tpl.get("category", "user"),
                "subject": _tpl["subject"],
                "body_html": _tpl["body_html"],
                "notification_title": _tpl.get("notification_title", ""),
                "notification_body": _tpl.get("notification_body", ""),
                "description": _tpl["description"],
                "updated_at": _now,
            }
            if _existing:
                _add = {k: v for k, v in _doc.items()
                        if k != "key" and (k not in _existing or _existing.get(k) in (None, ""))}
                if _add:
                    await db.email_templates.update_one({"key": _key}, {"$set": _add})
            else:
                _doc["created_at"] = _now
                await db.email_templates.insert_one(_doc)
    except Exception as _e:
        logger.warning(f"email_templates seed failed: {_e}")
    try:
        await ensure_event_configs()
    except Exception as _e:
        logger.warning(f"event config seed failed: {_e}")
    logger.info("Startup seeding complete")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
