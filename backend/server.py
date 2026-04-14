from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, File, UploadFile, Query, Header
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
import bcrypt
import jwt
import secrets
import asyncio
import uuid
import requests
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Any
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

# Object Storage Configuration
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_NAME = "guided-journey"
storage_key = None

def init_storage():
    """Initialize storage connection once at startup."""
    global storage_key
    if storage_key:
        return storage_key
    if not EMERGENT_KEY:
        logger.warning("EMERGENT_LLM_KEY not set, file uploads will not work")
        return None
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Storage initialized successfully")
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload file to storage."""
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not configured")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str) -> tuple:
    """Download file from storage."""
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not configured")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# Email Configuration (Mailgun SMTP)
MAILGUN_SMTP_HOST = os.environ.get("MAILGUN_SMTP_HOST", "smtp.eu.mailgun.org")
MAILGUN_SMTP_PORT = int(os.environ.get("MAILGUN_SMTP_PORT", 587))
MAILGUN_SMTP_USER = os.environ.get("MAILGUN_SMTP_USER", "")
MAILGUN_SMTP_PASSWORD = os.environ.get("MAILGUN_SMTP_PASSWORD", "")
MAILGUN_FROM_EMAIL = os.environ.get("MAILGUN_FROM_EMAIL", "")

def send_email_sync(to_email: str, subject: str, html_content: str) -> dict:
    """Send email via Mailgun SMTP (synchronous, run in thread)."""
    if not MAILGUN_SMTP_USER or not MAILGUN_FROM_EMAIL:
        logger.info(f"Email not configured. Would send to {to_email}: {subject}")
        return {"status": "skipped", "message": "Email not configured"}
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr(("GuidedJourney", MAILGUN_FROM_EMAIL))
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(MAILGUN_SMTP_HOST, MAILGUN_SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(MAILGUN_SMTP_USER, MAILGUN_SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}: {subject}")
        return {"status": "success"}
    except (smtplib.SMTPException, ConnectionRefusedError, socket.gaierror, TimeoutError) as e:
        logger.error(f"SMTP error sending to {to_email}: {e}")
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {"status": "failed", "error": str(e)}

async def send_email_notification(to_email: str, subject: str, html_content: str):
    """Send email notification using Mailgun SMTP (non-blocking)."""
    return await asyncio.to_thread(send_email_sync, to_email, subject, html_content)

# Password hashing
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# JWT Token Management
def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
        "type": "access"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

# Auth helper
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Role-based access
def require_role(*roles):
    async def check_role(request: Request):
        user = await get_current_user(request)
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role

# Pydantic Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    created_at: Optional[str] = None

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    date_of_birth: Optional[str] = None
    profile_image_id: Optional[str] = None

class PartnerCreate(BaseModel):
    name: str
    description: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class StepFieldCreate(BaseModel):
    name: str
    field_type: str  # text, email, phone, textarea, select, selectbox, file, multiupload, date
    label: str
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None  # for select/selectbox/multiupload document types

class StepCreate(BaseModel):
    title: str
    description: str
    order: int
    step_type: str  # form, partner_selection, milestone, display
    fields: Optional[List[StepFieldCreate]] = None
    filter_tag: Optional[str] = None  # for partner_selection: filter by this tag
    skippable: bool = False
    skip_label: Optional[str] = None
    action_label: Optional[str] = None  # for display type: button text
    pending_message: Optional[str] = None  # for milestone type
    complete_message: Optional[str] = None  # for milestone type
    required_fields: Optional[List[str]] = None  # field names required to proceed
    required_uploads: Optional[List[str]] = None  # document types required to proceed
    field_mappings: Optional[List[dict]] = None  # [{source_field, source_value, target_step_order, target_field, target_value}]
    email_on_enter: bool = False
    email_on_edit: bool = False
    email_on_leave: bool = False

class StepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    step_type: Optional[str] = None
    fields: Optional[List[StepFieldCreate]] = None
    filter_tag: Optional[str] = None
    skippable: Optional[bool] = None
    skip_label: Optional[str] = None
    action_label: Optional[str] = None
    pending_message: Optional[str] = None
    complete_message: Optional[str] = None
    required_fields: Optional[List[str]] = None
    required_uploads: Optional[List[str]] = None
    field_mappings: Optional[List[dict]] = None
    email_on_enter: Optional[bool] = None
    email_on_edit: Optional[bool] = None
    email_on_leave: Optional[bool] = None
    is_active: Optional[bool] = None

class UserProgressUpdate(BaseModel):
    step_id: str
    status: str  # pending, in_progress, completed
    data: Optional[dict] = None

class PartnerSubmissionCreate(BaseModel):
    partner_id: str
    data: dict

class CMSContentUpdate(BaseModel):
    section: str  # home, about, partners
    content: dict

class NotificationPreferences(BaseModel):
    email_on_step_enter: bool = True
    email_on_step_edit: bool = False
    email_on_step_leave: bool = True

class BulkRoleUpdate(BaseModel):
    user_ids: List[str]
    role: str

# Audit log helper
async def create_audit_log(actor_id: str, actor_email: str, action: str, target_type: str, target_id: str = "", details: dict = None):
    """Record an admin action in the audit log."""
    await db.audit_logs.insert_one({
        "actor_id": actor_id,
        "actor_email": actor_email,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

# Create the main app
app = FastAPI()

# Create routers
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
        "email": email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": "user",
        "profile": {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    # Initialize user progress
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    for step in steps:
        await db.user_progress.insert_one({
            "user_id": user_id,
            "step_id": str(step["_id"]),
            "status": "pending",
            "data": {},
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
    
    # Check brute force
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        lockout_until = attempt.get("lockout_until")
        if lockout_until and datetime.fromisoformat(lockout_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})
    
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        # Increment failed attempts
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {
                "$inc": {"count": 1},
                "$set": {"lockout_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}
            },
            upsert=True
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Clear failed attempts
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
        "user_id": str(user["_id"]),
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "used": False
    })
    
    reset_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
    logger.info(f"Password reset link for {email}: {reset_link}")
    
    await send_email_notification(
        email,
        "Password Reset Request",
        f"<p>Click <a href='{reset_link}'>here</a> to reset your password. This link expires in 1 hour.</p>"
    )
    
    return {"message": "If an account exists, a reset link has been sent"}

@auth_router.post("/reset-password")
async def reset_password(data: ResetPassword):
    token_doc = await db.password_reset_tokens.find_one({"token": data.token, "used": False})
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    if datetime.fromisoformat(token_doc["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    
    await db.users.update_one(
        {"_id": ObjectId(token_doc["user_id"])},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    await db.password_reset_tokens.update_one({"token": data.token}, {"$set": {"used": True}})
    
    return {"message": "Password reset successful"}

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
        await db.users.update_one(
            {"_id": ObjectId(user["_id"])},
            {"$set": {"name": update_data.pop("name")}}
        )
    
    if update_data:
        await db.users.update_one(
            {"_id": ObjectId(user["_id"])},
            {"$set": {f"profile.{k}": v for k, v in update_data.items()}}
        )
    
    return {"message": "Profile updated"}

# Notification Preferences
@api_router.get("/notifications/preferences")
async def get_notification_preferences(request: Request):
    user = await get_current_user(request)
    prefs = user.get("notification_preferences", {
        "email_on_step_enter": True,
        "email_on_step_edit": False,
        "email_on_step_leave": True
    })
    return prefs

@api_router.put("/notifications/preferences")
async def update_notification_preferences(data: NotificationPreferences, request: Request):
    user = await get_current_user(request)
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {"notification_preferences": data.model_dump()}}
    )
    return {"message": "Notification preferences updated"}

# ========================
# STEPS ROUTES
# ========================

@steps_router.get("")
async def get_steps(request: Request):
    user = await get_current_user(request)
    steps = await db.steps.find({"is_active": True}, {"_id": 0}).sort("order", 1).to_list(100)
    # Add string id
    all_steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    for i, step in enumerate(steps):
        step["id"] = str(all_steps[i]["_id"])
    return steps

@steps_router.get("/progress")
async def get_user_progress(request: Request):
    user = await get_current_user(request)
    progress = await db.user_progress.find({"user_id": user["_id"]}, {"_id": 0}).to_list(100)
    return progress

@steps_router.put("/progress")
async def update_user_progress(data: UserProgressUpdate, request: Request):
    user = await get_current_user(request)
    
    # Get step to check email settings
    step = await db.steps.find_one({"_id": ObjectId(data.step_id)})
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    existing = await db.user_progress.find_one({"user_id": user["_id"], "step_id": data.step_id})
    
    # Get user notification preferences
    user_prefs = user.get("notification_preferences", {
        "email_on_step_enter": True,
        "email_on_step_edit": False,
        "email_on_step_leave": True
    })
    
    # Send email on edit if step configured AND user opted in
    if existing and step.get("email_on_edit") and data.data and user_prefs.get("email_on_step_edit", False):
        await send_email_notification(
            user["email"],
            f"Step Updated: {step['title']}",
            f"<p>You have updated your progress on step: {step['title']}</p>"
        )
    
    # Send email on enter if step configured AND user opted in
    if not existing and step.get("email_on_enter") and user_prefs.get("email_on_step_enter", True):
        await send_email_notification(
            user["email"],
            f"Step Started: {step['title']}",
            f"<p>You have started step: {step['title']}</p>"
        )
    
    # Send email on leave (completion) if step configured AND user opted in
    if data.status == "completed" and step.get("email_on_leave") and user_prefs.get("email_on_step_leave", True):
        await send_email_notification(
            user["email"],
            f"Step Completed: {step['title']}",
            f"<p>Congratulations! You have completed step: {step['title']}</p>"
        )
    
    await db.user_progress.update_one(
        {"user_id": user["_id"], "step_id": data.step_id},
        {
            "$set": {
                "status": data.status,
                "data": data.data or {},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Progress updated"}

# ========================
# PARTNERS ROUTES
# ========================

@partner_router.get("")
async def get_partners(tag: str = ""):
    query = {"is_active": True}
    if tag:
        query["tags"] = tag
    partners = await db.partners.find(query).to_list(100)
    result = []
    for p in partners:
        result.append({
            "id": str(p["_id"]),
            "name": p["name"],
            "description": p["description"],
            "logo_url": p.get("logo_url"),
            "website": p.get("website"),
            "category": p.get("category"),
            "tags": p.get("tags", [])
        })
    return result

@partner_router.get("/{partner_id}")
async def get_partner(partner_id: str):
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {
        "id": str(partner["_id"]),
        "name": partner["name"],
        "description": partner["description"],
        "logo_url": partner.get("logo_url"),
        "website": partner.get("website"),
        "contact_email": partner.get("contact_email"),
        "category": partner.get("category"),
        "tags": partner.get("tags", [])
    }

@partner_router.post("/submit")
async def submit_to_partner(data: PartnerSubmissionCreate, request: Request):
    user = await get_current_user(request)
    
    partner = await db.partners.find_one({"_id": ObjectId(data.partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    submission = {
        "id": str(uuid.uuid4()),
        "user_id": user["_id"],
        "user_email": user["email"],
        "user_name": user["name"],
        "partner_id": data.partner_id,
        "data": data.data,
        "status": "submitted",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.partner_submissions.insert_one(submission)
    
    return {"message": "Submission successful", "submission_id": submission["id"]}

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
    
    file_doc = {
        "id": file_id,
        "user_id": user["_id"],
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.files.insert_one(file_doc)
    
    return {"id": file_id, "filename": file.filename, "path": result["path"]}

@files_router.get("/{file_id}")
async def get_file(file_id: str, request: Request, auth: str = Query(None)):
    # Support query param auth for img tags
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
        result.append({
            "id": str(u["_id"]),
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "created_at": u.get("created_at")
        })
    return result

# Admin Search Users - MUST be before /users/{user_id}
@admin_router.get("/users/search")
async def admin_search_users(request: Request, q: str = "", role: str = ""):
    await require_role("admin")(request)
    
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}}
        ]
    if role and role != "all":
        query["role"] = role
    
    users = await db.users.find(query, {"password_hash": 0}).to_list(1000)
    result = []
    for u in users:
        result.append({
            "id": str(u["_id"]),
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "created_at": u.get("created_at"),
            "partner_id": u.get("partner_id")
        })
    return result

@admin_router.get("/users/{user_id}")
async def admin_get_user(user_id: str, request: Request):
    await require_role("admin")(request)
    user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    submissions = await db.partner_submissions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "profile": user.get("profile", {}),
        "created_at": user.get("created_at"),
        "progress": progress,
        "submissions": submissions
    }

@admin_router.put("/users/{user_id}/progress")
async def admin_update_user_progress(user_id: str, data: UserProgressUpdate, request: Request):
    await require_role("admin")(request)
    
    await db.user_progress.update_one(
        {"user_id": user_id, "step_id": data.step_id},
        {
            "$set": {
                "status": data.status,
                "data": data.data or {},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    return {"message": "User progress updated"}

# Bulk Role Update
@admin_router.put("/users/bulk-role")
async def admin_bulk_update_role(data: BulkRoleUpdate, request: Request):
    await require_role("admin")(request)
    if data.role not in ["user", "admin", "partner"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    updated = 0
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    for uid in data.user_ids:
        try:
            # Skip the primary admin account
            target = await db.users.find_one({"_id": ObjectId(uid)})
            if target and target["email"] == admin_email and data.role != "admin":
                continue
            result = await db.users.update_one(
                {"_id": ObjectId(uid)},
                {"$set": {"role": data.role}}
            )
            if result.modified_count:
                updated += 1
        except Exception:
            continue
    return {"message": f"{updated} users updated to {data.role}"}

# CSV Export
@admin_router.get("/export/users")
async def admin_export_users_csv(request: Request):
    await require_role("admin")(request)
    
    users = await db.users.find({}, {"password_hash": 0}).to_list(10000)
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    step_headers = [s["title"] for s in steps]
    writer.writerow(["Name", "Email", "Role", "Created At"] + step_headers)
    
    for u in users:
        user_id = str(u["_id"])
        progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        progress_map = {p["step_id"]: p["status"] for p in progress}
        
        step_statuses = [progress_map.get(str(s["_id"]), "not_started") for s in steps]
        writer.writerow([
            u.get("name", ""),
            u.get("email", ""),
            u.get("role", ""),
            u.get("created_at", "")
        ] + step_statuses)
    
    csv_content = output.getvalue()
    from fastapi.responses import Response as RawResponse
    return RawResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"}
    )

@admin_router.put("/users/{user_id}/role")
async def admin_update_user_role(user_id: str, role: str, request: Request):
    admin_user = await require_role("admin")(request)
    if role not in ["user", "admin", "partner"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Protect the admin seed account from role changes
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if target and target["email"] == os.environ.get("ADMIN_EMAIL", "admin@example.com") and role != "admin":
        raise HTTPException(status_code=400, detail="Cannot change the primary admin's role")
    
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": role}})
    await create_audit_log(admin_user["_id"], admin_user["email"], "role_change", "user", user_id, {"new_role": role})
    return {"message": "User role updated"}

# Admin Step Management
@admin_router.get("/steps")
async def admin_get_steps(request: Request):
    await require_role("admin")(request)
    steps = await db.steps.find().sort("order", 1).to_list(100)
    result = []
    for s in steps:
        result.append({
            "id": str(s["_id"]),
            "title": s["title"],
            "description": s["description"],
            "order": s["order"],
            "step_type": s["step_type"],
            "fields": s.get("fields", []),
            "filter_tag": s.get("filter_tag", ""),
            "skippable": s.get("skippable", False),
            "skip_label": s.get("skip_label", ""),
            "action_label": s.get("action_label", ""),
            "pending_message": s.get("pending_message", ""),
            "complete_message": s.get("complete_message", ""),
            "required_fields": s.get("required_fields", []),
            "required_uploads": s.get("required_uploads", []),
            "field_mappings": s.get("field_mappings", []),
            "email_on_enter": s.get("email_on_enter", False),
            "email_on_edit": s.get("email_on_edit", False),
            "email_on_leave": s.get("email_on_leave", False),
            "is_active": s.get("is_active", True)
        })
    return result

@admin_router.post("/steps")
async def admin_create_step(data: StepCreate, request: Request):
    await require_role("admin")(request)
    
    step_doc = {
        "title": data.title,
        "description": data.description,
        "order": data.order,
        "step_type": data.step_type,
        "fields": [f.model_dump() for f in data.fields] if data.fields else [],
        "filter_tag": data.filter_tag or "",
        "skippable": data.skippable,
        "skip_label": data.skip_label or "",
        "action_label": data.action_label or "",
        "pending_message": data.pending_message or "",
        "complete_message": data.complete_message or "",
        "required_fields": data.required_fields or [],
        "required_uploads": data.required_uploads or [],
        "field_mappings": data.field_mappings or [],
        "email_on_enter": data.email_on_enter,
        "email_on_edit": data.email_on_edit,
        "email_on_leave": data.email_on_leave,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.steps.insert_one(step_doc)
    admin_user = await get_current_user(request)
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_create", "step", str(result.inserted_id), {"title": data.title})
    return {"id": str(result.inserted_id), "message": "Step created"}

class StepReorder(BaseModel):
    step_ids: List[str]

@admin_router.put("/steps/reorder")
async def admin_reorder_steps(data: StepReorder, request: Request):
    admin_user = await require_role("admin")(request)
    
    for idx, step_id in enumerate(data.step_ids):
        await db.steps.update_one(
            {"_id": ObjectId(step_id)},
            {"$set": {"order": idx + 1}}
        )
    
    await create_audit_log(
        admin_user["_id"], admin_user["email"], "steps_reorder", "step", "",
        {"new_order": data.step_ids}
    )
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
    await db.steps.delete_one({"_id": ObjectId(step_id)})
    await create_audit_log(admin_user["_id"], admin_user["email"], "step_delete", "step", step_id, {"title": step["title"] if step else "unknown"})
    return {"message": "Step deleted"}

# Admin Partner Management
@admin_router.get("/partners")
async def admin_get_partners(request: Request):
    await require_role("admin")(request)
    partners = await db.partners.find().to_list(100)
    result = []
    for p in partners:
        result.append({
            "id": str(p["_id"]),
            "name": p["name"],
            "description": p["description"],
            "logo_url": p.get("logo_url"),
            "website": p.get("website"),
            "contact_email": p.get("contact_email"),
            "category": p.get("category"),
            "tags": p.get("tags", []),
            "is_active": p.get("is_active", True),
            "user_id": p.get("user_id")
        })
    return result

@admin_router.post("/partners")
async def admin_create_partner(data: PartnerCreate, request: Request):
    await require_role("admin")(request)
    
    partner_doc = {
        "name": data.name,
        "description": data.description,
        "logo_url": data.logo_url,
        "website": data.website,
        "contact_email": data.contact_email,
        "category": data.category,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.partners.insert_one(partner_doc)
    return {"id": str(result.inserted_id), "message": "Partner created"}

@admin_router.put("/partners/{partner_id}")
async def admin_update_partner(partner_id: str, data: PartnerUpdate, request: Request):
    await require_role("admin")(request)
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$set": update_data})
    admin_user = await get_current_user(request)
    await create_audit_log(admin_user["_id"], admin_user["email"], "partner_update", "partner", partner_id, {"fields_changed": list(update_data.keys())})
    return {"message": "Partner updated"}

@admin_router.delete("/partners/{partner_id}")
async def admin_delete_partner(partner_id: str, request: Request):
    await require_role("admin")(request)
    await db.partners.delete_one({"_id": ObjectId(partner_id)})
    return {"message": "Partner deleted"}

@admin_router.put("/partners/{partner_id}/link-user")
async def admin_link_partner_user(partner_id: str, user_id: str, request: Request):
    await require_role("admin")(request)
    
    # Verify user exists
    target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify partner exists
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Unlink previous user if any
    old_user_id = partner.get("user_id")
    if old_user_id:
        await db.users.update_one(
            {"_id": ObjectId(old_user_id)},
            {"$set": {"role": "user"}, "$unset": {"partner_id": ""}}
        )
    
    # Update partner with user link
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$set": {"user_id": user_id}})
    # Update user role to partner
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
        await db.users.update_one(
            {"_id": ObjectId(old_user_id)},
            {"$set": {"role": "user"}, "$unset": {"partner_id": ""}}
        )
    
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$unset": {"user_id": ""}})
    return {"message": "Partner unlinked from user"}

# Admin Analytics
@admin_router.get("/analytics")
async def admin_get_analytics(request: Request):
    await require_role("admin")(request)
    
    total_users = await db.users.count_documents({"role": "user"})
    total_partners = await db.partners.count_documents({"is_active": True})
    total_submissions = await db.partner_submissions.count_documents({})
    
    # Step completion rates
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
    step_analytics = []
    for step in steps:
        step_id = str(step["_id"])
        total = await db.user_progress.count_documents({"step_id": step_id})
        completed = await db.user_progress.count_documents({"step_id": step_id, "status": "completed"})
        in_progress = await db.user_progress.count_documents({"step_id": step_id, "status": "in_progress"})
        step_analytics.append({
            "step_id": step_id,
            "title": step["title"],
            "order": step["order"],
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "completion_rate": round((completed / total * 100) if total > 0 else 0, 1)
        })
    
    # Users by role
    admin_count = await db.users.count_documents({"role": "admin"})
    partner_count = await db.users.count_documents({"role": "partner"})
    
    # Recent registrations (last 7 days)
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_users = await db.users.count_documents({
        "created_at": {"$gte": seven_days_ago}
    })
    
    return {
        "total_users": total_users,
        "total_partners": total_partners,
        "total_submissions": total_submissions,
        "admin_count": admin_count,
        "partner_count": partner_count,
        "recent_registrations": recent_users,
        "step_analytics": step_analytics
    }

# Admin Audit Log
@admin_router.get("/audit-log")
async def admin_get_audit_log(
    request: Request, 
    limit: int = 100, 
    skip: int = 0,
    action: str = "",
    date_from: str = "",
    date_to: str = ""
):
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
    
    # Get distinct action types for filter dropdown
    action_types = await db.audit_logs.distinct("action")
    
    return {"logs": logs, "total": total, "action_types": action_types}

# ========================
# PARTNER DASHBOARD ROUTES
# ========================

@api_router.get("/partner/submissions")
async def get_partner_submissions(request: Request):
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    
    submissions = await db.partner_submissions.find({"partner_id": partner_id}, {"_id": 0}).to_list(1000)
    return submissions

@api_router.get("/partner/profile")
async def get_partner_profile(request: Request):
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    return {
        "id": str(partner["_id"]),
        "name": partner["name"],
        "description": partner["description"],
        "logo_url": partner.get("logo_url"),
        "website": partner.get("website"),
        "contact_email": partner.get("contact_email"),
        "category": partner.get("category")
    }

@api_router.put("/partner/profile")
async def update_partner_profile(data: PartnerUpdate, request: Request):
    user = await require_role("partner")(request)
    partner_id = user.get("partner_id")
    if not partner_id:
        raise HTTPException(status_code=400, detail="User not linked to a partner")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.partners.update_one({"_id": ObjectId(partner_id)}, {"$set": update_data})
    return {"message": "Partner profile updated"}

# ========================
# CMS ROUTES
# ========================

@cms_router.get("/{section}")
async def get_cms_content(section: str):
    content = await db.cms_content.find_one({"section": section}, {"_id": 0})
    if not content:
        # Return default content
        defaults = {
            "home": {
                "hero_title": "Transform Your Business Journey",
                "hero_subtitle": "A guided experience to connect you with the right partners",
                "hero_cta": "Get Started"
            },
            "about": {
                "title": "About Us",
                "description": "We help businesses connect with the right partners through a streamlined onboarding process.",
                "mission": "Our mission is to simplify business partnerships."
            },
            "partners": {
                "title": "Our Partners",
                "description": "Work with industry-leading partners to achieve your goals."
            }
        }
        return {"section": section, "content": defaults.get(section, {})}
    return content

@cms_router.put("/{section}")
async def update_cms_content(section: str, data: CMSContentUpdate, request: Request):
    admin_user = await require_role("admin")(request)
    
    await db.cms_content.update_one(
        {"section": section},
        {"$set": {"section": section, "content": data.content, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    await create_audit_log(admin_user["_id"], admin_user["email"], "cms_update", "cms", section, {"section": section})
    return {"message": "Content updated"}

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(partner_router)
api_router.include_router(steps_router)
api_router.include_router(files_router)
api_router.include_router(cms_router)

# Root endpoint
@api_router.get("/")
async def root():
    return {"message": "Guided Journey API"}

app.include_router(api_router)

# CORS
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
cors_origins = [frontend_url, "http://localhost:3000"]
if frontend_url.startswith("https://"):
    cors_origins.append(frontend_url.replace("https://", "http://"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup events
@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    
    # Initialize storage
    try:
        init_storage()
    except Exception as e:
        logger.warning(f"Storage init failed: {e}")
    
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hashed,
            "name": "Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"Admin user created: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password), "role": "admin"}})
        logger.info("Admin password updated")
    elif existing.get("role") != "admin":
        await db.users.update_one({"email": admin_email}, {"$set": {"role": "admin"}})
        logger.info("Admin role restored")
    
    # Seed default steps if none exist
    step_count = await db.steps.count_documents({})
    if step_count == 0:
        doc_types = ["Visum", "Antrag auf Approbation", "Approbation", "Eingangsbescheinigung bei zuständiger Behörde", "Kenntnissprüfung"]
        default_steps = [
            {
                "title": "Persönliche Daten", "description": "Füllen Sie Ihre persönlichen Informationen aus", "order": 1, "step_type": "form",
                "fields": [
                    {"name": "name", "field_type": "text", "label": "Name", "placeholder": "Ihr Nachname", "required": True},
                    {"name": "first_name", "field_type": "text", "label": "Vorname", "placeholder": "Ihr Vorname", "required": True},
                    {"name": "phone", "field_type": "phone", "label": "Telefon", "placeholder": "+49 (0) 123 456 789", "required": True},
                    {"name": "address", "field_type": "text", "label": "Adresse", "placeholder": "Straße und Hausnummer", "required": True},
                    {"name": "field_of_study", "field_type": "selectbox", "label": "Fachgebiet", "options": ["Allgemeinmedizin", "Zahnmedizin", "HNO"], "required": True},
                    {"name": "documents", "field_type": "multiupload", "label": "Dokumente", "options": doc_types, "required": False}
                ],
                "required_fields": ["name", "first_name", "phone", "address", "field_of_study"],
                "email_on_leave": True, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Service Antragstellung", "description": "Wählen Sie einen Partner für die Antragstellung", "order": 2, "step_type": "partner_selection",
                "fields": [], "filter_tag": "Antragstellung", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Meilenstein Antragstellung", "description": "Status Ihrer Antragstellung", "order": 3, "step_type": "milestone",
                "fields": [], "pending_message": "Warten auf Abschluss der Antragstellung. Ihr Partner bearbeitet Ihren Antrag.",
                "complete_message": "Alles erledigt! Sie können zum nächsten Schritt weitergehen.",
                "email_on_leave": True, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "FaMed", "description": "Weiter zur FaMed-Prüfung", "order": 4, "step_type": "display",
                "fields": [], "action_label": "zur FaMed", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Service Kenntnisprüfung", "description": "Wählen Sie einen Partner für die Kenntnisprüfung", "order": 5, "step_type": "partner_selection",
                "fields": [], "filter_tag": "Kenntnisprüfung", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Meilenstein Kenntnisprüfung", "description": "Status Ihrer Kenntnisprüfung", "order": 6, "step_type": "milestone",
                "fields": [], "pending_message": "Warten auf Abschluss der Kenntnisprüfung. Ihr Partner bearbeitet Ihre Prüfung.",
                "complete_message": "Alles erledigt! Sie können zum nächsten Schritt weitergehen.",
                "email_on_leave": True, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Service Weiterbildung", "description": "Wählen Sie einen Partner für die Weiterbildung", "order": 7, "step_type": "partner_selection",
                "fields": [], "filter_tag": "Weiterbildung", "skippable": True, "skip_label": "Vorerst überspringen",
                "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Meilenstein Job finden", "description": "Hier können wir Ihnen helfen!", "order": 8, "step_type": "display",
                "fields": [], "pending_message": "Hier können wir Ihnen helfen!", "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        await db.steps.insert_many(default_steps)
        logger.info("Default steps created (8 steps)")
    
    # Seed sample partners if none exist
    partner_count = await db.partners.count_documents({})
    if partner_count == 0:
        sample_partners = [
            {"name": "ILS", "description": "Wir helfen bei allen Anträgen", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/digiFORT.png", "website": "https://www.ils.de/", "category": "Antragstellung", "tags": ["Antragstellung"], "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"name": "ILS2", "description": "Wir helfen bei allen Kenntnisprüfungen", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/digiFORT.png", "website": "https://www.ils.de/", "category": "Kenntnisprüfung", "tags": ["Kenntnisprüfung"], "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"name": "ILS3", "description": "Wir helfen bei allen Weiterbildungen", "logo_url": "https://digifort-experts.de/wp-content/uploads/2026/02/digiFORT.png", "website": "https://www.ils.de/", "category": "Weiterbildung", "tags": ["Weiterbildung"], "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
        ]
        await db.partners.insert_many(sample_partners)
        logger.info("Sample partners created (3 tagged)")
    
    # Seed CMS
    for section, defaults in {
        "home": {"hero_title": "GERdoctor - Praktizieren in Deutschland", "hero_subtitle": "Vom Visum bis zur Arbeitserlaubnis unterstützen wir Sie auf Ihrem Weg", "hero_cta": "Jetzt starten"},
        "about": {"title": "Über uns", "description": "Erhalte die Arbeitserlaubnis zum Praktizieren in Deutschland. Wir gehen mit dir alle Schritte bis zur Approbation und Praxis Findung.", "mission": "Der einfache Weg zur deutschen Approbation"},
        "partners": {"title": "Unsere Partner unterstützen dich", "description": "Arbeiten Sie mit branchenführenden Partnern zusammen, um Ihre Ziele zu erreichen."}
    }.items():
        existing_cms = await db.cms_content.find_one({"section": section})
        if not existing_cms:
            await db.cms_content.insert_one({"section": section, "content": defaults, "created_at": datetime.now(timezone.utc).isoformat()})
    
    # Seed demo user
    demo_email = "demo@example.com"
    demo_password = "Demo123!"
    if not await db.users.find_one({"email": demo_email}):
        result = await db.users.insert_one({"email": demo_email, "password_hash": hash_password(demo_password), "name": "Demo User", "role": "user", "profile": {}, "created_at": datetime.now(timezone.utc).isoformat()})
        demo_id = str(result.inserted_id)
        steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(100)
        for step in steps:
            await db.user_progress.insert_one({"user_id": demo_id, "step_id": str(step["_id"]), "status": "pending", "data": {}, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()})
        logger.info("Demo user created")
    
    # Seed partner user
    partner_email = "partner@example.com"
    if not await db.users.find_one({"email": partner_email}):
        first_partner = await db.partners.find_one({"is_active": True})
        if first_partner:
            result = await db.users.insert_one({"email": partner_email, "password_hash": hash_password("Partner123!"), "name": "ILS Admin", "role": "partner", "partner_id": str(first_partner["_id"]), "created_at": datetime.now(timezone.utc).isoformat()})
            await db.partners.update_one({"_id": first_partner["_id"]}, {"$set": {"user_id": str(result.inserted_id)}})
            logger.info("Partner user created")
    
    # Write test credentials
    os.makedirs("/app/memory", exist_ok=True)
    with open("/app/memory/test_credentials.md", "w") as f:
        f.write(f"""# Test Credentials
## Admin: {admin_email} / {admin_password}
## Demo User: demo@example.com / Demo123!
## Partner: partner@example.com / Partner123! (linked to ILS)
## Seeded: 8 steps, 3 tagged partners, German CMS, demo user, partner user
""")
    logger.info("Startup seeding complete")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
