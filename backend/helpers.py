"""Shared helpers: email, storage, audit log, completion calculations."""
import os
import logging
import asyncio
import requests
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException
from bson import ObjectId
from dateutil.relativedelta import relativedelta
from database import db

logger = logging.getLogger("server")

# ========================
# OBJECT STORAGE
# ========================
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_NAME = "guided-journey"
storage_key = None

def init_storage():
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
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not configured")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# ========================
# EMAIL
# ========================
MAILGUN_SMTP_HOST = os.environ.get("MAILGUN_SMTP_HOST", "smtp.eu.mailgun.org")
MAILGUN_SMTP_PORT = int(os.environ.get("MAILGUN_SMTP_PORT", 587))
MAILGUN_SMTP_USER = os.environ.get("MAILGUN_SMTP_USER", "")
MAILGUN_SMTP_PASSWORD = os.environ.get("MAILGUN_SMTP_PASSWORD", "")
MAILGUN_FROM_EMAIL = os.environ.get("MAILGUN_FROM_EMAIL", "")

def send_email_sync(to_email: str, subject: str, html_content: str) -> dict:
    if not MAILGUN_SMTP_USER or not MAILGUN_FROM_EMAIL:
        logger.info(f"Email not configured. Would send to {to_email}: {subject}")
        return {"status": "skipped", "message": "Email not configured"}
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr(("GERdoctor", MAILGUN_FROM_EMAIL))
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
    return await asyncio.to_thread(send_email_sync, to_email, subject, html_content)


# ========================
# TEMPLATE RENDERING
# ========================
def _replace_vars(text: str, variables: dict) -> str:
    """Replace {{var_name}} tokens. Missing tokens fall back to empty string
    so partner emails don't leak raw {{user_email}} markers."""
    if not text:
        return ""
    import re as _re
    def _sub(match: "_re.Match[str]") -> str:
        key = match.group(1).strip()
        val = variables.get(key)
        return "" if val is None else str(val)
    return _re.sub(r"{{\s*([\w.]+)\s*}}", _sub, text)


async def render_email(
    template_key: str,
    variables: dict,
    override_subject: str = "",
    override_body: str = "",
) -> dict:
    """Fetch header + template + footer from email_templates collection, render
    variables and return {subject, html}. If override_subject/body is given and
    non-empty, they replace the DB template body/subject (step-level overrides
    still supported, but wrapped with header/footer).

    Returns {} when the collection hasn't been seeded — callers should treat
    that as "skip send" gracefully."""
    variables = dict(variables or {})
    variables.setdefault("app_url", os.environ.get("FRONTEND_URL", ""))

    header_doc = await db.email_templates.find_one({"key": "header"})
    footer_doc = await db.email_templates.find_one({"key": "footer"})
    tpl_doc = await db.email_templates.find_one({"key": template_key})
    if not tpl_doc and not override_body:
        logger.warning(f"render_email: template '{template_key}' not found in email_templates collection")
        return {}

    header_html = (header_doc or {}).get("body_html", "") if header_doc else ""
    footer_html = (footer_doc or {}).get("body_html", "") if footer_doc else ""
    subject_raw = override_subject or (tpl_doc or {}).get("subject", "")
    body_raw = override_body or (tpl_doc or {}).get("body_html", "")

    subject = _replace_vars(subject_raw, variables)
    body = _replace_vars(body_raw, variables)
    header = _replace_vars(header_html, variables)
    footer = _replace_vars(footer_html, variables)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f8fafc;">
  <div style="max-width:640px;margin:0 auto;background:#ffffff;">
    {header}
    {body}
    {footer}
  </div>
