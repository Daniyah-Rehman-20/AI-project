"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.core.security import get_current_user_id
from app.dependencies import DbSession
from app.modules.auth.schemas import (
    LoginRequest,
    MessageResponse,
    OAuthStartResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_service(db: DbSession) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    db: DbSession,
) -> TokenResponse:
    """Register a new user (e.g. analyst@example.com)."""
    return await AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: DbSession,
) -> TokenResponse:
    return await AuthService(db).login(
        payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    db: DbSession,
) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: RefreshRequest,
    db: DbSession,
) -> MessageResponse:
    await AuthService(db).logout(payload.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: DbSession,
    user_id=Depends(get_current_user_id),
) -> UserResponse:
    return await AuthService(db).get_me(user_id)


@router.get("/oauth/google", response_model=OAuthStartResponse)
async def google_oauth_start(db: DbSession) -> OAuthStartResponse:
    return await AuthService(db).google_oauth_start()


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    request: Request,
    db: DbSession,
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    tokens = await AuthService(db, settings).google_oauth_callback(
        code,
        state,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    redirect_url = (
        f"{settings.app_frontend_url}/login?"
        f"access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    )
    return RedirectResponse(url=redirect_url)
