"""Close the remaining HTTP-adapter branches with explicit port outcomes."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from bson import ObjectId
from fastapi import HTTPException

from slices.admin_user_management.router import build_admin_user_management_router
from slices.admin_user_management.progress import AdminProgressStepNotFound
from slices.admin_user_management.web import AdminUserCreate, AdminUserProgressUpdate, BulkRoleUpdate, UserPermissionsUpdate
from slices.event_system.router import build_event_system_router
from slices.files_storage.router import build_files_router
from slices.groups_permissions.router import build_groups_permissions_router
from slices.groups_permissions.web import PermissionGroupCreate, PermissionGroupUpdate
from slices.identity_access.router import build_identity_routers
from slices.identity_access.web import ForgotPassword, PartnerRegister, ResetPassword, UserLogin, UserRegister
from slices.partner_administration.router import build_partner_administration_router
from slices.partner_administration.service import PartnerAdministrationError
from slices.partner_administration.web import PartnerUpdate
from slices.step_configuration.router import build_step_configuration_router
from slices.step_configuration.administration import StepAdministrationInvalidId, StepAdministrationNotFound
from slices.step_configuration.service import StepConfigurationNotFound
from slices.step_configuration.web_models import StepUpdate
from slices.step_templates.router import build_step_templates_router
from slices.survey_administration.router import build_survey_routers
from slices.survey_administration.web import SurveyCreate, SurveyUpdate
from slices.survey_runtime.router import build_survey_estimate_router
from slices.files_storage.domain import FileRuleError


ACTOR = {"_id": str(ObjectId()), "email": "admin@test", "role": "admin"}


def guard(*_roles):
    async def dependency(_request): return ACTOR
    return dependency


def endpoint(router, name):
    return next(route.endpoint for route in router.routes if route.name == name)


@pytest.mark.anyio
async def test_admin_user_management_success_and_failure_boundaries() -> None:
    result = SimpleNamespace(to_document=lambda: {"id": "u"})
    service = SimpleNamespace(
        create=AsyncMock(return_value=result), update_permissions=AsyncMock(return_value=(["g"], {"allow": [], "deny": []})),
        user=AsyncMock(return_value={}), bulk_role=AsyncMock(return_value=2), change_role=AsyncMock(), archive=AsyncMock(),
    )
    listing = SimpleNamespace(detail=AsyncMock(return_value=None))
    progress = SimpleNamespace(update=AsyncMock())
    permission = AsyncMock(return_value=False)
    router = build_admin_user_management_router(service, listing, progress, guard, permission, lambda x: list(x), AsyncMock(return_value=[]), AsyncMock())
    request = MagicMock()
    create = AdminUserCreate.model_construct(email="x@test", password="password", name="X", role="admin", group_ids=[], partner_id=None, survey_id=None)
    with pytest.raises(HTTPException): await endpoint(router, "create")(create, request)
    permission.return_value = True
    assert await endpoint(router, "create")(create, request) == {"id": "u"}
    service.create.side_effect = RuntimeError()
    with pytest.raises(HTTPException): await endpoint(router, "create")(create, request)
    with pytest.raises(HTTPException):
        await endpoint(router, "permissions")("bad", UserPermissionsUpdate.model_construct(group_ids=[], allow=[], deny=[]), request)
    with pytest.raises(HTTPException): await endpoint(router, "detail")("u", request)
    progress.update.side_effect = AdminProgressStepNotFound()
    with pytest.raises(HTTPException): await endpoint(router, "update_progress")("u", AdminUserProgressUpdate.model_construct(step_id="s", status="done", data={}), request)
    progress.update.side_effect = None
    service.update_permissions.side_effect = RuntimeError()
    with pytest.raises(HTTPException): await endpoint(router, "permissions")(str(ObjectId()), UserPermissionsUpdate.model_construct(group_ids=[], allow=[], deny=[]), request)
    service.update_permissions.side_effect = None
    for method, mock, args in (
        ("bulk_role", service.bulk_role, (BulkRoleUpdate.model_construct(user_ids=["u"], role="user"), request)),
        ("role", service.change_role, ("u", "user", request)), ("archive", service.archive, ("u", request)),
    ):
        mock.side_effect = RuntimeError()
        with pytest.raises(HTTPException): await endpoint(router, method)(*args)


@pytest.mark.anyio
async def test_event_files_and_groups_error_and_success_boundaries() -> None:
    request = MagicMock(); request.scope = {"headers": []}
    events = SimpleNamespace(update_config=AsyncMock(side_effect=RuntimeError()))
    router = build_event_system_router(events, guard, AsyncMock(), AsyncMock(side_effect=ValueError()))
    with pytest.raises(HTTPException): await endpoint(router, "update_config")("x", SimpleNamespace(model_dump=lambda **_: {}), request)
    with pytest.raises(HTTPException): await endpoint(router, "retry_event")("x", request)
    retry = AsyncMock(return_value={"id": "x"}); router = build_event_system_router(events, guard, AsyncMock(), retry)
    assert await endpoint(router, "retry_event")("x", request) == {"id": "x"}

    upload = MagicMock(filename="x", content_type="text/plain"); upload.read = AsyncMock(return_value=b"x")
    stored = SimpleNamespace(data=b"x", content_type="text/plain")
    files = SimpleNamespace(upload=AsyncMock(return_value=SimpleNamespace(id="f", filename="x", path="/f")), download=AsyncMock(return_value=stored))
    current = AsyncMock(return_value=ACTOR)
    fr = build_files_router(files, current, lambda x: x, lambda: "f", lambda: "now", 10)
    assert await endpoint(fr, "upload")(request, upload)
    assert (await endpoint(fr, "download")("f", request, "token")).body == b"x"
    files.upload.side_effect = FileRuleError("bad")
    with pytest.raises(HTTPException): await endpoint(fr, "upload")(request, upload)
    files.download.side_effect = FileRuleError("bad")
    with pytest.raises(HTTPException): await endpoint(fr, "download")("f", request, None)
    current.side_effect = HTTPException(403)
    with pytest.raises(HTTPException): await endpoint(fr, "download")("f", request, None)

    service = SimpleNamespace(
        create=AsyncMock(return_value={"_id": "g", "name": "G", "description": "", "role": "user", "permissions": []}),
        update=AsyncMock(return_value=({"_id": "g", "name": "G", "description": "", "role": "user", "permissions": []}, 1)), delete=AsyncMock(return_value="G"),
    )
    gr = build_groups_permissions_router(service, guard, AsyncMock(), [], frozenset(), lambda: "g", lambda: "now")
    assert await endpoint(gr, "create")(PermissionGroupCreate.model_construct(name="G", description="", role="user", permissions=[]), request)
    assert await endpoint(gr, "update")("g", PermissionGroupUpdate.model_construct(name="G", description=None, role=None, permissions=None), request)
    for method, mock, args in (("create", service.create, (PermissionGroupCreate.model_construct(name="G", description="", role="user", permissions=[]), request)), ("update", service.update, ("g", PermissionGroupUpdate.model_construct(name=None, description=None, role=None, permissions=None), request)), ("delete", service.delete, ("g", request))):
        mock.side_effect = RuntimeError()
        with pytest.raises(HTTPException): await endpoint(gr, method)(*args)


@pytest.mark.anyio
async def test_identity_all_exception_and_refresh_paths(monkeypatch) -> None:
    account = SimpleNamespace(user_id="u", partner_id="p", user={"_id": "u", "email": "x@test", "role": "user"})
    service = SimpleNamespace(register_user=AsyncMock(side_effect=RuntimeError()), register_partner=AsyncMock(side_effect=RuntimeError()), authenticate=AsyncMock(side_effect=RuntimeError()), user=AsyncMock(return_value=None), begin_password_reset=AsyncMock(return_value={"name": "X"}), reset_password=AsyncMock(side_effect=RuntimeError()))
    args = (service, guard, AsyncMock(), AsyncMock(return_value={}), AsyncMock(return_value={"_id": "s"}), AsyncMock(return_value="g"), lambda x: x, lambda *_: True, lambda *_: "access", lambda *_: "refresh", lambda *_: {}, lambda: "secret", "HS256", AsyncMock(), AsyncMock(), AsyncMock(return_value={}), lambda: "reset", AsyncMock(), "https://front", "default", lambda: "now")
    auth, public, admin = build_identity_routers(*args); response = MagicMock(); request = MagicMock(); request.client = None; request.cookies = {}
    models = [(auth, "register", UserRegister.model_construct(email="x@test", password="p", survey_slug=None), (response,)), (public, "register_partner", PartnerRegister.model_construct(email="x@test", password="p", company_name="C"), (response,)), (auth, "login", UserLogin.model_construct(email="x@test", password="p"), (request, response)), (auth, "reset", ResetPassword.model_construct(token="t", new_password="p"), ())]
    for router, name, model, rest in models:
        with pytest.raises(HTTPException): await endpoint(router, name)(model, *rest)
    with pytest.raises(HTTPException): await endpoint(auth, "refresh")(request, response)
    request.cookies = {"refresh_token": "t"}
    monkeypatch.setattr(jwt, "decode", lambda *_a, **_k: {"type": "wrong", "sub": "u"})
    with pytest.raises(HTTPException): await endpoint(auth, "refresh")(request, response)
    monkeypatch.setattr(jwt, "decode", lambda *_a, **_k: {"type": "refresh", "sub": "u"})
    with pytest.raises(HTTPException): await endpoint(auth, "refresh")(request, response)
    service.user.return_value = {"_id": "u", "email": "x@test", "role": "user"}
    assert await endpoint(auth, "refresh")(request, response) == {"message": "Token refreshed"}
    monkeypatch.setattr(jwt, "decode", MagicMock(side_effect=jwt.ExpiredSignatureError()))
    with pytest.raises(HTTPException): await endpoint(auth, "refresh")(request, response)
    monkeypatch.setattr(jwt, "decode", MagicMock(side_effect=jwt.InvalidTokenError()))
    with pytest.raises(HTTPException): await endpoint(auth, "refresh")(request, response)
    assert await endpoint(auth, "forgot")(ForgotPassword.model_construct(email="x@test"))
    service.user.return_value = None
    with pytest.raises(HTTPException): await endpoint(admin, "impersonate")("u", request)
    service.user.return_value = {"_id": "u", "email": "x@test", "role": "user"}
    assert (await endpoint(admin, "impersonate")("u", request))["access_token"] == "access"


@pytest.mark.anyio
async def test_partner_step_template_and_survey_error_mappings() -> None:
    request = MagicMock(); audit = AsyncMock()
    partner = SimpleNamespace(update=AsyncMock(return_value={"updated_at": "now", "stripe_customer_id": "c", "stripe_subscription_id": "s"}), delete=AsyncMock(), link_user=AsyncMock(), unlink_user=AsyncMock())
    pr = build_partner_administration_router(partner, MagicMock(), guard, AsyncMock(return_value="g"), audit, lambda: "now", AsyncMock())
    update = PartnerUpdate.model_construct(name="P")
    assert await endpoint(pr, "update")("p", update, request)
    for method, args in (("update", ("p", update, request)), ("delete", ("p", request)), ("link", ("p", "u", request)), ("unlink", ("p", request))):
        getattr(partner, {"link": "link_user", "unlink": "unlink_user"}.get(method, method)).side_effect = PartnerAdministrationError()
        with pytest.raises(HTTPException): await endpoint(pr, method)(*args)
    partner.delete.side_effect = None; partner.delete.return_value = SimpleNamespace(partner_name="P")
    partner.link_user.side_effect = None; partner.link_user.return_value = "U"
    partner.unlink_user.side_effect = None
    assert await endpoint(pr, "delete")("p", request)
    assert await endpoint(pr, "link")("p", "u", request)
    assert await endpoint(pr, "unlink")("p", request)

    commands = SimpleNamespace(update=AsyncMock(side_effect=StepConfigurationNotFound()))
    administration = SimpleNamespace(versions=AsyncMock(), archive=AsyncMock())
    sr = build_step_configuration_router(commands, administration, guard, AsyncMock(return_value={"_id": "s"}), AsyncMock(return_value={"_id": "s"}), dict, audit)
    with pytest.raises(HTTPException): await endpoint(sr, "update")("s", StepUpdate.model_construct(), request)
    commands.update.side_effect = None; commands.update.return_value = (1, 2)
    assert await endpoint(sr, "update")("s", StepUpdate.model_construct(title="New"), request)
    administration.steps = AsyncMock(return_value=[])
    assert await endpoint(sr, "steps")(request, None, "slug", False) == []
    assert await endpoint(sr, "steps")(request, None, None, False) == []
    for error in (StepAdministrationInvalidId(), StepAdministrationNotFound()):
        administration.versions.side_effect = error
        with pytest.raises(HTTPException): await endpoint(sr, "versions")("s", request)
    administration.archive.side_effect = StepAdministrationNotFound()
    with pytest.raises(HTTPException): await endpoint(sr, "archive")("s", request)
    administration.archive.side_effect = None; administration.archive.return_value = ({}, None, None)
    assert await endpoint(sr, "archive")("s", request) == {"message": "Step already archived"}

    templates = SimpleNamespace(delete=AsyncMock(side_effect=RuntimeError()), create_from_step=AsyncMock(side_effect=RuntimeError()), apply=AsyncMock(side_effect=RuntimeError()))
    tr = build_step_templates_router(templates, guard, audit, AsyncMock(return_value={"_id": "s"}))
    for method, args in (("delete", ("t", request)), ("from_step", ("s", request, "N", "")), ("apply", ("t", request, 1, None))):
        with pytest.raises(HTTPException): await endpoint(tr, method)(*args)
    templates.apply.side_effect = None; templates.apply.return_value = SimpleNamespace(step_id="s")
    assert await endpoint(tr, "apply")("t", request, 1, None) == {"id": "s", "message": "Template applied as new step"}

    survey = SimpleNamespace(create=AsyncMock(side_effect=RuntimeError()), update=AsyncMock(side_effect=RuntimeError()))
    ar, _ = build_survey_routers(survey, guard, audit)
    with pytest.raises(HTTPException): await endpoint(ar, "create_survey")(SurveyCreate.model_construct(name="S", slug="s", description="", audience="", is_active=True, is_default=False, theme={}), request)
    with pytest.raises(HTTPException): await endpoint(ar, "update_survey")("s", SurveyUpdate.model_construct(), request)
    estimate_router = build_survey_estimate_router(AsyncMock(return_value="tomorrow"), guard)
    assert await endpoint(estimate_router, "estimated_completion")("u", request) == {"estimated_completion": "tomorrow"}
