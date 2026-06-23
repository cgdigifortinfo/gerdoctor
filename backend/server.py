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
import uuid
import asyncio
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId

# Shared modules
from database import db, client
from models import (
    UserRegister, UserLogin, ForgotPassword, ResetPassword, UserResponse, ProfileUpdate,
    PartnerCreate, PartnerUpdate, StepCreate, StepUpdate, StepReorder, StepFieldCreate,
    UserProgressUpdate, PartnerSubmissionCreate, MultiPartnerSubmission,
    CMSContentUpdate, NotificationPreferences, BulkRoleUpdate, AdminUserCreate, SiteSettingsUpdate,
    StepTemplateCreate, StepTemplateUpdate, PartnerSelfUpdate, StepLayoutBulk,
    SurveyCreate, SurveyUpdate
)
from auth import (
    get_jwt_secret, JWT_ALGORITHM, hash_password, verify_password,
    create_access_token, create_refresh_token, get_current_user, require_role
)
from helpers import (
    init_storage, put_object, get_object, APP_NAME,
    send_email_notification, create_audit_log, notify_partner_of_new_submission,
    notify_user_awaiting_partner, notify_user_milestone_completed,
    render_email, send_rendered_email, _partner_deep_link,
    calculate_completion_pct, calculate_estimated_completion, calculate_user_metrics,
    calculate_users_metrics,
    apply_auto_completes, _get_step_context,
    apply_anerkennungsstatus_skips
)
from email_template_defaults import DEFAULT_TEMPLATES

logger = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)

# ========================
# APP & ROUTERS
# ========================
app = FastAPI()

api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
partner_router = APIRouter(prefix="/partners", tags=["partners"])
steps_router = APIRouter(prefix="/steps", tags=["steps"])
files_router = APIRouter(prefix="/files", tags=["files"])
cms_router = APIRouter(prefix="/cms", tags=["cms"])

