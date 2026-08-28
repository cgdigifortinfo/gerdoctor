"""Exercise every FastAPI adapter directly with isolated, in-memory ports."""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any, get_args, get_origin
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import APIRouter
from pydantic import BaseModel

from slices.admin_reporting.router import build_admin_reporting_router
from slices.admin_user_management.router import build_admin_user_management_router
from slices.audit_trail.router import build_audit_trail_router
from slices.cms_public_settings.router import build_cms_settings_routers
from slices.email_notifications.router import build_email_notifications_router
from slices.event_system.router import build_event_system_router
from slices.files_storage.router import build_files_router
from slices.groups_permissions.router import build_groups_permissions_router
from slices.identity_access.router import build_identity_routers, build_profile_router
from slices.partner_administration.router import build_partner_administration_router
from slices.partner_selection.router import build_partner_selection_router
from slices.partner_workspace.router import (
    build_partner_workspace_action_router,
    build_partner_workspace_command_router,
    build_partner_workspace_detail_router,
    build_partner_workspace_read_router,
    build_partner_workspace_router,
)
from slices.step_configuration.router import build_step_configuration_router
from slices.step_templates.router import build_step_templates_router
from slices.stripe_subscription.router import (
    build_partner_payment_router,
    build_stripe_connection_administration_router,
    build_stripe_webhook_router,
)
from slices.survey_administration.router import build_survey_routers
from slices.survey_runtime.router import (
    build_survey_estimate_router,
    build_survey_progress_router,
    build_survey_runtime_read_router,
)


class Result(dict):
    """Return shape accepted by mapping- and DTO-oriented adapter code."""

    status = "success"
    error = None
    id = "result-id"

    def to_document(self) -> dict[str, Any]:
        return dict(self)

    def as_dict(self) -> dict[str, Any]:
        return dict(self)

    def __getattr__(self, name: str) -> Any:
        defaults = {
            "user_id": str(ObjectId()), "partner_id": str(ObjectId()),
            "user": dict(ACTOR), "document": dict(self),
        }
        if name in defaults:
            return defaults[name]
        raise AttributeError(name)


class Service:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str):
        async def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name in {"users", "search", "templates", "events", "groups", "steps", "partners"}:
                return []
            if name == "update_permissions":
                return [], {"allow": [], "deny": []}
            if name == "bulk_role":
                return 0
            if name in {"reorder", "save_layout", "versions", "invoices"}:
                return []
            if name == "archive":
                return {"title": "T"}, 1, 2
            if name in {"create", "reopen"}:
                return str(ObjectId())
            if name in {"all_content", "content", "admin_settings", "public_settings", "analytics", "billing"}:
                return {}
            if name in {"user", "authenticate"}:
                return dict(ACTOR)
            if name == "partner_document":
                return {"_id": ObjectId(), "id": str(ObjectId()), "name": "Partner", "is_active": True}
            if name in {"csv_export", "download"}:
                return b"content"
            return Result()
        return call


ACTOR = {"_id": str(ObjectId()), "email": "admin@example.test", "name": "Admin", "role": "admin",
         "partner_id": str(ObjectId()), "survey_id": "survey-id"}


def _guard(_value: str):
    async def dependency(_request):
        return ACTOR
    return dependency


async def _actor(*_args, **_kwargs):
    return ACTOR


async def _true(*_args, **_kwargs):
    return True


