"""
IHCA API - Main application entry point.
Shared utilities are imported from the slice packages and the remaining
composition modules. Routes are still composed in this file.
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
from collections.abc import Mapping
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, Response, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from bson import ObjectId

# Shared modules
from database import db, client
from models import (
    ProfileUpdate,
    PartnerCreate, PartnerUpdate, StepCreate, StepUpdate, StepReorder, StepFieldCreate,
    NotificationPreferences,
    PartnerSelfUpdate, PartnerBillingSettingsUpdate, StepLayoutBulk,
    StepResponse,
)
from stripe_service import (
    SECRET_FIELDS, public_stripe_status, list_customer_invoices,
    create_pending_invoice_item,
)
from slices.identity_access.auth import (
    get_jwt_secret, JWT_ALGORITHM, hash_password, verify_password,
    create_access_token, create_refresh_token, get_current_user, require_role, require_permission
)
from helpers import (
    send_email_notification, create_audit_log, notify_partner_of_new_submission,
    notify_user_awaiting_partner, notify_user_milestone_completed,
    render_email, render_notification, send_rendered_email, _partner_deep_link,
    email_notifications_service, audit_trail_service,
    calculate_completion_pct, calculate_estimated_completion,
    calculate_users_metrics, calculate_metrics_from_loaded_context,
    apply_auto_completes, _get_step_context,
    apply_anerkennungsstatus_skips, _evaluate_condition,
)
from slices.email_notifications.defaults import default_message_templates
from slices.email_notifications.router import build_email_notifications_router
from slices.step_configuration.form_builder import (
    CONTENT_FIELD_TYPES, FORM_SCHEMA_VERSION,
    migrate_database_form_configs, normalize_step_field,
)
from slices.groups_permissions.permissions import (
    ALL_PERMISSION_KEYS, PERMISSION_CATALOG, default_group_id,
    effective_permissions, ensure_permission_groups, ensure_user_role_group, has_permission,
    permission_for_admin_request, permission_for_portal_request,
    permission_group_summaries,
)
from slices.identity_access.domain import partner_is_awaiting_assignment
from slices.identity_access.repository import MongoIdentityRepository
from slices.identity_access.service import IdentityAccessService
from slices.identity_access.router import build_identity_routers, build_profile_router
from slices.groups_permissions.repository import MongoGroupsPermissionsRepository
from slices.groups_permissions.service import GroupsPermissionsService
from slices.groups_permissions.web import groups_permissions_http_error
from slices.groups_permissions.router import build_groups_permissions_router
from slices.groups_permissions.domain import validated_permissions
from slices.stripe_subscription.domain import (
    SubscriptionRuleError, partner_access_unlocked, subscription_webhook_action,
)
from infrastructure.stripe_subscription_gateway import StripeApiSubscriptionGateway
from slices.stripe_subscription.models import CheckoutIdentity, CheckoutSettings, PartnerSubscription
from slices.stripe_subscription.repository import MongoStripeSubscriptionRepository
from slices.stripe_subscription.service import StripeSubscriptionService
from slices.stripe_subscription.web import stripe_subscription_http_error
from slices.stripe_subscription.administration import (
    MongoStripeConnectionAdministrationRepository,
    StripeConnectionAdministrationService,
    subscription_partner,
)
from slices.stripe_subscription.partner_portal import (
    MongoPartnerPortalRepository,
    PartnerPortalService,
)
from slices.stripe_subscription.router import (
    build_partner_payment_router,
    build_stripe_connection_administration_router,
    build_stripe_webhook_router,
)
from slices.stripe_subscription.webhook import MongoStripeWebhookRepository, StripeWebhookService
from infrastructure.local_object_storage import LocalObjectStorage
from slices.files_storage.models import FilePrincipal
from slices.files_storage.repository import MongoFilesRepository
from slices.files_storage.service import FilesStorageService
from slices.files_storage.router import build_files_router
from slices.admin_user_management.repository import MongoAdminUserRepository
from slices.admin_user_management.service import AdminUserManagementService
from slices.admin_user_management.listing_repository import MongoAdminUserListingRepository
from slices.admin_user_management.listing_service import AdminUserListingService
from slices.admin_user_management.progress import (
    AdminUserProgressService,
    MongoAdminProgressRepository,
)
from slices.admin_user_management.router import build_admin_user_management_router
from slices.admin_reporting.repository import MongoAdminReportingRepository
from slices.admin_reporting.service import AdminReportingService
from slices.admin_reporting.router import build_admin_reporting_router
from slices.cms_public_settings.repository import MongoCmsPublicSettingsRepository
from slices.cms_public_settings.service import CmsPublicSettingsService
from slices.cms_public_settings.router import build_cms_settings_routers
from slices.step_templates.repository import MongoStepTemplateRepository
from slices.step_templates.service import StepTemplateService
from slices.step_templates.router import build_step_templates_router
from slices.survey_administration.domain import survey_view
from slices.survey_administration.repository import MongoSurveyAdministrationRepository
from slices.survey_administration.service import SurveyAdministrationService
from slices.survey_administration.web import survey_http_error
from slices.survey_administration.router import build_survey_routers
from event_system import (
    ensure_event_configs, emit_domain_event, retry_domain_event, event_system_service,
)
from slices.event_system.router import build_event_system_router
from slices.audit_trail.router import build_audit_trail_router
from slices.step_versioning.facade import (
    ensure_step_version, insert_step_version, migrate_step_answer_versioning,
    revision_view, update_step_versioned, write_progress_revision,
)
from slices.partner_billing.domain import (
    effective_partner_user_fee as _effective_partner_user_fee,
    service_step_for_partner_action as _service_step_for_partner_action,
)
from slices.partner_billing.repository import PartnerBillingRepository
from slices.partner_billing.service import PartnerBillingService
from slices.partner_assignments.repository import MongoPartnerAssignmentRepository
from slices.partner_assignments.service import PartnerAssignmentService
from slices.partner_submissions.repository import MongoPartnerSubmissionRepository
from slices.partner_submissions.service import PartnerSubmissionService
from slices.partner_insights.repository import MongoPartnerInsightsRepository
from slices.partner_insights.service import PartnerInsightsService
from slices.partner_insights.adapters import (
    AssignmentCompletionAdapter,
    SubmissionCompletionAdapter,
)
from slices.partner_workspace.repository import MongoPartnerWorkspaceRepository
from slices.partner_workspace.service import PartnerWorkspaceService, WorkspaceUserNotFound
from slices.partner_workspace.profile import MongoPartnerProfileRepository, PartnerProfileService
from slices.partner_workspace.router import (
    build_partner_workspace_command_router, build_partner_workspace_detail_router, build_partner_workspace_read_router,
    build_partner_workspace_action_router, build_partner_workspace_router,
)
from slices.partner_workspace.detail_service import PartnerWorkspaceDetailService
from slices.partner_workspace.command_repository import MongoPartnerWorkspaceCommandRepository
from slices.partner_workspace.command_service import PartnerWorkspaceCommandService
from slices.partner_workspace.action_service import PartnerWorkspaceActionService
from slices.partner_workspace.read_repository import MongoPartnerWorkspaceReadRepository
from slices.partner_workspace.read_service import PartnerWorkspaceReadService
from slices.partner_workspace.domain import (
    InvalidWorkspaceAction,
    RejectionReasonRequired,
    adjacent_visible_step,
    merge_progress_data,
    new_partner_uploads,
    partner_selection_step_id,
    revision_is_visible,
    sanitize_progress,
    validate_workspace_action,
)
from slices.partner_workspace.mappers import workspace_revision_from_document, workspace_step_from_document
from slices.partner_selection.repository import MongoPartnerSelectionRepository
from slices.partner_selection.router import build_partner_selection_router
from infrastructure.clock import system_utc_clock
from infrastructure.identifiers import uuid4_generator
from infrastructure.mongo_ids import object_id_or_none
from infrastructure.mongo_bootstrap import initialize_mongo_schema
from web.access_middleware import install_access_middleware
from web.lifecycle import lifecycle
from web.root_router import build_root_router
from slices.partner_billing.web import invoice_view as _invoice_view
from slices.document_workflow.mappers import document_workflow_context
from slices.document_workflow.repository import MongoDocumentWorkflowRepository
from slices.document_workflow.migration import migrate_document_workflows
from slices.document_workflow.service import DocumentWorkflowReadOnly, DocumentWorkflowService
from slices.document_workflow.web import document_workflow_http_error
from slices.survey_runtime.dashboard import MongoSurveyDashboardRepository, SurveyDashboardService
from slices.survey_runtime.router import (
    build_survey_estimate_router, build_survey_progress_router,
    build_survey_runtime_read_router,
)
from slices.survey_runtime.web import UserProgressUpdate
from slices.survey_runtime.progress_repository import MongoSurveyProgressRepository
from slices.survey_runtime.progress_service import SurveyProgressService
from slices.step_configuration.repository import MongoStepConfigurationRepository
from slices.step_configuration.service import StepConfigurationNotFound, StepConfigurationService
from slices.step_configuration.web import step_configuration_http_error
from slices.step_configuration.administration import (
    MongoStepAdministrationRepository,
    StepAdministrationService,
)
from slices.step_configuration.router import build_step_configuration_router
from slices.partner_administration.domain import (
    partner_admin_record, partner_update_plan, service_steps_for_partner, sorted_partner_records,
)
from slices.partner_administration.repository import MongoPartnerAdministrationRepository
from slices.partner_administration.service import PartnerAdministrationError, PartnerAdministrationService
from slices.partner_administration.web import partner_administration_http_error
from slices.partner_administration.listing import (
    MongoPartnerAdministrationListingRepository,
    PartnerAdministrationListingService,
)
from slices.partner_administration.router import build_partner_administration_router
from slices.partner_assignments.domain import (
    managed_step_ids as _typed_managed_step_ids,
    partner_work_status as _typed_partner_work_status,
)
from slices.partner_assignments.mappers import (
    flow_step_from_document as _assignment_step,
    progress_from_document as _assignment_progress,
)
from slices.partner_billing.mappers import (
    partner_from_document as _billing_partner,
    service_step_from_document as _billing_service_step,
    upload_from_document as _billing_upload,
    user_from_document as _billing_user,
)

logger = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)

# ========================
# APP & ROUTERS
# ========================
app = FastAPI()


install_access_middleware(
    app, db, permission_for_admin_request, permission_for_portal_request,
    get_current_user, has_permission, partner_is_awaiting_assignment,
)

api_router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/admin", tags=["admin"])

DEFAULT_SURVEY_SLUG = "aerzte"
PFLEGE_SURVEY_SLUG = "pflege"
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))

def _survey_payload(s: dict) -> dict:
    return survey_view(s)

def _survey_administration_service() -> SurveyAdministrationService:
    return SurveyAdministrationService(MongoSurveyAdministrationRepository(db),
                                       system_utc_clock.now_iso, DEFAULT_SURVEY_SLUG)

async def _get_default_survey() -> dict:
    return await _survey_administration_service().ensure_default()

async def _get_survey_by_slug(slug: Optional[str]) -> dict:
    try: return await _survey_administration_service().by_slug(slug)
    except Exception as error: raise survey_http_error(error)

async def _get_user_survey(user: dict, survey_slug: Optional[str] = None) -> dict:
    try: return await _survey_administration_service().for_user(user, survey_slug)
    except Exception as error: raise survey_http_error(error)

def _step_query_for_survey(survey_id: str, active_only: bool = True) -> dict:
    query = {"survey_id": survey_id, "is_deleted": {"$ne": True}}
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
        "current_version": step.get("current_version", 1),
        "is_deleted": step.get("is_deleted", False),
        "deleted_at": step.get("deleted_at"),
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

def _file_principal(user: dict) -> FilePrincipal:
    return FilePrincipal(str(user["_id"]), str(user.get("role", "user")), user.get("partner_id"))


def _files_storage_service() -> FilesStorageService:
    return FilesStorageService(
        MongoFilesRepository(db),
        LocalObjectStorage(os.environ.get("LOCAL_STORAGE_ROOT", "./data/uploads").strip(), logger),
        MAX_UPLOAD_BYTES,
    )


def _survey_dashboard_service() -> SurveyDashboardService:
    return SurveyDashboardService(
        MongoSurveyDashboardRepository(db), calculate_metrics_from_loaded_context,
    )

# ========================
# STEPS ROUTES
# ========================

def _document_workflow_state(steps: list[dict], progress: list[dict]) -> dict[str, dict]:
    """Resolve shared documents and immutable branch steps for decision blocks."""
    resolved = DocumentWorkflowService.resolve(document_workflow_context(steps, progress))
    return {step_id: step_state.as_dict() for step_id, step_state in resolved.items()}


async def _migrate_document_workflow_titles() -> int:
    return await migrate_document_workflows(db, _step_query_for_survey)


async def _assert_document_workflow_editable(user_id: str, step: Mapping[str, Any]) -> None:
    service = DocumentWorkflowService(MongoDocumentWorkflowRepository(db))
    try:
        await service.assert_editable(user_id, step.get("survey_id"), str(step.get("_id")))
    except DocumentWorkflowReadOnly as error:
        raise document_workflow_http_error(error)


async def _write_user_progress_revision(**values: Any) -> Any:
    return await write_progress_revision(db, **values)


def _survey_progress_service() -> SurveyProgressService:
    return SurveyProgressService(
        MongoSurveyProgressRepository(db), _assert_document_workflow_editable,
        _get_default_survey, _write_user_progress_revision, send_rendered_email,
        apply_anerkennungsstatus_skips, apply_auto_completes,
        system_utc_clock.now_iso, frozenset(CONTENT_FIELD_TYPES),
    )

async def _persist_partner_selection_progress(user: dict, step: dict, selection_data: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await write_progress_revision(
        db, user_id=user["_id"], step=step, status="completed", data=selection_data,
        actor={"id": user["_id"], "email": user.get("email", ""), "role": user.get("role", "user")},
        change_type="partner_selection", extra_fields={"completed_at": now},
    )

# ========================
# ADMIN ROUTES
# ========================

def _groups_permissions_service() -> GroupsPermissionsService:
    return GroupsPermissionsService(MongoGroupsPermissionsRepository(db), frozenset(ALL_PERMISSION_KEYS))


async def _validated_group_ids(group_ids: list[str], role: str) -> list[str]:
    try:
        return await _groups_permissions_service().validate_group_ids(group_ids or [], role)
    except Exception as error:
        http_error = groups_permissions_http_error(error)
        if http_error.status_code == 404:
            http_error.status_code = 400
        raise http_error


def _validated_permission_keys(values: list[str], role: str) -> list[str]:
    return validated_permissions(values, role, frozenset(ALL_PERMISSION_KEYS))


def _admin_user_management_service() -> AdminUserManagementService:
    return AdminUserManagementService(
        MongoAdminUserRepository(db), system_utc_clock.now_iso, hash_password,
        _validated_group_ids, default_group_id, _get_default_survey,
        create_audit_log, _files_storage_service().protect_owner_files,
        os.environ.get("ADMIN_EMAIL", "admin@example.com"), DEFAULT_SURVEY_SLUG,
    )


def _admin_user_listing_service() -> AdminUserListingService:
    return AdminUserListingService(
        MongoAdminUserListingRepository(db),
        _partner_work_status_for_users,
        calculate_users_metrics,
        lambda user_id: revision_view(db, user_id),
        calculate_completion_pct,
        permission_group_summaries,
        effective_permissions,
        os.environ.get("ADMIN_EMAIL", "admin@example.com"),
    )


def _admin_user_progress_service() -> AdminUserProgressService:
    return AdminUserProgressService(
        MongoAdminProgressRepository(db),
        lambda **values: write_progress_revision(db, **values),
        apply_anerkennungsstatus_skips,
        apply_auto_completes,
    )


def _step_configuration_service() -> StepConfigurationService:
    return StepConfigurationService(
        MongoStepConfigurationRepository(db, insert_step_version, update_step_versioned),
        system_utc_clock.now,
    )


def _step_administration_service() -> StepAdministrationService:
    return StepAdministrationService(
        MongoStepAdministrationRepository(db, ensure_step_version, update_step_versioned),
        system_utc_clock.now,
    )

# Admin Partners
def _partner_administration_service() -> PartnerAdministrationService:
    return PartnerAdministrationService(MongoPartnerAdministrationRepository(db))


def _partner_administration_listing_service() -> PartnerAdministrationListingService:
    return PartnerAdministrationListingService(
        MongoPartnerAdministrationListingRepository(db),
        _partner_work_status_for_users,
    )

# ========================
# PARTNER DASHBOARD ROUTES
# ========================

def _partner_billing_service() -> PartnerBillingService:
    return PartnerBillingService(
        PartnerBillingRepository(db), create_pending_invoice_item,
        id_factory=uuid4_generator.new,
        clock=system_utc_clock.now_iso,
    )


async def _admin_invoice_views(customer_id: str) -> list[dict[str, Any]]:
    try:
        payload = await list_customer_invoices(customer_id)
    except HTTPException:
        return []
    return [_invoice_view(invoice) for invoice in payload.get("data", [])]


def _admin_reporting_service() -> AdminReportingService:
    return AdminReportingService(
        MongoAdminReportingRepository(db), _admin_invoice_views,
        _usage_billing_stats, system_utc_clock.now,
    )


async def _usage_billing_stats(partner_id: str) -> dict:
    return await _partner_billing_service().stats(partner_id)


async def _record_partner_user_charge(
    partner: dict,
    target_user: dict,
    upload: dict,
    service_step: dict | None = None,
) -> dict:
    charge = await _partner_billing_service().record_upload(
        _billing_partner(partner),
        _billing_user(target_user),
        _billing_upload(upload),
        _billing_service_step(service_step),
    )
    return charge.to_document()


async def _sync_pending_partner_usage_charges(partner: dict) -> int:
    return await _partner_billing_service().sync_pending(_billing_partner(partner))


async def _sync_subscription_usage(partner_id: str) -> int:
    partner = await db.partners.find_one({"_id": ObjectId(partner_id)})
    return await _sync_pending_partner_usage_charges(partner) if partner else 0


def _stripe_subscription_service() -> StripeSubscriptionService:
    return StripeSubscriptionService(
        MongoStripeSubscriptionRepository(db), StripeApiSubscriptionGateway(),
        _sync_subscription_usage,
    )


def _stripe_connection_administration_service() -> StripeConnectionAdministrationService:
    return StripeConnectionAdministrationService(
        MongoStripeConnectionAdministrationRepository(db),
        _stripe_subscription_service(), system_utc_clock.now_iso,
    )


async def _partner_invoice_views(customer_id: str) -> list[dict[str, Any]]:
    payload = await list_customer_invoices(customer_id)
    return [_invoice_view(invoice) for invoice in payload.get("data", [])]


def _partner_portal_service() -> PartnerPortalService:
    return PartnerPortalService(
        MongoPartnerPortalRepository(db), _stripe_subscription_service(),
        _usage_billing_stats, public_stripe_status, _partner_invoice_views,
        os.environ.get("FRONTEND_URL", "http://localhost:3001"),
    )


def _stripe_webhook_service() -> StripeWebhookService:
    return StripeWebhookService(
        MongoStripeWebhookRepository(db), _sync_pending_partner_usage_charges,
        system_utc_clock.now_iso, time.time,
    )


async def _partner_submission_statuses(submissions: list[dict]) -> dict[tuple[str, str], dict]:
    """Resolve completion independently for every user/service submission."""
    return await PartnerSubmissionService(
        MongoPartnerSubmissionRepository(db),
    ).work_statuses(submissions)


def _partner_insights_service() -> PartnerInsightsService:
    return PartnerInsightsService(
        MongoPartnerInsightsRepository(db),
        SubmissionCompletionAdapter(PartnerSubmissionService(
            MongoPartnerSubmissionRepository(db),
        )),
        AssignmentCompletionAdapter(PartnerAssignmentService(
            MongoPartnerAssignmentRepository(db),
        )),
        system_utc_clock.now,
    )


def _partner_profile_service() -> PartnerProfileService:
    return PartnerProfileService(MongoPartnerProfileRepository(db))


def _partner_workspace_read_service() -> PartnerWorkspaceReadService:
    return PartnerWorkspaceReadService(
        MongoPartnerWorkspaceReadRepository(db), calculate_users_metrics,
        _partner_work_status_for_users, _partner_submission_statuses,
        _partner_user_email_value,
    )


def _partner_workspace_detail_service() -> PartnerWorkspaceDetailService:
    return PartnerWorkspaceDetailService(
        PartnerWorkspaceService(MongoPartnerWorkspaceRepository(db)),
        MongoPartnerWorkspaceReadRepository(db), lambda user_id: revision_view(db, user_id),
        calculate_completion_pct, _partner_user_email_value,
    )


async def _write_partner_workspace_revision(**values: Any) -> Any:
    return await write_progress_revision(db, **values)


async def _notify_user_milestone_safely(
    user: Mapping[str, Any], partner: Mapping[str, Any], step: Mapping[str, Any],
) -> None:
    try: await notify_user_milestone_completed(dict(user), dict(partner), dict(step))
    except Exception as error: logger.warning("notify_user_milestone_completed failed: %s", error)


def _partner_workspace_command_service() -> PartnerWorkspaceCommandService:
    return PartnerWorkspaceCommandService(
        MongoPartnerWorkspaceCommandRepository(db), _partner_work_status_for_user,
        _write_partner_workspace_revision, system_utc_clock.now_iso,
        _partner_step_action_context, apply_auto_completes,
        _notify_user_milestone_safely, send_rendered_email, _get_step_context,
    )


def _partner_workspace_action_service() -> PartnerWorkspaceActionService:
    return PartnerWorkspaceActionService(
        MongoPartnerWorkspaceCommandRepository(db), _partner_step_action_context,
        _write_partner_workspace_revision, emit_domain_event, _record_partner_user_charge,
        _service_step_for_partner_action, apply_auto_completes, _get_step_context,
        create_audit_log, system_utc_clock.now_iso,
    )


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
    return _typed_partner_work_status(
        [_assignment_step(step) for step in all_steps],
        [_assignment_progress(row) for row in progs],
        partner_id,
        partner_name,
    ).to_dict()


async def _partner_work_status_for_users(
    user_ids: list[str], partner_id: str, partner_name: str,
) -> dict[str, dict]:
    """Bulk partner milestone state with three queries regardless of user count."""
    statuses = await PartnerAssignmentService(
        MongoPartnerAssignmentRepository(db),
    ).work_statuses(user_ids, partner_id, partner_name)
    return {user_id: status.to_dict() for user_id, status in statuses.items()}


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


def _compute_partner_managed_step_ids(all_steps: list, progress: list, partner_id: str, partner_name: str) -> list[str]:
    """Return only steps this user explicitly assigned to the current partner."""
    return list(_typed_managed_step_ids(
        [_assignment_step(step) for step in all_steps],
        [_assignment_progress(row) for row in progress],
        partner_id,
        partner_name,
    ))

async def _partner_step_action_context(user_id: str, partner_id: str, partner_doc: dict | None) -> tuple[dict, list, list, list[str]]:
    partner_name = (partner_doc or {}).get("name") or ""
    workspace = await PartnerWorkspaceService(MongoPartnerWorkspaceRepository(db)).load(
        user_id, partner_id, partner_name,
    )
    target_user = {
        "_id": workspace.user.id, "name": workspace.user.name, "email": workspace.user.email,
        "survey_id": workspace.user.survey_id,
        "notification_preferences": dict(workspace.user.notification_preferences),
    }
    progress = [dict(row.document) for row in workspace.progress]
    steps = [{**step.document, "id": step.id} for step in workspace.steps]
    return target_user, progress, steps, list(workspace.managed_step_ids)


# ========================
# CMS ROUTES
# ========================

def _cms_public_settings_service() -> CmsPublicSettingsService:
    return CmsPublicSettingsService(
        MongoCmsPublicSettingsRepository(db), system_utc_clock.now_iso, frozenset(SECRET_FIELDS),
    )

# ========================
# STEP TEMPLATES (Admin)
# ========================

async def _template_version_step(step, fields, unset_fields, actor, change_type):
    await update_step_versioned(db, step, fields, unset_fields, actor, change_type)

async def _template_insert_version(step, version, actor, change_type):
    await insert_step_version(db, step, version, actor, change_type)

async def _template_write_progress(user_id, step, status, data, actor, change_type):
    await write_progress_revision(db, user_id=user_id, step=step, status=status, data=data,
                                  actor=actor, change_type=change_type)

def _step_template_service() -> StepTemplateService:
    return StepTemplateService(MongoStepTemplateRepository(db), system_utc_clock.now_iso,
                               _template_version_step, _template_insert_version, _template_write_progress)


# ========================
# ROUTER ASSEMBLY
# ========================

api_router.include_router(admin_router)
api_router.include_router(build_survey_progress_router(_survey_progress_service(), get_current_user))
api_router.include_router(build_partner_selection_router(
    MongoPartnerSelectionRepository(db), get_current_user,
    _assert_document_workflow_editable, _persist_partner_selection_progress,
    notify_partner_of_new_submission, notify_user_awaiting_partner,
    system_utc_clock.now_iso, uuid4_generator.new, logger,
))
api_router.include_router(build_survey_runtime_read_router(
    _survey_dashboard_service(), get_current_user, _get_user_survey,
    calculate_estimated_completion, _get_step_context,
))
api_router.include_router(build_survey_estimate_router(calculate_estimated_completion, require_role))
api_router.include_router(build_files_router(
    _files_storage_service(), get_current_user, _file_principal,
    lambda: str(uuid.uuid4()), system_utc_clock.now_iso, MAX_UPLOAD_BYTES,
))
survey_admin_router, survey_public_router = build_survey_routers(
    _survey_administration_service(), require_role, create_audit_log,
)
cms_content_router, cms_admin_router, public_settings_router = build_cms_settings_routers(
    _cms_public_settings_service(), require_role, require_permission, create_audit_log, public_stripe_status,
)
api_router.include_router(survey_admin_router)
api_router.include_router(survey_public_router)
api_router.include_router(cms_content_router)
api_router.include_router(cms_admin_router)
api_router.include_router(public_settings_router)
api_router.include_router(build_step_templates_router(
    _step_template_service(), require_role, create_audit_log, _get_default_survey,
))
api_router.include_router(build_event_system_router(
    event_system_service, require_role, create_audit_log, retry_domain_event,
))
api_router.include_router(build_audit_trail_router(audit_trail_service, require_role))
api_router.include_router(build_email_notifications_router(
    email_notifications_service, require_role, create_audit_log, render_email,
    render_notification, send_email_notification, system_utc_clock.now_iso,
))
api_router.include_router(build_groups_permissions_router(
    _groups_permissions_service(), require_role, create_audit_log, PERMISSION_CATALOG,
    frozenset(ALL_PERMISSION_KEYS), lambda: uuid.uuid4().hex, system_utc_clock.now_iso,
))
identity_service = IdentityAccessService(MongoIdentityRepository(db))
identity_auth_router, identity_public_router, identity_admin_router = build_identity_routers(
    identity_service, require_role, get_current_user, _auth_user_payload, _get_survey_by_slug,
    default_group_id, hash_password, verify_password, create_access_token, create_refresh_token,
    _auth_cookie_kwargs, get_jwt_secret, JWT_ALGORITHM, create_audit_log, ensure_user_role_group,
    public_stripe_status, lambda: secrets.token_urlsafe(32), send_rendered_email,
    os.environ.get("FRONTEND_URL", "http://localhost:3001"), DEFAULT_SURVEY_SLUG,
    system_utc_clock.now_iso,
)
api_router.include_router(identity_auth_router)
api_router.include_router(identity_public_router)
api_router.include_router(identity_admin_router)
api_router.include_router(build_profile_router(identity_service, get_current_user))
api_router.include_router(build_admin_user_management_router(
    _admin_user_management_service(), _admin_user_listing_service(),
    _admin_user_progress_service(), require_role, has_permission,
    lambda values: _validated_permission_keys(list(values), "user"),
    effective_permissions, create_audit_log,
))
api_router.include_router(build_partner_administration_router(
    _partner_administration_service(), _partner_administration_listing_service(),
    require_role, default_group_id, create_audit_log, system_utc_clock.now_iso,
    _sync_pending_partner_usage_charges,
))
api_router.include_router(build_step_configuration_router(
    _step_configuration_service(), _step_administration_service(), require_role,
    _get_survey_by_slug, _get_default_survey, _admin_step_payload, create_audit_log,
))
api_router.include_router(build_admin_reporting_router(
    _admin_reporting_service(), require_role,
))
api_router.include_router(build_stripe_connection_administration_router(
    _stripe_connection_administration_service(), require_role, create_audit_log,
))
api_router.include_router(build_partner_payment_router(
    _partner_portal_service(), require_role, create_audit_log, system_utc_clock.now_iso,
))
api_router.include_router(build_stripe_webhook_router(_stripe_webhook_service()))
api_router.include_router(build_partner_workspace_router(
    _partner_profile_service(), identity_service, _partner_insights_service(),
    require_role, create_audit_log, system_utc_clock.now_iso,
))
api_router.include_router(build_partner_workspace_read_router(
    _partner_workspace_read_service(), require_role,
))
api_router.include_router(build_partner_workspace_detail_router(
    _partner_workspace_detail_service(), require_role,
))
api_router.include_router(build_partner_workspace_command_router(
    _partner_workspace_command_service(), require_role,
))
api_router.include_router(build_partner_workspace_action_router(
    _partner_workspace_action_service(), require_role,
))

api_router.include_router(build_root_router())

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

async def startup() -> None:
    await initialize_mongo_schema(db)
    await audit_trail_service.initialize()
    try:
        _files_storage_service().initialize()
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
    await _cms_public_settings_service().seed(_default_cms, _default_cms_en, {
        "site_title": "IHCA", "logo_text": "IHCA", "logo_bold_part": "IH", "logo_light_part": "CA",
        "contact_email": "", "footer_text": "", "primary_color": "#114f55",
        "meta_description": "IHCA — international health connect association. Praktizieren in Deutschland.",
    })
    # Seed email templates (idempotent — won't overwrite admin edits)
    try:
        _now = datetime.now(timezone.utc).isoformat()
        await email_notifications_service.seed(tuple(default_message_templates().values()), _now)
    except Exception as _e:
        logger.warning(f"email_templates seed failed: {_e}")
    try:
        await ensure_event_configs()
    except Exception as _e:
        logger.warning(f"event config seed failed: {_e}")
    migration = await migrate_step_answer_versioning(db)
    logger.info("Step/answer version migration: %s", migration)
    logger.info("Startup seeding complete")

async def shutdown_db_client() -> None:
    client.close()


app.router.lifespan_context = lifecycle(startup, shutdown_db_client)