</body>
</html>"""
    return {"subject": subject, "html": html}


async def send_rendered_email(
    to_email: str,
    template_key: str,
    variables: dict,
    override_subject: str = "",
    override_body: str = "",
) -> dict:
    """Convenience: render + send. Returns the send_email result dict.
    Safe when the template is missing — logs & returns {'status': 'skipped'}."""
    rendered = await render_email(template_key, variables, override_subject, override_body)
    if not rendered:
        return {"status": "skipped", "reason": f"template '{template_key}' missing"}
    return await send_email_notification(to_email, rendered["subject"], rendered["html"])


def _partner_deep_link(user_id: str) -> str:
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return f"{base}/partner-dashboard?openUser={user_id}" if base else f"/partner-dashboard?openUser={user_id}"


async def notify_partner_of_new_submission(partner: dict, user: dict, submission_data: dict) -> int:
    """Send a "neue Anmeldung"-Mail to every partner-role user linked to the
    partner org + the public contact_email (deduplicated). Returns the number of
    recipients contacted. Safe to call even when SMTP is unconfigured (returns 0).

    Uses the DB-driven `partner_new_submission` template (wrapped with header/
    footer) so admins can edit copy in the Admin E-Mail-Vorlagen Tab."""
    if not partner:
        return 0
    partner_id = str(partner.get("_id")) if partner.get("_id") else partner.get("id")
    partner_name = partner.get("name", "")

    recipients: set[str] = set()
    if partner.get("contact_email"):
        recipients.add(partner["contact_email"])
    async for pu in db.users.find({"role": "partner", "partner_id": partner_id},
                                  {"email": 1, "notification_prefs": 1}):
        prefs = pu.get("notification_prefs") or {}
        if prefs.get("email") is False:
            continue
        if pu.get("email"):
            recipients.add(pu["email"])
    for uid in partner.get("linked_user_ids") or []:
        try:
            pu = await db.users.find_one({"_id": ObjectId(uid)},
                                          {"email": 1, "role": 1, "notification_prefs": 1})
        except Exception:
            continue
        if pu and pu.get("role") == "partner":
            prefs = pu.get("notification_prefs") or {}
            if prefs.get("email") is False:
                continue
            if pu.get("email"):
                recipients.add(pu["email"])

    if not recipients:
        return 0

    data = submission_data or {}
    field = data.get("fachrichtung_gewuenscht") or data.get("fachrichtung_praktiziert") \
            or data.get("field_of_study", "")
    bundesland = data.get("anerkennungsverfahren_bundesland", "")
    step_order = data.get("step_order")

    user_id = str(user.get("_id") or user.get("id", ""))
    variables = {
        "partner_name": partner_name,
        "user_name": user.get("name") or user.get("email", ""),
        "user_email": user.get("email", ""),
        "field_of_study": field or "—",
        "bundesland": bundesland or "—",
        "step_order": step_order or "",
        "open_user_link": _partner_deep_link(user_id),
    }

    sent = 0
    for recipient in recipients:
        try:
            result = await send_rendered_email(recipient, "partner_new_submission", variables)
            if result.get("status") == "success":
                sent += 1
        except Exception as exc:
            logger.warning(f"notify_partner failed for {recipient}: {exc}")
    return sent


async def notify_user_awaiting_partner(user: dict, partner: dict) -> dict:
    """Send a confirmation email to the user that their submission has been
    forwarded and they are awaiting the partner's response."""
    if not user or not user.get("email"):
        return {"status": "skipped"}
    prefs = user.get("notification_preferences") or {}
    if prefs.get("email_on_step_enter") is False:
        return {"status": "skipped", "reason": "opt-out"}
    variables = {
        "user_name": user.get("name") or user.get("email", ""),
        "partner_name": (partner or {}).get("name", "Partner"),
    }
    try:
        return await send_rendered_email(user["email"], "user_awaiting_partner", variables)
    except Exception as exc:
        logger.warning(f"notify_user_awaiting_partner failed for {user.get('email')}: {exc}")
        return {"status": "failed", "error": str(exc)}


