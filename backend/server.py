"""
GERdoctor API - Main application entry point.
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
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId

# Shared modules
from database import db, client
from models import (
    UserRegister, UserLogin, ForgotPassword, ResetPassword, UserResponse, ProfileUpdate,
    PartnerCreate, PartnerUpdate, StepCreate, StepUpdate, StepReorder, StepFieldCreate,
    UserProgressUpdate, PartnerSubmissionCreate, MultiPartnerSubmission,
    CMSContentUpdate, NotificationPreferences, BulkRoleUpdate, AdminUserCreate, SiteSettingsUpdate
)
from auth import (
    get_jwt_secret, JWT_ALGORITHM, hash_password, verify_password,
    create_access_token, create_refresh_token, get_current_user, require_role
)
from helpers import (
    init_storage, put_object, get_object, APP_NAME,
    send_email_notification, create_audit_log,
    calculate_completion_pct, calculate_estimated_completion
)

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

# ========================
# AUTH ROUTES
# ========================

@auth_router.post("/register")
async def register(data: UserRegister, response: Response):
    email = data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_doc = {
        "email": email, "password_hash": hash_password(data.password),
        "name": data.name, "role": "user", "profile": {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    for step in steps:
        await db.user_progress.insert_one({
            "user_id": user_id, "step_id": str(step["_id"]),
            "status": "pending", "data": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    access_token = create_access_token(user_id, email, "user")
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=7200, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    return {"id": user_id, "email": email, "name": data.name, "role": "user", "access_token": access_token}

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
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=7200, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    return {"id": user_id, "email": user["email"], "name": user["name"], "role": user["role"], "access_token": access_token}

@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}

@auth_router.get("/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return {"id": user["_id"], "email": user["email"], "name": user["name"], "role": user["role"], "profile": user.get("profile", {})}

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
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=7200, path="/")
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
    await send_email_notification(email, "Password Reset Request", f"<p>Click <a href='{reset_link}'>here</a> to reset your password. This link expires in 1 hour.</p>")
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
    return {"access_token": access_token, "user": {"id": tid, "email": target["email"], "name": target["name"], "role": target["role"]}}

# ========================
# USER PROFILE ROUTES
# ========================

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
async def get_steps(request: Request):
    user = await get_current_user(request)
    steps = await db.steps.find({"is_active": True}, {"_id": 0}).sort("order", 1).to_list(100)
    all_steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    for i, step in enumerate(steps):
        step["id"] = str(all_steps[i]["_id"])
    return steps

@steps_router.get("/progress")
async def get_user_progress(request: Request):
    user = await get_current_user(request)
    return await db.user_progress.find({"user_id": user["_id"]}, {"_id": 0}).to_list(100)

@steps_router.get("/all-data")
async def get_all_step_data(request: Request):
    user = await get_current_user(request)
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    progress = await db.user_progress.find({"user_id": user["_id"]}, {"_id": 0}).to_list(100)
    progress_map = {p["step_id"]: p for p in progress}
    return [{
        "step_id": str(s["_id"]), "order": s["order"], "title": s["title"],
        "step_type": s["step_type"], "status": progress_map.get(str(s["_id"]), {}).get("status", "pending"),
        "data": progress_map.get(str(s["_id"]), {}).get("data", {}),
        "conditions": s.get("conditions", []), "field_mappings": s.get("field_mappings", []),
        "required_fields": s.get("required_fields", []), "required_uploads": s.get("required_uploads", [])
    } for s in steps]

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

    user_prefs = user.get("notification_preferences", {"email_on_step_enter": True, "email_on_step_edit": False, "email_on_step_leave": True})
    def render_template(template, variables):
        result = template
        for key, val in variables.items():
            result = result.replace(f'{{{{{key}}}}}', str(val))
        return result
    email_vars = {"user_name": user["name"], "user_email": user["email"], "step_title": step["title"], "step_order": step["order"], "step_description": step["description"]}
    if existing and step.get("email_on_edit") and data.data and user_prefs.get("email_on_step_edit", False):
        await send_email_notification(user["email"], render_template(step.get("email_subject_edit") or "Schritt aktualisiert: {{step_title}}", email_vars), render_template(step.get("email_body_edit") or "<p>Hallo {{user_name}},</p><p>Sie haben Ihren Fortschritt im Schritt <strong>{{step_title}}</strong> aktualisiert.</p>", email_vars))
    if not existing and step.get("email_on_enter") and user_prefs.get("email_on_step_enter", True):
        await send_email_notification(user["email"], render_template(step.get("email_subject_enter") or "Schritt gestartet: {{step_title}}", email_vars), render_template(step.get("email_body_enter") or "<p>Hallo {{user_name}},</p><p>Sie haben den Schritt <strong>{{step_title}}</strong> begonnen.</p>", email_vars))
    if data.status == "completed" and step.get("email_on_leave") and user_prefs.get("email_on_step_leave", True):
        await send_email_notification(user["email"], render_template(step.get("email_subject_leave") or "Schritt abgeschlossen: {{step_title}}", email_vars), render_template(step.get("email_body_leave") or "<p>Hallo {{user_name}},</p><p>Herzlichen Glueckwunsch! Sie haben den Schritt <strong>{{step_title}}</strong> abgeschlossen.</p>", email_vars))

    now_iso = datetime.now(timezone.utc).isoformat()
    update_fields = {"status": data.status, "data": data.data or {}, "updated_at": now_iso}
    if (not existing or not existing.get("started_at")) and data.status in ("in_progress", "completed"):
        update_fields["started_at"] = now_iso
    if data.status == "completed":
        update_fields["completed_at"] = now_iso
    await db.user_progress.update_one({"user_id": user["_id"], "step_id": data.step_id}, {"$set": update_fields}, upsert=True)
    await db.progress_history.insert_one({"user_id": user["_id"], "step_id": data.step_id, "step_title": step["title"], "step_order": step["order"], "action": data.status, "timestamp": now_iso})
    return {"message": "Progress updated"}

@steps_router.get("/history")
async def get_user_history(request: Request):
    user = await get_current_user(request)
    return await db.progress_history.find({"user_id": user["_id"]}, {"_id": 0}).sort("timestamp", -1).to_list(200)

@steps_router.get("/estimated-completion")
async def get_estimated_completion(request: Request):
    user = await get_current_user(request)
    return {"estimated_completion": await calculate_estimated_completion(user["_id"])}

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
    result = []
    for u in users:
        uid = str(u["_id"])
        result.append({"id": uid, "email": u["email"], "name": u["name"], "role": u["role"], "created_at": u.get("created_at"), "completion_pct": await calculate_completion_pct(uid), "estimated_completion": await calculate_estimated_completion(uid)})
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
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_doc = {"email": data.email, "password_hash": bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode(), "name": data.name, "role": data.role, "profile": {}, "created_at": datetime.now(timezone.utc).isoformat()}
    if data.partner_id:
        user_doc["partner_id"] = data.partner_id
    result = await db.users.insert_one(user_doc)
    uid = str(result.inserted_id)
    if data.role == "partner" and data.partner_id:
        await db.partners.update_one({"_id": ObjectId(data.partner_id)}, {"$set": {"user_id": uid}})
    await create_audit_log(admin_user["_id"], admin_user["email"], "user_create", "user", uid, {"email": data.email, "role": data.role})
    return {"id": uid, "message": "User created"}

@admin_router.get("/users/{user_id}")
async def admin_get_user(user_id: str, request: Request):
    await require_role("admin")(request)
    user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    submissions = await db.partner_submissions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    history = await db.progress_history.find({"user_id": user_id}, {"_id": 0}).sort("timestamp", -1).to_list(200)
    return {"id": str(user["_id"]), "email": user["email"], "name": user["name"], "role": user["role"], "profile": user.get("profile", {}), "created_at": user.get("created_at"), "progress": progress, "submissions": submissions, "history": history, "completion_pct": await calculate_completion_pct(user_id)}

@admin_router.put("/users/{user_id}/progress")
async def admin_update_user_progress(user_id: str, data: UserProgressUpdate, request: Request):
    await require_role("admin")(request)
    await db.user_progress.update_one({"user_id": user_id, "step_id": data.step_id}, {"$set": {"status": data.status, "data": data.data or {}, "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
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

# Admin Steps
@admin_router.get("/steps")
async def admin_get_steps(request: Request):
    await require_role("admin")(request)
    steps = await db.steps.find().sort("order", 1).to_list(100)
    return [{"id": str(s["_id"]), "title": s["title"], "description": s["description"], "order": s["order"], "step_type": s["step_type"], "fields": s.get("fields", []), "filter_tag": s.get("filter_tag", ""), "skippable": s.get("skippable", False), "skip_label": s.get("skip_label", ""), "action_label": s.get("action_label", ""), "pending_message": s.get("pending_message", ""), "complete_message": s.get("complete_message", ""), "required_fields": s.get("required_fields", []), "required_uploads": s.get("required_uploads", []), "field_mappings": s.get("field_mappings", []), "conditions": s.get("conditions", []), "email_on_enter": s.get("email_on_enter", False), "email_on_edit": s.get("email_on_edit", False), "email_on_leave": s.get("email_on_leave", False), "email_subject_enter": s.get("email_subject_enter", ""), "email_body_enter": s.get("email_body_enter", ""), "email_subject_edit": s.get("email_subject_edit", ""), "email_body_edit": s.get("email_body_edit", ""), "email_subject_leave": s.get("email_subject_leave", ""), "email_body_leave": s.get("email_body_leave", ""), "is_active": s.get("is_active", True), "duration_value": s.get("duration_value", 0), "duration_unit": s.get("duration_unit", "days")} for s in steps]

@admin_router.post("/steps")
async def admin_create_step(data: StepCreate, request: Request):
    await require_role("admin")(request)
    step_doc = {"title": data.title, "description": data.description, "order": data.order, "step_type": data.step_type, "fields": [f.model_dump() for f in data.fields] if data.fields else [], "filter_tag": data.filter_tag or "", "skippable": data.skippable, "skip_label": data.skip_label or "", "action_label": data.action_label or "", "pending_message": data.pending_message or "", "complete_message": data.complete_message or "", "required_fields": data.required_fields or [], "required_uploads": data.required_uploads or [], "field_mappings": data.field_mappings or [], "conditions": data.conditions or [], "email_on_enter": data.email_on_enter, "email_on_edit": data.email_on_edit, "email_on_leave": data.email_on_leave, "email_subject_enter": data.email_subject_enter or "", "email_body_enter": data.email_body_enter or "", "email_subject_edit": data.email_subject_edit or "", "email_body_edit": data.email_body_edit or "", "email_subject_leave": data.email_subject_leave or "", "email_body_leave": data.email_body_leave or "", "duration_value": data.duration_value, "duration_unit": data.duration_unit, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
    result = await db.steps.insert_one(step_doc)
    admin_user = await get_current_user(request)
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_create", "step", str(result.inserted_id), {"title": data.title})
    return {"id": str(result.inserted_id), "message": "Step created"}

@admin_router.put("/steps/reorder")
async def admin_reorder_steps(data: StepReorder, request: Request):
    admin_user = await require_role("admin")(request)
    for idx, step_id in enumerate(data.step_ids):
        await db.steps.update_one({"_id": ObjectId(step_id)}, {"$set": {"order": idx + 1}})
    await create_audit_log(admin_user["_id"], admin_user["email"], "steps_reorder", "step", "", {"new_order": data.step_ids})
    return {"message": "Steps reordered"}

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
    result = []
    for p in partners:
        pid = str(p["_id"])
        dashboard_user = await db.users.find_one({"partner_id": pid}, {"_id": 1, "name": 1, "email": 1})
        linked_ids = p.get("linked_user_ids", [])
        linked_users = []
        for uid in linked_ids:
            try:
                u = await db.users.find_one({"_id": ObjectId(uid)}, {"_id": 1, "name": 1, "email": 1})
                if u:
                    linked_users.append({"id": str(u["_id"]), "name": u["name"], "email": u["email"]})
            except Exception:
                pass
        if dashboard_user:
            du_id = str(dashboard_user["_id"])
            if du_id not in linked_ids:
                linked_users.insert(0, {"id": du_id, "name": dashboard_user["name"], "email": dashboard_user["email"]})
        result.append({"id": pid, "name": p["name"], "description": p.get("description", ""), "logo_url": p.get("logo_url"), "website": p.get("website"), "contact_email": p.get("contact_email"), "category": p.get("category"), "tags": p.get("tags", []), "is_active": p.get("is_active", True), "user_id": p.get("user_id"), "linked_users": linked_users, "linked_user_ids": linked_ids})
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
    return {"name": user["name"], "email": user["email"], "partner_name": partner["name"] if partner else None, "partner_id": partner_id}

@api_router.put("/partner/profile")
async def update_partner_profile(data: ProfileUpdate, request: Request):
    user = await require_role("partner")(request)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "name" in update_data:
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"name": update_data.pop("name")}})
    if update_data:
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {f"profile.{k}": v for k, v in update_data.items()}})
    return {"message": "Profile updated"}


@api_router.get("/partner/submissions")
async def get_partner_submissions(request: Request):
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    linked_user_ids = set(partner.get("linked_user_ids", [])) if partner else set()
    submissions = await db.partner_submissions.find({"partner_id": partner_id}, {"_id": 0}).to_list(1000)
    step1 = await db.steps.find_one({"order": 1, "is_active": True})
    seen_user_ids = set()
    for sub in submissions:
        uid = sub.get("user_id")
        if uid:
            seen_user_ids.add(uid)
            sub["estimated_completion"] = await calculate_estimated_completion(uid)
            sub["completion_pct"] = await calculate_completion_pct(uid)
            if step1:
                prog = await db.user_progress.find_one({"user_id": uid, "step_id": str(step1["_id"])})
                sub["field_of_study"] = prog.get("data", {}).get("field_of_study", "") if prog else ""
            else:
                sub["field_of_study"] = ""
    for uid in linked_user_ids:
        if uid in seen_user_ids:
            continue
        u = await db.users.find_one({"_id": ObjectId(uid)}, {"password_hash": 0})
        if not u or u.get("role") == "admin":
            continue
        field_of_study = ""
        if step1:
            prog = await db.user_progress.find_one({"user_id": uid, "step_id": str(step1["_id"])})
            field_of_study = prog.get("data", {}).get("field_of_study", "") if prog else ""
        submissions.append({"user_id": uid, "user_name": u["name"], "user_email": u["email"], "partner_id": partner_id, "data": {"source": "linked"}, "status": "linked", "completion_pct": await calculate_completion_pct(uid), "estimated_completion": await calculate_estimated_completion(uid), "field_of_study": field_of_study})
        seen_user_ids.add(uid)
    return submissions

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
    result = []
    for u in all_users:
        uid = str(u["_id"])
        if uid in my_user_ids:
            continue
        field_of_study = ""
        if step1:
            prog = await db.user_progress.find_one({"user_id": uid, "step_id": str(step1["_id"])})
            field_of_study = prog.get("data", {}).get("field_of_study", "") if prog else ""
        result.append({"user_id": uid, "user_name": u["name"], "user_email": u["email"], "completion_pct": await calculate_completion_pct(uid), "estimated_completion": await calculate_estimated_completion(uid), "field_of_study": field_of_study, "created_at": u.get("created_at", "")})
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
    sanitized_progress = []
    for p in progress:
        step = next((s for s in all_steps if s["id"] == p.get("step_id")), None)
        if step and step.get("step_type") in ("partner_selection", "partner_multiselection"):
            data = p.get("data", {})
            if data.get("selected_partner_id") and data["selected_partner_id"] != partner_id:
                sanitized_progress.append({**p, "data": {}})
                continue
        sanitized_progress.append(p)
    return {"id": str(target_user["_id"]), "email": target_user["email"], "name": target_user["name"], "progress": sanitized_progress, "steps": all_steps, "completion_pct": await calculate_completion_pct(user_id), "partner_step_id": partner_step_id}

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
    if data.status == "completed":
        user_prefs = target_user.get("notification_preferences", {"email_on_step_enter": True, "email_on_step_edit": False, "email_on_step_leave": True})
        partner_name = partner_doc.get("name", "") if partner_doc else ""
        def render_template(template, variables):
            result = template
            for key, val in variables.items():
                result = result.replace(f'{{{{{key}}}}}', str(val))
            return result
        email_vars = {"user_name": target_user["name"], "user_email": target_user["email"], "step_title": step["title"], "step_order": step["order"], "step_description": step.get("description", ""), "partner_name": partner_name}
        if step.get("email_on_leave") and user_prefs.get("email_on_step_leave", True):
            await send_email_notification(target_user["email"], render_template(step.get("email_subject_leave") or "Schritt abgeschlossen: {{step_title}}", email_vars), render_template(step.get("email_body_leave") or "<p>Hallo {{user_name}},</p><p>Ihr Schritt <strong>{{step_title}}</strong> wurde von {{partner_name}} abgeschlossen.</p>", email_vars))
            logger.info(f"Step completion email sent to {target_user['email']} for step '{step['title']}' by partner {partner_name}")
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
                if next_step.get("email_on_enter") and user_prefs.get("email_on_step_enter", True):
                    next_vars = {**email_vars, "step_title": next_step["title"], "step_order": next_step["order"]}
                    await send_email_notification(target_user["email"], render_template(next_step.get("email_subject_enter") or "Naechster Schritt: {{step_title}}", next_vars), render_template(next_step.get("email_body_enter") or "<p>Hallo {{user_name}},</p><p>Ihr naechster Schritt <strong>{{step_title}}</strong> ist jetzt freigeschaltet.</p>", next_vars))
    return {"message": "User progress updated"}

@api_router.get("/users/{user_id}/estimated-completion")
async def get_user_estimated_completion(user_id: str, request: Request):
    await require_role("admin", "partner")(request)
    return {"estimated_completion": await calculate_estimated_completion(user_id)}

# ========================
# CMS ROUTES
# ========================

@cms_router.get("")
async def get_cms_content():
    content = await db.cms_content.find({}, {"_id": 0}).to_list(100)
    return {c["section"]: c.get("content", {}) for c in content}

@cms_router.get("/{section}")
async def get_cms_section(section: str):
    content = await db.cms_content.find_one({"section": section}, {"_id": 0})
    return content.get("content", {}) if content else {}

@cms_router.put("/{section}")
async def update_cms_content(section: str, data: CMSContentUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    await db.cms_content.update_one({"section": section}, {"$set": {"section": section, "content": data.content, "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    await create_audit_log(admin_user["_id"], admin_user["email"], "cms_update", "cms", section, {"section": section})
    return {"message": "Content updated"}

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
    return {"message": "GERdoctor API"}

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
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    try:
        init_storage()
    except Exception as e:
        logger.warning(f"Storage init failed: {e}")
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_password), "name": "Admin", "role": "admin", "created_at": datetime.now(timezone.utc).isoformat()})
        logger.info(f"Admin user created: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password), "role": "admin"}})
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
    for section, defaults in {"home": {"hero_title": "GERdoctor - dein persoenlicher Weg zum Facharzt in Deutschland", "hero_subtitle": "Von der Vorbereitung bis zum Arbeitseinstieg unterstuetzen wir vollumfaenglich", "hero_cta": "Jetzt starten"}, "about": {"title": "Ueber uns", "description": "Erhalte die Arbeitserlaubnis zum Praktizieren in Deutschland.", "mission": "Der einfache Weg zur deutschen Approbation"}, "partners": {"title": "Unsere Partner unterstuetzen dich", "description": "Arbeiten Sie mit branchenfuehrenden Partnern zusammen."}}.items():
        if not await db.cms_content.find_one({"section": section}):
            await db.cms_content.insert_one({"section": section, "content": defaults, "created_at": datetime.now(timezone.utc).isoformat()})
    # Seed site settings
    if not await db.site_settings.find_one({"_key": "global"}):
        await db.site_settings.insert_one({"_key": "global", "site_title": "GERdoctor", "logo_text": "GERdoctor", "logo_bold_part": "GER", "logo_light_part": "doctor", "contact_email": "", "footer_text": "", "primary_color": "#114f55", "meta_description": "Praktizieren in Deutschland", "created_at": datetime.now(timezone.utc).isoformat()})
    logger.info("Startup seeding complete")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
