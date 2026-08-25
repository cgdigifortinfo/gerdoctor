"""Shared helpers: email, storage, audit log, completion calculations."""
import os
import logging
import asyncio
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException
from bson import ObjectId
from slices.step_versioning.facade import write_progress_revision
from dateutil.relativedelta import relativedelta
from database import db
from slices.survey_runtime.domain import (
    add_duration as runtime_add_duration,
    calculate_metrics as runtime_calculate_metrics,
    completion_steps as runtime_completion_steps,
    evaluate_condition as runtime_evaluate_condition,
    is_progress_gate_condition as runtime_is_progress_gate_condition,
)
from slices.survey_runtime.mappers import runtime_context_from_documents
from slices.survey_runtime.domain import order_state as runtime_order_state, visibility as runtime_visibility
from infrastructure.clock import system_utc_clock
from slices.survey_runtime.repository import MongoSurveyRuntimeRepository
from slices.survey_runtime.service import SurveyRuntimeService
from infrastructure.smtp_email_gateway import SmtpEmailGateway
from slices.email_notifications.repository import MongoMessageTemplateRepository
from slices.email_notifications.service import EmailNotificationsService, TemplateNotFound
from slices.email_notifications.domain import replace_variables as _replace_vars
from slices.audit_trail.repository import MongoAuditTrailRepository
from slices.audit_trail.service import AuditTrailService

logger = logging.getLogger("server")
survey_runtime_service = SurveyRuntimeService(MongoSurveyRuntimeRepository(db), system_utc_clock.now)
audit_trail_service = AuditTrailService(MongoAuditTrailRepository(db), system_utc_clock.now_iso)

# ========================
# EMAIL
# ========================
smtp_email_gateway = SmtpEmailGateway(
        os.environ.get("MAILGUN_SMTP_HOST", "smtp.eu.mailgun.org"),
        int(os.environ.get("MAILGUN_SMTP_PORT", 587)),
        os.environ.get("MAILGUN_SMTP_USER", ""),
        os.environ.get("MAILGUN_SMTP_PASSWORD", ""),
        os.environ.get("MAILGUN_FROM_EMAIL", ""),
)
email_notifications_service = EmailNotificationsService(
    MongoMessageTemplateRepository(db), smtp_email_gateway,
    os.environ.get("FRONTEND_URL", ""),
)


def send_email_sync(to_email: str, subject: str, html_content: str) -> dict:
    return smtp_email_gateway.send_sync(to_email, subject, html_content).to_document()


async def send_email_notification(to_email: str, subject: str, html_content: str) -> dict:
    return await asyncio.to_thread(send_email_sync, to_email, subject, html_content)


# ========================
# TEMPLATE RENDERING
# ========================
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
    try:
        rendered = await email_notifications_service.email(
            template_key, variables or {}, override_subject, override_body,
        )
    except TemplateNotFound:
        logger.warning("render_email: template '%s' not found", template_key)
        return {}
    return rendered.to_document()


async def render_notification(
    template_key: str,
    variables: dict,
    override_title: str | None = None,
    override_body: str | None = None,
) -> dict:
    """Render the compact Browser/App copy stored beside an email template."""
    try:
        rendered = await email_notifications_service.notification(
            template_key, variables or {}, override_title, override_body,
        )
    except TemplateNotFound:
        logger.warning("render_notification: template '%s' not found", template_key)
        return {}
    return rendered.to_document()


async def send_rendered_email(
    to_email: str,
    template_key: str,
    variables: dict,
    override_subject: str = "",
    override_body: str = "",
) -> dict:
    """Convenience: render + send. Returns the send_email result dict.
    Safe when the template is missing — logs & returns {'status': 'skipped'}."""
    result = await email_notifications_service.send_rendered(
        to_email, template_key, variables or {}, override_subject, override_body,
    )
    document = result.to_document()
    if result.status == "skipped" and result.error:
        return {"status": "skipped", "reason": result.error}
    return document


def _partner_deep_link(user_id: str) -> str:
    from slices.email_notifications.domain import partner_deep_link
    return partner_deep_link(os.environ.get("FRONTEND_URL", ""), user_id)


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
    await audit_trail_service.record(actor_id, actor_email, action, target_type, target_id, details)