async def notify_user_milestone_completed(user: dict, partner: dict, step: dict) -> dict:
    """Inform the user that the partner has completed their milestone."""
    if not user or not user.get("email"):
        return {"status": "skipped"}
    prefs = user.get("notification_preferences") or {}
    if prefs.get("email_on_step_leave") is False:
        return {"status": "skipped", "reason": "opt-out"}
    variables = {
        "user_name": user.get("name") or user.get("email", ""),
        "partner_name": (partner or {}).get("name", "Partner"),
        "milestone_title": (step or {}).get("title", ""),
        "step_title": (step or {}).get("title", ""),
        "step_order": (step or {}).get("order", ""),
        "step_description": (step or {}).get("description", ""),
    }
    try:
        return await send_rendered_email(user["email"], "user_milestone_completed", variables)
    except Exception as exc:
        logger.warning(f"notify_user_milestone_completed failed for {user.get('email')}: {exc}")
        return {"status": "failed", "error": str(exc)}

# ========================
# AUDIT LOG
# ========================
async def create_audit_log(actor_id: str, actor_email: str, action: str, target_type: str, target_id: str = "", details: dict = None):
    await db.audit_logs.insert_one({
        "actor_id": actor_id,
        "actor_email": actor_email,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

# ========================
# COMPLETION CALCULATIONS
# ========================
def add_duration(start_date, value, unit):
    if unit == "days":
        return start_date + timedelta(days=value)
    elif unit == "weeks":
        return start_date + timedelta(weeks=value)
    elif unit == "months":
        return start_date + relativedelta(months=value)
    elif unit == "years":
        return start_date + relativedelta(years=value)
    return start_date

# ========================
# CONDITION EVALUATION (server-side, mirrors frontend)
# ========================
def _evaluate_condition(cond: dict, order_map: dict) -> bool:
    """Evaluate a single condition against a map {order: {data, status}}.
    Supports compound conditions via `all_of` / `any_of` (list of sub-conditions)."""
    if isinstance(cond.get("all_of"), list):
        return all(_evaluate_condition(c, order_map) for c in cond["all_of"])
    if isinstance(cond.get("any_of"), list):
        return any(_evaluate_condition(c, order_map) for c in cond["any_of"])
    source = order_map.get(cond.get("source_step_order"))
    if not source:
        return False
    field = cond.get("field")
    data = source.get("data") or {}
    field_value = data.get(field) if field in data else source.get("status")
    expected = cond.get("value")
    op = cond.get("operator", "equals")
    if op == "equals":
        return str(field_value) == str(expected)
    if op == "not_equals":
        return str(field_value) != str(expected)
    if op == "contains":
        return str(expected) in str(field_value or "")
    if op == "not_empty":
        return bool(field_value) and field_value != ""
    if op == "empty":
        return not field_value or field_value == ""
    if op == "status_is":
        return source.get("status") == expected
    if op == "status_not":
        return source.get("status") != expected
    if op == "has_upload":
        uploads = data.get(field) or []
        if not isinstance(uploads, list):
            return False
        # Empty expected → any non-empty upload entry with a file_id qualifies
        if expected in (None, ""):
            return any(isinstance(u, dict) and u.get("file_id") for u in uploads)
        return any(
            isinstance(u, dict) and u.get("document_type") == expected and u.get("file_id")
            for u in uploads
        )
    if op == "missing_upload":
        uploads = data.get(field) or []
        if not isinstance(uploads, list):
            return True
        if expected in (None, ""):
            # Missing when NO entry has a file_id
            return not any(isinstance(u, dict) and u.get("file_id") for u in uploads)
        return not any(
            isinstance(u, dict) and u.get("document_type") == expected and u.get("file_id")
            for u in uploads
        )
    return False


async def _get_step_context(user_id: str):
    """Return (steps_sorted, order_map, hidden_step_ids, blocked_step_ids) for a user."""
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(200)
    progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    progress_map = {p["step_id"]: p for p in progress}
    order_map = {}
    for s in steps:
        sid = str(s["_id"])
        p = progress_map.get(sid, {})
        order_map[s["order"]] = {"data": p.get("data", {}), "status": p.get("status", "pending")}

    hidden_ids = set()
    blocked_ids = set()
    for s in steps:
        sid = str(s["_id"])
        for cond in (s.get("conditions") or []):
            action = cond.get("action")
            if action not in ("hide", "block"):
                continue
            if _evaluate_condition(cond, order_map):
                if action == "hide":
                    hidden_ids.add(sid)
                elif action == "block":
                    blocked_ids.add(sid)
    return steps, order_map, hidden_ids, blocked_ids


async def compute_auto_complete_steps(user_id: str):
    """Return list of step_ids that should be auto-completed based on conditions.
    Called after a progress update so e.g. milestones auto-complete when an upload path was taken."""
    steps, order_map, hidden_ids, _ = await _get_step_context(user_id)
    progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    status_map = {p["step_id"]: p.get("status", "pending") for p in progress}
    to_auto = []
    for s in steps:
        sid = str(s["_id"])
        if sid in hidden_ids:
            continue
        if status_map.get(sid) == "completed":
            continue
        for cond in (s.get("conditions") or []):
            if cond.get("action") != "auto_complete":
                continue
            if _evaluate_condition(cond, order_map):
                to_auto.append(sid)
                break
    return to_auto


async def apply_auto_completes(user_id: str):
    """Complete any steps whose auto_complete condition is currently met."""
    sids = await compute_auto_complete_steps(user_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    for sid in sids:
        existing = await db.user_progress.find_one({"user_id": user_id, "step_id": sid})
        if existing and existing.get("status") == "completed":
            continue
        step = await db.steps.find_one({"_id": ObjectId(sid)})
        update_fields = {
            "status": "completed",
            "data": (existing or {}).get("data") or {"auto_completed": True},
            "updated_at": now_iso,
            "completed_at": now_iso,
        }
        if not (existing and existing.get("started_at")):
            update_fields["started_at"] = now_iso
        await db.user_progress.update_one(
            {"user_id": user_id, "step_id": sid},
            {"$set": update_fields},
            upsert=True,
        )
        await db.progress_history.insert_one({
            "user_id": user_id, "step_id": sid,
            "step_title": (step or {}).get("title", ""),
            "step_order": (step or {}).get("order", 0),
            "action": "auto_completed", "timestamp": now_iso,
        })
    return sids


# ========================
# ANERKENNUNGSSTATUS → Block auto-skip
# ========================
# Each block is (decision_order, upload_order_or_None, milestone_order)
BLOCK_DEFINITIONS = {
    "Antragstellung Approbation": (2, 3, 5),
    "Fachsprachenprüfung":        (6, 7, 9),
    "Gleichwertigkeitsprüfung":  (10, 11, 13),
    "Kenntnisprüfung":            (14, 15, 17),
    "Weiterbildung":              (21, 22, 24),
}

# Which blocks are already-done when the user picks a given anerkennungsstatus.
# Chosen mapping (can be refined later):
#   "…Fachsprachenprüfung bestanden"          → Fachsprachenprüfung fertig
#   "Berufserlaubnis erteilt"                  → Antragstellung fertig
#   "Termin Kenntnisprüfung beantragt"         → Antragstellung + Fachsprachen fertig
#   "Gleichwertigkeitsprüfung beantragt"       → Antragstellung + Fachsprachen fertig
#   "In Deutschland approbiert"                → Antragstellung + Fachsprachen + Gleichwert. + Kenntnisprüfung fertig
ANERKENNUNGSSTATUS_COMPLETE_MAP = {
    "Ich habe die Fachsprachenprüfung Medizin bestanden": [
        "Fachsprachenprüfung",
    ],
    "Die Berufserlaubnis wurde mir erteilt": [
        "Antragstellung Approbation",
    ],
    "Ich habe einen Termin zur Kenntnisprüfung (beantragt)": [
        "Antragstellung Approbation", "Fachsprachenprüfung",
    ],
    "Ich habe die Gleichwertigkeitsprüfung beantragt": [
        "Antragstellung Approbation", "Fachsprachenprüfung",
    ],
    "Ich bin in Deutschland approbiert": [
        "Antragstellung Approbation", "Fachsprachenprüfung",
        "Gleichwertigkeitsprüfung", "Kenntnisprüfung",
    ],
}


async def apply_anerkennungsstatus_skips(user_id: str, status: str):
    """Auto-complete whole blocks based on the user's anerkennungsstatus.

    Blocks marked complete stay hidden for the user (decision='upload' triggers
    hide-conditions on partner step + auto_complete on milestone) and count as
    done in progress/ETA.
    Idempotent — already-completed steps are skipped."""
    if not status:
        return []
    blocks = ANERKENNUNGSSTATUS_COMPLETE_MAP.get(status, [])
    if not blocks:
        return []
    now_iso = datetime.now(timezone.utc).isoformat()
    affected = []
    for block_name in blocks:
        dec_order, upload_order, ms_order = BLOCK_DEFINITIONS[block_name]
        for order in (dec_order, upload_order, ms_order):
            if order is None:
                continue
            step = await db.steps.find_one({"order": order, "is_active": True})
            if not step:
                continue
            sid = str(step["_id"])
            existing = await db.user_progress.find_one({"user_id": user_id, "step_id": sid})
            if existing and existing.get("status") == "completed":
                continue
            data = {"auto_skipped_by_status": True, "anerkennungsstatus": status}
            if step.get("step_type") == "decision":
                # Force the 'upload' branch so partner_step stays hidden + milestone auto-matches
                data["decision"] = "upload"
            await db.user_progress.update_one(
                {"user_id": user_id, "step_id": sid},
                {"$set": {
                    "status": "completed", "data": data,
                    "updated_at": now_iso,
                    "completed_at": now_iso,
                    "started_at": (existing or {}).get("started_at") or now_iso,
                }},
                upsert=True,
            )
            await db.progress_history.insert_one({
                "user_id": user_id, "step_id": sid,
                "step_title": step.get("title", ""),
                "step_order": step.get("order", 0),
                "action": "auto_skipped_by_status",
                "timestamp": now_iso,
            })
            affected.append(sid)
    return affected


async def calculate_completion_pct(user_id: str) -> int:
    steps, _, hidden_ids, _ = await _get_step_context(user_id)
    countable_steps = [s for s in steps if s.get("duration_value", 0) > 0 and str(s["_id"]) not in hidden_ids]
    if not countable_steps:
        return 0
    countable_ids = {str(s["_id"]) for s in countable_steps}
    completed = await db.user_progress.count_documents({
        "user_id": user_id,
        "status": "completed",
        "step_id": {"$in": list(countable_ids)}
    })
    return round((completed / len(countable_steps) * 100))

async def calculate_estimated_completion(user_id: str) -> Optional[str]:
    steps, _, hidden_ids, _ = await _get_step_context(user_id)
    progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    progress_map = {p["step_id"]: p for p in progress}
    if not steps:
        return None
    last_completed_at = None
    for s in steps:
        sid = str(s["_id"])
        if sid in hidden_ids:
            continue
        p = progress_map.get(sid, {})
        if p.get("status") == "completed" and p.get("completed_at"):
            ts = p["completed_at"]
            if not last_completed_at or ts > last_completed_at:
                last_completed_at = ts
    if last_completed_at:
        try:
            start_date = datetime.fromisoformat(last_completed_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            start_date = datetime.now(timezone.utc)
    else:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user and user.get("created_at"):
            try:
                start_date = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                start_date = datetime.now(timezone.utc)
        else:
            start_date = datetime.now(timezone.utc)
    current = start_date
    for s in steps:
        sid = str(s["_id"])
        if sid in hidden_ids:
            continue
        p = progress_map.get(sid, {})
        if p.get("status") != "completed":
            duration_value = s.get("duration_value", 0)
            duration_unit = s.get("duration_unit", "days")
            if duration_value > 0:
                current = add_duration(current, duration_value, duration_unit)
    return current.isoformat()
