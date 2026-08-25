"""FastAPI routes for account lifecycle, sessions and impersonation."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any
import jwt
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, Response
from slices.identity_access.service import IdentityAccessService
from slices.identity_access.web import (
    ForgotPassword, NotificationPreferences, PartnerRegister, ProfileUpdate,
    ResetPassword, UserLogin, UserRegister, account_http_error,
)

Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Payload = Callable[[dict[str, Any], str | None], Awaitable[dict[str, Any]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]

def build_identity_routers(service: IdentityAccessService, require_role: Guard,
    current_user: Callable[[Request], Awaitable[dict[str, Any]]], user_payload: Payload,
    survey_by_slug: Callable[[str | None], Awaitable[dict[str, Any]]],
    default_group: Callable[[str], Awaitable[str | None]], hash_password: Callable[[str], str],
    verify_password: Callable[[str,str], bool], access_token: Callable[[str,str,str], str],
    refresh_token: Callable[[str], str], cookie_kwargs: Callable[[int], dict[str, Any]],
    jwt_secret: Callable[[], str], jwt_algorithm: str, audit: Audit,
    ensure_role_group: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    stripe_status: Callable[[], Awaitable[dict[str, Any]]], reset_token: Callable[[], str],
    send_reset: Callable[[str,str,Mapping[str,Any]], Awaitable[Any]], frontend_url: str,
    default_slug: str, now_iso: Callable[[], str]) -> tuple[APIRouter, APIRouter, APIRouter]:
    auth=APIRouter(prefix="/auth",tags=["auth"]); public=APIRouter(tags=["registration"]); admin=APIRouter(prefix="/admin",tags=["admin"])
    def cookies(response: Response, user_id: str, email: str, role: str) -> str:
        token=access_token(user_id,email,role); response.set_cookie("access_token",token,**cookie_kwargs(7200))
        response.set_cookie("refresh_token",refresh_token(user_id),**cookie_kwargs(604800)); return token
    @auth.post("/register")
    async def register(data: UserRegister,response: Response) -> dict[str,Any]:
        survey=await survey_by_slug(data.survey_slug); group=await default_group("user")
        try: account=await service.register_user(data.model_dump(),survey,group,hash_password(data.password),now_iso(),default_slug)
        except Exception as error: raise account_http_error(error)
        token=cookies(response,account.user_id,str(data.email).lower(),"user"); return await user_payload(account.user,token)
    @public.get("/partner-registration/config")
    async def partner_config() -> dict[str,Any]: return {"registration_enabled":True,"stripe":await stripe_status()}
    @public.post("/partner-registration")
    async def register_partner(data: PartnerRegister,response: Response) -> dict[str,Any]:
        group=await default_group("partner")
        try: account=await service.register_partner(data.model_dump(),group,hash_password(data.password),now_iso())
        except Exception as error: raise account_http_error(error)
        email=str(data.email).lower(); await audit(account.user_id,email,"partner_self_registration","partner",account.partner_id or "",{"company_name":data.company_name})
        token=cookies(response,account.user_id,email,"partner")
        return {"user":await user_payload(account.user,token),"partner_id":account.partner_id,"status":"pending"}
    @auth.post("/login")
    async def login(data: UserLogin,request: Request,response: Response) -> dict[str,Any]:
        ip=request.client.host if request.client else "unknown"
        try: user=await service.authenticate(str(data.email),data.password,ip,verify_password,datetime.now(timezone.utc))
        except Exception as error: raise account_http_error(error)
        token=cookies(response,str(user["_id"]),str(user["email"]),str(user["role"])); return await user_payload(user,token)
    @auth.post("/logout")
    async def logout(response: Response) -> dict[str,str]:
        response.delete_cookie("access_token",path="/"); response.delete_cookie("refresh_token",path="/"); return {"message":"Logged out"}
    @auth.get("/me")
    async def me(request: Request) -> dict[str,Any]: return await user_payload(await current_user(request),None)
    @auth.post("/refresh")
    async def refresh(request: Request,response: Response) -> dict[str,str]:
        token=request.cookies.get("refresh_token")
        if not token: raise HTTPException(401,"No refresh token")
        try:
            claims=jwt.decode(token,jwt_secret(),algorithms=[jwt_algorithm])
            if claims.get("type") != "refresh": raise HTTPException(401,"Invalid token type")
            user=await service.user(claims["sub"])
            if not user: raise HTTPException(401,"User not found")
            response.set_cookie("access_token",access_token(str(user["_id"]),str(user["email"]),str(user["role"])),**cookie_kwargs(7200))
            return {"message":"Token refreshed"}
        except jwt.ExpiredSignatureError: raise HTTPException(401,"Refresh token expired")
        except jwt.InvalidTokenError: raise HTTPException(401,"Invalid refresh token")
    @auth.post("/forgot-password")
    async def forgot(data: ForgotPassword) -> dict[str,str]:
        token=reset_token(); user=await service.begin_password_reset(str(data.email),token,datetime.now(timezone.utc))
        if user:
            link=f"{frontend_url}/reset-password?token={token}"
            await send_reset(str(data.email).lower(),"user_password_reset",{"reset_link":link,"user_name":user.get("name","")})
        return {"message":"If an account exists, a reset link has been sent"}
    @auth.post("/reset-password")
    async def reset(data: ResetPassword) -> dict[str,str]:
        try: await service.reset_password(data.token,hash_password(data.new_password),datetime.now(timezone.utc))
        except Exception as error: raise account_http_error(error)
        return {"message":"Password reset successful"}
    @admin.post("/impersonate/{user_id}")
    async def impersonate(user_id: str,request: Request) -> dict[str,Any]:
        actor=await require_role("admin")(request)
        target=await service.user(user_id)
        if not target: raise HTTPException(404,"User not found")
        target=await ensure_role_group(target); token=access_token(str(target["_id"]),str(target["email"]),str(target["role"]))
        await audit(actor["_id"],actor["email"],"impersonate","user",str(target["_id"]),{"target_email":target["email"]})
        return {"access_token":token,"user":await user_payload(target,None)}
    return auth,public,admin


def build_profile_router(
    service: IdentityAccessService,
    current_user: Callable[[Request], Awaitable[dict[str, Any]]],
) -> APIRouter:
    router = APIRouter(tags=["profile"])

    @router.get("/profile")
    async def profile(request: Request) -> dict[str, Any]:
        user = await current_user(request)
        return {"profile": user.get("profile", {}), "name": user["name"], "email": user["email"]}

    @router.put("/profile")
    async def update_profile(data: ProfileUpdate, request: Request) -> dict[str, str]:
        user = await current_user(request)
        await service.update_profile(user["_id"], data.model_dump())
        return {"message": "Profile updated"}

    @router.get("/notifications/preferences")
    async def preferences(request: Request) -> dict[str, Any]:
        user = await current_user(request)
        return dict(user.get("notification_preferences") or {
            "email_on_step_enter": True,
            "email_on_step_edit": False,
            "email_on_step_leave": True,
        })

    @router.put("/notifications/preferences")
    async def update_preferences(
        data: NotificationPreferences, request: Request,
    ) -> dict[str, str]:
        user = await current_user(request)
        await service.update_notification_preferences(user["_id"], data.model_dump())
        return {"message": "Notification preferences updated"}

    return router