# ========================
# COMPLETION CALCULATIONS
# ========================
def add_duration(start_date, value, unit):
    return runtime_add_duration(start_date, value, unit)


def _is_progress_gate_condition(cond: dict) -> bool:
    return runtime_is_progress_gate_condition(cond)


def _completion_denominator_steps(steps: list, hidden_ids: set) -> list:
    context = runtime_context_from_documents(steps, [])
    return [step.document for step in runtime_completion_steps(context.steps, frozenset(hidden_ids))]

# ========================
# CONDITION EVALUATION (server-side, mirrors frontend)
# ========================
def _evaluate_condition(cond: dict, order_map: dict) -> bool:
    """Evaluate a single condition against a map {order: {data, status}}.
    Supports compound conditions via `all_of` / `any_of` (list of sub-conditions)."""
    return runtime_evaluate_condition(cond, order_map)


async def _get_step_context(user_id: str):
    """Return (steps_sorted, order_map, hidden_step_ids, blocked_step_ids) for a user."""
    context = await survey_runtime_service.context(user_id)
    visible = runtime_visibility(context)
    return (
        [step.document for step in context.steps], runtime_order_state(context),
        set(visible.hidden_step_ids), set(visible.blocked_step_ids),
    )


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
            "survey_id": step.get("survey_id") if step else None,
            "updated_at": now_iso,
            "completed_at": now_iso,
        }
        if not (existing and existing.get("started_at")):
            update_fields["started_at"] = now_iso
        if step:
            await write_progress_revision(
                db, user_id=user_id, step=step, status="completed", data=update_fields["data"],
                actor={"role": "system"}, change_type="auto_complete",
                extra_fields={key: value for key, value in update_fields.items() if key not in {"status", "data"}},
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
# (orders post-2026-04-28 ueberholspur insertion: every theme block shifted +1)
BLOCK_DEFINITIONS = {
    "Antragstellung Approbation": (3, 4, 6),
    "Fachsprachenprüfung":        (7, 8, 10),
    "Gleichwertigkeitsprüfung":  (11, 12, 14),
    "Kenntnisprüfung":            (15, 16, 18),
    "Weiterbildung":              (22, 23, 25),
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
            await write_progress_revision(
                db, user_id=user_id, step=step, status="completed", data=data,
                actor={"role": "system"}, change_type="status_auto_skip",
                extra_fields={"completed_at": now_iso, "started_at": (existing or {}).get("started_at") or now_iso},
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
    """Percentage of the user's journey that is complete.

    Counts completed steps against the user's survey journey. Branch-hidden
    steps (e.g. upload vs. partner path) are excluded from the denominator, but
    future steps that are merely hidden until a previous milestone completes
    still count. Otherwise the linear journey would jump to 33% after the first
    of three initially visible steps.

    Steps that are skipped via `apply_anerkennungsstatus_skips` come back as
    status=completed in user_progress, so they're correctly counted as done.
    """
    steps, _, hidden_ids, _ = await _get_step_context(user_id)

    denominator_steps = _completion_denominator_steps(steps, hidden_ids)
    if not denominator_steps:
        return 0
    denominator_ids = {str(s["_id"]) for s in denominator_steps}
    completed = await db.user_progress.count_documents({
        "user_id": user_id,
        "status": "completed",
        "step_id": {"$in": list(denominator_ids)},
    })
    return round((completed / len(denominator_steps) * 100))


async def calculate_user_metrics(user_id: str) -> dict:
    """Calculate completion percentage and ETA with one step-context lookup."""
    steps, _, hidden_ids, _ = await _get_step_context(user_id)
    progress = await db.user_progress.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    progress_map = {p["step_id"]: p for p in progress}

    denominator_steps = _completion_denominator_steps(steps, hidden_ids)
    if denominator_steps:
        denominator_ids = {str(s["_id"]) for s in denominator_steps}
        completed = sum(
            1 for step_id, progress_doc in progress_map.items()
            if step_id in denominator_ids and progress_doc.get("status") == "completed"
        )
        completion_pct = round((completed / len(denominator_steps) * 100))
    else:
        completion_pct = 0

    if not steps:
        estimated_completion = None
    else:
        last_completed_at = None
        for step in steps:
            sid = str(step["_id"])
            if sid in hidden_ids:
                continue
            progress_doc = progress_map.get(sid, {})
            if progress_doc.get("status") == "completed" and progress_doc.get("completed_at"):
                try:
                    completed_at = datetime.fromisoformat(progress_doc["completed_at"])
                    if last_completed_at is None or completed_at > last_completed_at:
                        last_completed_at = completed_at
                except Exception:
                    pass
        current = last_completed_at or datetime.now(timezone.utc)
        for step in steps:
            sid = str(step["_id"])
            if sid in hidden_ids:
                continue
            progress_doc = progress_map.get(sid, {})
            if progress_doc.get("status") != "completed":
                current = add_duration(current, step.get("duration_value", 0), step.get("duration_unit", "days"))
        estimated_completion = current.date().isoformat()

    return {
        "completion_pct": completion_pct,
        "estimated_completion": estimated_completion,
    }


def _metrics_from_loaded_context(steps: list, progress: list) -> dict:
    """Pure bulk-friendly counterpart of calculate_user_metrics."""
    return runtime_calculate_metrics(
        runtime_context_from_documents(steps, progress), datetime.now(timezone.utc)
    ).as_dict()


def calculate_metrics_from_loaded_context(steps: list, progress: list) -> dict:
    """Calculate user dashboard metrics from already loaded steps/progress.

    This keeps reload/bootstrap endpoints from issuing duplicate MongoDB reads
    while sharing the same visibility and ETA logic as bulk metric calls.
    """
    return _metrics_from_loaded_context(steps, progress)


async def calculate_users_metrics(user_ids: list[str]) -> dict[str, dict]:
    """Calculate metrics for many users with three MongoDB queries total."""
    unique_ids = list(dict.fromkeys(uid for uid in user_ids if uid))
    if not unique_ids:
        return {}
    object_ids = []
    for uid in unique_ids:
        try:
            object_ids.append(ObjectId(uid))
        except Exception:
            continue
    users = await db.users.find(
        {"_id": {"$in": object_ids}}, {"survey_id": 1, "role": 1}
    ).to_list(len(object_ids) or 1)
    survey_by_user = {str(user["_id"]): user.get("survey_id") for user in users}
    survey_ids = {sid for sid in survey_by_user.values() if sid}
    step_query = {"is_active": True}
    if survey_ids:
        step_query["survey_id"] = {"$in": list(survey_ids)}
    steps = await db.steps.find(step_query).sort([("survey_id", 1), ("order", 1)]).to_list(1000)
    steps_by_survey = defaultdict(list)
    for step in steps:
        steps_by_survey[step.get("survey_id")].append(step)
    progress = await db.user_progress.find(
        {"user_id": {"$in": unique_ids}}, {"_id": 0}
    ).to_list(max(1000, len(unique_ids) * 100))
    progress_by_user = defaultdict(list)
    for row in progress:
        progress_by_user[row.get("user_id")].append(row)

    empty = {"completion_pct": 0, "estimated_completion": None}
    return {
        uid: _metrics_from_loaded_context(
            steps_by_survey.get(survey_by_user.get(uid), []),
            progress_by_user.get(uid, []),
        ) if survey_by_user.get(uid) else empty.copy()
        for uid in unique_ids
    }


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
        p = progress_map.get(sid, {})
        if p.get("status") == "completed":
            continue
        # Visibility skip: hide a step from ETA if it's hidden AND not a
        # milestone. Milestones always lead to the goal — even when their
        # decision step hasn't been picked yet, the user will eventually go
        # through one of the branches and incur the milestone duration. So
        # always count their `duration_value` toward ETA.
        if sid in hidden_ids and s.get("step_type") != "milestone":
            continue
        duration_value = s.get("duration_value", 0)
        duration_unit = s.get("duration_unit", "days")
        if duration_value > 0:
            current = add_duration(current, duration_value, duration_unit)
    return current.isoformat()