DEFAULT_SURVEY_SLUG = "aerzte"
PFLEGE_SURVEY_SLUG = "pflege"

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
    user_doc = {
        "email": email, "password_hash": hash_password(data.password),
        "name": data.name, "role": "user", "profile": {},
        "survey_id": survey_id, "survey_slug": survey.get("slug", DEFAULT_SURVEY_SLUG),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    steps = await db.steps.find(_step_query_for_survey(survey_id)).sort("order", 1).to_list(100)
    for step in steps:
        await db.user_progress.insert_one({
            "user_id": user_id, "step_id": str(step["_id"]),
            "survey_id": survey_id,
            "step_order": step.get("order"),
            "status": "pending", "data": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    access_token = create_access_token(user_id, email, "user")
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="access_token", value=access_token, **_auth_cookie_kwargs(7200))
    response.set_cookie(key="refresh_token", value=refresh_token, **_auth_cookie_kwargs(604800))
    return {"id": user_id, "email": email, "name": data.name, "role": "user", "survey_id": survey_id, "survey_slug": survey.get("slug"), "access_token": access_token}

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
    return {"id": user_id, "email": user["email"], "name": user["name"], "role": user["role"], "survey_id": user.get("survey_id"), "survey_slug": user.get("survey_slug"), "access_token": access_token}

@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}

@auth_router.get("/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return {"id": user["_id"], "email": user["email"], "name": user["name"], "role": user["role"], "profile": user.get("profile", {}), "survey_id": user.get("survey_id"), "survey_slug": user.get("survey_slug")}

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
    await db.password_reset_tokens.insert_one({
        "user_id": str(user["_id"]), "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(), "used": False
    })
    reset_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
    logger.info(f"Password reset link for {email}: {reset_link}")
    await send_rendered_email(email, "user_password_reset", {"reset_link": reset_link, "user_name": user.get("name", "")})
    return {"message": "If an account exists, a reset link has been sent"}

@auth_router.post("/reset-password")
async def reset_password(data: ResetPassword):
    token_doc = await db.password_reset_tokens.find_one({"token": data.token, "used": False})
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if datetime.fromisoformat(token_doc["expires_at"]) < datetime.now(timezone.utc):
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
    tid = str(target["_id"])
    access_token = create_access_token(tid, target["email"], target["role"])
    await create_audit_log(admin_user["_id"], admin_user["email"], "impersonate", "user", tid, {"target_email": target["email"]})
    return {"access_token": access_token, "user": {"id": tid, "email": target["email"], "name": target["name"], "role": target["role"], "survey_id": target.get("survey_id"), "survey_slug": target.get("survey_slug")}}

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
    metrics_task = calculate_user_metrics(user["_id"])
    steps, progress, history, settings, metrics = await asyncio.gather(
        steps_task, progress_task, history_task, settings_task, metrics_task,
    )
    progress_map = {row["step_id"]: row for row in progress}
    serialized_steps = [
        {**{key: value for key, value in step.items() if key != "_id"}, "id": str(step["_id"])}
        for step in steps
    ]
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

    if data.status == "completed" and not (data.data or {}).get("skipped"):
        required_fields = step.get("required_fields", [])
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
    partner = await db.partners.find_one({"_id": ObjectId(data.partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    existing = await db.partner_submissions.find_one({"user_id": user["_id"], "partner_id": data.partner_id})
    if existing:
        await db.partner_submissions.update_one({"user_id": user["_id"], "partner_id": data.partner_id}, {"$set": {"data": data.data, "status": "submitted", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"message": "Submission updated", "submission_id": existing["id"]}
    submission = {"id": str(uuid.uuid4()), "user_id": user["_id"], "user_email": user["email"], "user_name": user["name"], "partner_id": data.partner_id, "data": data.data, "status": "submitted", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.partner_submissions.insert_one(submission)
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
    results = []
    for pid in data.partner_ids:
        partner = await db.partners.find_one({"_id": ObjectId(pid)})
        if not partner:
            continue
        existing = await db.partner_submissions.find_one({"user_id": user["_id"], "partner_id": pid})
        if existing:
            await db.partner_submissions.update_one({"user_id": user["_id"], "partner_id": pid}, {"$set": {"data": data.data or {}, "status": "submitted", "updated_at": datetime.now(timezone.utc).isoformat()}})
            results.append(existing["id"])
        else:
            sub = {"id": str(uuid.uuid4()), "user_id": user["_id"], "user_email": user["email"], "user_name": user["name"], "partner_id": pid, "data": data.data or {}, "status": "submitted", "created_at": datetime.now(timezone.utc).isoformat()}
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
    return {"message": f"Submitted to {len(results)} partners", "submission_ids": results}

# ========================
# FILES ROUTES
# ========================

@files_router.post("/upload")
async def upload_file(file: UploadFile = File(...), request: Request = None):
    user = await get_current_user(request)
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{user['_id']}/{file_id}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    file_doc = {"id": file_id, "user_id": user["_id"], "storage_path": result["path"], "original_filename": file.filename, "content_type": file.content_type, "size": result.get("size", len(data)), "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.files.insert_one(file_doc)
    return {"id": file_id, "filename": file.filename, "path": result["path"]}

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
    data, content_type = get_object(file_doc["storage_path"])
    from fastapi.responses import Response as FastAPIResponse
    return FastAPIResponse(content=data, media_type=file_doc.get("content_type", content_type))

# ========================
# ADMIN ROUTES
# ========================

@admin_router.get("/users")
async def admin_get_users(request: Request):
    user = await require_role("admin")(request)
    users = await db.users.find({}, {"password_hash": 0}).to_list(1000)

    # Preload partners into a lookup {id_str: name}
    partner_docs = await db.partners.find({}, {"name": 1, "linked_user_ids": 1}).to_list(1000)
    partner_name_by_id = {str(p["_id"]): p.get("name", "") for p in partner_docs}
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
        # 1) Partner-role users: resolve their own partner_id → org name
        if u.get("role") == "partner" and u.get("partner_id"):
            pname = partner_name_by_id.get(u["partner_id"])
            if pname:
                partner_names.append(pname)
        # 2) Any user: partners that explicitly linked this user
        for pname in partners_by_linked_user.get(uid, []):
            if pname and pname not in partner_names:
                partner_names.append(pname)
        # 3) role=user: partners chosen via partner_selection progress data
        if u.get("role") == "user" and partner_step_ids:
            for pr in partner_progress_by_user.get(uid, []):
                data = pr.get("data") or {}
                pid = data.get("selected_partner_id")
                if pid and partner_name_by_id.get(pid):
                    name = partner_name_by_id[pid]
                    if name not in partner_names:
                        partner_names.append(name)
                for pid in (data.get("selected_partner_ids") or []):
                    if partner_name_by_id.get(pid):
                        name = partner_name_by_id[pid]
                        if name not in partner_names:
                            partner_names.append(name)
                # Fallback: some legacy/demo rows store only selected_partner_name
                pname = data.get("selected_partner_name")
                if pname and pname not in partner_names:
                    partner_names.append(pname)

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
            "pending_registrations": pending_registrations,
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
    return [{"id": str(u["_id"]), "email": u["email"], "name": u["name"], "role": u["role"], "created_at": u.get("created_at"), "partner_id": u.get("partner_id")} for u in users]

@admin_router.post("/users")
async def admin_create_user(data: AdminUserCreate, request: Request):
    admin_user = await require_role("admin")(request)
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
    }
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
    if data.role == "partner" and data.partner_id:
        await db.partners.update_one({"_id": ObjectId(data.partner_id)}, {"$set": {"user_id": uid}})
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
    return {"id": str(user["_id"]), "email": user["email"], "name": user["name"], "role": user["role"], "profile": user.get("profile", {}), "survey_id": user.get("survey_id"), "survey_slug": user.get("survey_slug"), "created_at": user.get("created_at"), "progress": progress, "submissions": submissions, "history": history, "completion_pct": await calculate_completion_pct(user_id)}

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
    await require_role("admin")(request)
    if data.role not in ["user", "admin", "partner"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    updated = 0
    for uid in data.user_ids:
        try:
            target = await db.users.find_one({"_id": ObjectId(uid)})
            if target and target["email"] == admin_email and data.role != "admin":
                continue
            result = await db.users.update_one({"_id": ObjectId(uid)}, {"$set": {"role": data.role}})
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
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if target and target["email"] == os.environ.get("ADMIN_EMAIL", "admin@example.com") and role != "admin":
        raise HTTPException(status_code=400, detail="Cannot change the primary admin's role")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": role}})
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
@admin_router.get("/steps")
async def admin_get_steps(request: Request, survey_id: Optional[str] = Query(None), survey_slug: Optional[str] = Query(None)):
    await require_role("admin")(request)
    query = {}
    if survey_slug:
        survey = await _get_survey_by_slug(survey_slug)
        query["survey_id"] = str(survey["_id"])
    elif survey_id:
        query["survey_id"] = survey_id
    steps = await db.steps.find(query).sort("order", 1).to_list(100)
    return [{"id": str(s["_id"]), "survey_id": s.get("survey_id", ""), "title": s["title"], "description": s["description"], "order": s["order"], "step_type": s["step_type"], "fields": s.get("fields", []), "filter_tag": s.get("filter_tag", ""), "skippable": s.get("skippable", False), "skip_label": s.get("skip_label", ""), "action_label": s.get("action_label", ""), "pending_message": s.get("pending_message", ""), "complete_message": s.get("complete_message", ""), "required_fields": s.get("required_fields", []), "required_uploads": s.get("required_uploads", []), "field_mappings": s.get("field_mappings", []), "conditions": s.get("conditions", []), "email_on_enter": s.get("email_on_enter", False), "email_on_edit": s.get("email_on_edit", False), "email_on_leave": s.get("email_on_leave", False), "email_subject_enter": s.get("email_subject_enter", ""), "email_body_enter": s.get("email_body_enter", ""), "email_subject_edit": s.get("email_subject_edit", ""), "email_body_edit": s.get("email_body_edit", ""), "email_subject_leave": s.get("email_subject_leave", ""), "email_body_leave": s.get("email_body_leave", ""), "is_active": s.get("is_active", True), "duration_value": s.get("duration_value", 0), "duration_unit": s.get("duration_unit", "days"), "translations": s.get("translations", {}), "flow_position": s.get("flow_position")} for s in steps]

@admin_router.post("/steps")
async def admin_create_step(data: StepCreate, request: Request):
    await require_role("admin")(request)
    survey_id = data.survey_id or str((await _get_default_survey())["_id"])
    step_doc = {"survey_id": survey_id, "title": data.title, "description": data.description, "order": data.order, "step_type": data.step_type, "fields": [f.model_dump() for f in data.fields] if data.fields else [], "filter_tag": data.filter_tag or "", "skippable": data.skippable, "skip_label": data.skip_label or "", "action_label": data.action_label or "", "pending_message": data.pending_message or "", "complete_message": data.complete_message or "", "required_fields": data.required_fields or [], "required_uploads": data.required_uploads or [], "field_mappings": data.field_mappings or [], "conditions": data.conditions or [], "email_on_enter": data.email_on_enter, "email_on_edit": data.email_on_edit, "email_on_leave": data.email_on_leave, "email_subject_enter": data.email_subject_enter or "", "email_body_enter": data.email_body_enter or "", "email_subject_edit": data.email_subject_edit or "", "email_body_edit": data.email_body_edit or "", "email_subject_leave": data.email_subject_leave or "", "email_body_leave": data.email_body_leave or "", "duration_value": data.duration_value, "duration_unit": data.duration_unit, "translations": data.translations or {}, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
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
    for sid, pos in (data.positions or {}).items():
        if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
            continue
        try:
            await db.steps.update_one(
                {"_id": ObjectId(sid)},
                {"$set": {"flow_position": {"x": float(pos["x"]), "y": float(pos["y"])},
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
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "fields" in update_data and update_data["fields"]:
        update_data["fields"] = [f if isinstance(f, dict) else f.model_dump() for f in update_data["fields"]]
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.steps.update_one({"_id": ObjectId(step_id)}, {"$set": update_data})
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
    partners = await db.partners.find().to_list(100)
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
        })
    return result

@admin_router.post("/partners")
async def admin_create_partner(data: PartnerCreate, request: Request):
    admin_user = await require_role("admin")(request)
    partner_doc = {"name": data.name, "description": data.description, "logo_url": data.logo_url, "website": data.website, "contact_email": data.contact_email, "category": data.category, "tags": data.tags or [], "linked_user_ids": data.linked_user_ids or [], "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
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
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$set": update_data})
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
    for pu in partner_users:
        await db.users.update_one({"_id": pu["_id"]}, {"$set": {"role": "user"}, "$unset": {"partner_id": ""}})
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
        await db.users.update_one({"_id": ObjectId(old_user_id)}, {"$set": {"role": "user"}, "$unset": {"partner_id": ""}})
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$set": {"user_id": user_id}})
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": "partner", "partner_id": partner_id}})
    return {"message": "Partner linked to user", "user_name": target_user["name"]}

@admin_router.put("/partners/{partner_id}/unlink-user")
async def admin_unlink_partner_user(partner_id: str, request: Request):
    await require_role("admin")(request)
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    old_user_id = partner.get("user_id")
    if old_user_id:
        await db.users.update_one({"_id": ObjectId(old_user_id)}, {"$set": {"role": "user"}, "$unset": {"partner_id": ""}})
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
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.audit_logs.count_documents(query)
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
    }

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

    # Group counts by user's step-1 profile data
    step1 = await db.steps.find_one({"order": 1, "is_active": True})
    step1_id = str(step1["_id"]) if step1 else None
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
    if step1_id and target_user_ids:
        async for row in db.user_progress.find({
            "user_id": {"$in": list(target_user_ids)}, "step_id": step1_id,
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


@api_router.get("/partner/submissions")
async def get_partner_submissions(request: Request):
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    partner_name = (partner or {}).get("name") or ""
    linked_user_ids = set(partner.get("linked_user_ids", [])) if partner else set()
    submissions = await db.partner_submissions.find({"partner_id": partner_id}, {"_id": 0}).to_list(1000)
    step1 = await db.steps.find_one({"order": 1, "is_active": True})
    seen_user_ids = {sub.get("user_id") for sub in submissions if sub.get("user_id")}
    target_user_ids = seen_user_ids | linked_user_ids
    metrics_by_user = await calculate_users_metrics(list(target_user_ids))
    work_by_user = await _partner_work_status_for_users(
        list(target_user_ids), partner_id, partner_name,
    )
    step1_by_user = {}
    if step1 and target_user_ids:
        async for row in db.user_progress.find({
            "user_id": {"$in": list(target_user_ids)},
            "step_id": str(step1["_id"]),
        }, {"user_id": 1, "data": 1}):
            step1_by_user[row["user_id"]] = row.get("data") or {}
    for sub in submissions:
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
            "user_id": uid, "user_name": u["name"], "user_email": u["email"],
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
    step1 = await db.steps.find_one({"order": 1, "is_active": True})
    other_users = [u for u in all_users if str(u["_id"]) not in my_user_ids]
    other_ids = [str(u["_id"]) for u in other_users]
    metrics_by_user = await calculate_users_metrics(other_ids)
    step1_by_user = {}
    if step1 and other_ids:
        async for row in db.user_progress.find({
            "user_id": {"$in": other_ids}, "step_id": str(step1["_id"]),
        }, {"user_id": 1, "data": 1}):
            step1_by_user[row["user_id"]] = row.get("data") or {}
    result = []
    for u in other_users:
        uid = str(u["_id"])
        s1data = step1_by_user.get(uid, {})
        metrics = metrics_by_user.get(uid, {})
        result.append({"user_id": uid, "user_name": u["name"], "user_email": u["email"], "completion_pct": metrics.get("completion_pct", 0), "estimated_completion": metrics.get("estimated_completion"), "field_of_study": s1data.get("fachrichtung_gewuenscht") or s1data.get("fachrichtung_praktiziert") or s1data.get("field_of_study", ""), "bundesland": s1data.get("anerkennungsverfahren_bundesland", ""), "created_at": u.get("created_at", "")})
    return result

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
    all_steps = []
    async for s in db.steps.find({"is_active": True}).sort("order", 1):
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
    progress_by_step_id = {p.get("step_id"): p for p in progress}
    managed: list[str] = []

    for s in all_steps:
        if s.get("step_type") not in ("partner_selection", "partner_multiselection"):
            continue
        pr = progress_by_step_id.get(s["id"]) or {}
        d = pr.get("data") or {}
        picks = set()
        if d.get("selected_partner_id"):
            picks.add(str(d["selected_partner_id"]))
        for pid in (d.get("selected_partner_ids") or []):
            picks.add(str(pid))
        name_match = (d.get("selected_partner_name") == partner_name) and bool(partner_name)
        # For multi-partner, match against partner tag on the step (only this partner's tag steps)
        if str(partner_id) in picks or name_match:
            managed.append(s["id"])
            # Walk forward in order to find the next milestone step in the same block
            for nxt in all_steps:
                if nxt["order"] <= s["order"]:
                    continue
                if nxt.get("step_type") == "milestone":
                    managed.append(nxt["id"])
                    break
                # stop at the next decision → means we left this block
                if nxt.get("step_type") == "decision":
                    break

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
        "id": str(target_user["_id"]), "email": target_user["email"],
        "name": target_user["name"], "progress": sanitized_progress,
        "steps": all_steps,
        "completion_pct": await calculate_completion_pct(user_id),
        "partner_step_id": partner_step_id,
        "partner_managed_step_ids": managed,
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
    admin_user = await require_role("admin")(request)
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
    return settings or {}

@admin_router.put("/settings")
async def admin_update_settings(data: SiteSettingsUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.site_settings.update_one({"_key": "global"}, {"$set": update_data}, upsert=True)
    await create_audit_log(admin_user["_id"], admin_user["email"], "settings_update", "settings", "", update_data)
    return {"message": "Settings updated"}

@api_router.get("/settings/public")
async def get_public_settings():
    settings = await db.site_settings.find_one({"_key": "global"}, {"_id": 0, "_key": 0})
    return settings or {}

# ========================
# EMAIL TEMPLATES (Admin)
# ========================
# Curated set of variables per category — exposed to the Admin UI as a
# reference panel. Categories mirror the `category` field on seeded templates.
_EMAIL_TEMPLATE_VARIABLES = {
    "layout":  ["app_url"],
    "partner": ["partner_name", "user_name", "user_email", "field_of_study",
                "bundesland", "step_order", "open_user_link", "app_url"],
    "user":    ["user_name", "partner_name", "milestone_title", "reset_link", "app_url"],
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
    allowed = {k: v for k, v in (payload or {}).items() if k in ("subject", "body_html", "description")}
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
api_router.include_router(steps_router)
api_router.include_router(files_router)
api_router.include_router(cms_router)

@api_router.get("/")
async def root():
    return {"message": "IHCA API"}

app.include_router(api_router)

# CORS
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
cors_origins = [frontend_url, "http://localhost:3000"]
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
    await db.steps.create_index([("survey_id", 1), ("is_active", 1), ("order", 1)])
    await db.steps.create_index([("is_active", 1), ("order", 1)])
    await db.user_progress.create_index([("user_id", 1), ("step_id", 1)], unique=True)
    await db.user_progress.create_index([("user_id", 1), ("survey_id", 1)])
    await db.user_progress.create_index([("step_id", 1), ("status", 1)])
    await db.user_progress.create_index([("user_id", 1), ("status", 1), ("step_order", 1)])
    await db.partner_submissions.create_index([("partner_id", 1), ("user_id", 1)])
    await db.partner_submissions.create_index([("user_id", 1), ("partner_id", 1)])
    await db.partner_submissions.create_index([("partner_id", 1), ("created_at", -1)])
    await db.files.create_index("id", unique=True)
    await db.partners.create_index("name")
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
                "font_heading": "Varela Round",
                "font_body": "Montserrat",
                "logo_url": "https://fsp-pflege.de/wp-content/uploads/2025/02/FSPP-Logo-Final.png",
                "icon_url": "https://fsp-pflege.de/wp-content/uploads/2025/03/FSPP-Icon-Vektor.svg",
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
                    "path": "/",
                    "survey_slug": "aerzte",
                    "partner_tags": "Antragstellung,Kenntnisprüfung,Weiterbildung",
                    "eyebrow": "Praktizieren in Deutschland",
                    "hero_title": "IHCA - dein persoenlicher Weg zum Facharzt in Deutschland",
                    "hero_subtitle": "Von der Vorbereitung bis zum Arbeitseinstieg unterstuetzen wir vollumfaenglich",
                    "hero_cta": "Jetzt starten",
                    "learn_more_label": "Mehr erfahren",
                    "hero_image_url": "https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/5fd3c87e94b794ef345545f4831b1564009ab10cecdbca63c977b897e96e5b8a.png",
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
                    "hero_image_url": "https://static.prod-images.emergentagent.com/jobs/315e3c10-27eb-4e13-8f67-587e823053ba/images/5fd3c87e94b794ef345545f4831b1564009ab10cecdbca63c977b897e96e5b8a.png",
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
    logger.info("Startup seeding complete")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