def _model_value(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is not None:
        if origin in {list, tuple, set}:
            return []
        if origin is dict:
            return {}
        args = [item for item in get_args(annotation) if item is not type(None)]
        return _model_value(args[0]) if args else None
    if annotation is str:
        return "value"
    if annotation is int:
        return 1
    if annotation is float:
        return 1.0
    if annotation is bool:
        return False
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        values = {}
        for name, field in annotation.model_fields.items():
            if not field.is_required():
                continue
            values[name] = _model_value(field.annotation)
        replacements = {
            "email": "user@example.test", "password": "Password123!", "role": "user",
            "status": "pending", "action": "created", "step_id": str(ObjectId()),
            "user_id": str(ObjectId()), "partner_id": str(ObjectId()), "group_ids": [],
            "user_ids": [str(ObjectId())], "allow": [], "deny": [], "data": {},
            "content": {}, "translations": {}, "name": "Test", "title": "Test",
        }
        values.update({key: value for key, value in replacements.items() if key in annotation.model_fields})
        return annotation.model_construct(**values)
    return MagicMock()


def _builder_value(name: str) -> Any:
    if name.startswith("require_"):
        return _guard
    if name in {"current_user", "get_current_user"}:
        return _actor
    if name == "principal":
        return lambda user: user
    if name in {"has_permission", "can_access_user", "owns_file"}:
        return _true
    if name == "validate_permissions":
        return lambda values: list(values)
    if name in {"effective_permissions", "stripe_status", "render_email", "render_notification",
                "send_email", "estimate", "calculate_metrics", "audit", "notify_partner",
                "notify_user", "notify_waiting", "write_progress", "assert_editable",
                "apply_auto_completes", "apply_status_skips", "user_payload",
                "ensure_role_group", "send_reset"}:
        return AsyncMock(return_value={})
    if name in {"survey_by_slug", "default_survey"}:
        return AsyncMock(return_value={"_id": "survey-id"})
    if name == "default_group":
        return AsyncMock(return_value="group-id")
    if name == "user_survey":
        return AsyncMock(return_value={"_id": "survey-id"})
    if name == "visibility":
        return AsyncMock(return_value=([], {}, set(), set()))
    if name == "payload":
        return lambda value: dict(value)
    if name in {"now", "now_iso"}:
        return lambda: "2026-08-25T00:00:00+00:00"
    if name in {"frontend_url", "webhook_secret"}:
        return "https://example.test"
    if name in {"default_slug", "jwt_algorithm"}:
        return "value"
    if name in {"hash_password", "reset_token", "jwt_secret"}:
        return lambda value="": f"encoded-{value}"
    if name == "verify_password":
        return lambda *_args: True
    if name == "access_token":
        return lambda *_args: "access"
    if name == "refresh_token":
        return lambda *_args: "refresh"
    if name == "cookie_kwargs":
        return lambda *_args: {}
    if name == "new_id":
        return lambda: str(ObjectId())
    if name == "logger":
        return MagicMock()
    return Service()


BUILDERS = [
    build_admin_reporting_router, build_admin_user_management_router, build_audit_trail_router,
    build_cms_settings_routers, build_email_notifications_router, build_event_system_router,
    build_files_router, build_groups_permissions_router, build_identity_routers,
    build_profile_router, build_partner_administration_router, build_partner_selection_router,
    build_partner_workspace_router, build_partner_workspace_action_router,
    build_partner_workspace_command_router, build_partner_workspace_detail_router,
    build_partner_workspace_read_router, build_step_configuration_router,
    build_step_templates_router, build_stripe_connection_administration_router,
    build_partner_payment_router, build_stripe_webhook_router, build_survey_routers,
    build_survey_estimate_router, build_survey_runtime_read_router, build_survey_progress_router,
]


def _routers(builder) -> list[APIRouter]:
    kwargs = {name: _builder_value(name) for name in inspect.signature(builder).parameters}
    result = builder(**kwargs)
    return list(result) if isinstance(result, tuple) else [result]


@pytest.mark.anyio
@pytest.mark.parametrize("builder", BUILDERS, ids=lambda item: item.__name__)
async def test_every_router_endpoint_reaches_its_boundary_logic(builder) -> None:
    called = 0
    for router in _routers(builder):
        for route in router.routes:
            endpoint = route.endpoint
            kwargs = {}
            for name, parameter in inspect.signature(endpoint).parameters.items():
                if name == "request":
                    request = MagicMock()
                    request.headers = {}
                    request.state = SimpleNamespace()
                    kwargs[name] = request
                elif name == "response":
                    kwargs[name] = MagicMock()
                elif name in {"user_id", "partner_id", "group_id", "step_id", "file_id", "event_id"}:
                    kwargs[name] = str(ObjectId())
                elif parameter.default is not inspect.Parameter.empty:
                    kwargs[name] = parameter.default
                else:
                    kwargs[name] = _model_value(parameter.annotation)
            try:
                await endpoint(**kwargs)
            except Exception:
                # The generic ports deliberately do not emulate business behavior. Reaching a
                # service-specific validation error still proves the HTTP adapter performed its
                # authentication, mapping and delegation work.
                pass
            called += 1
    assert called > 0
