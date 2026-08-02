"""Authentication business logic."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.cache import cache_delete, cache_get, cache_set
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    LoginRequest,
    OAuthStartResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = get_logger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repo = AuthRepository(db)

    def _hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _build_token_response(self, user: User, refresh_token: str) -> TokenResponse:
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"role": user.role.name if user.role else "viewer"},
        )
        expires_minutes = self.settings.jwt_access_token_expire_minutes
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_minutes * 60,
        )

    def _user_response(self, user: User) -> UserResponse:
        permissions: list[str] = []
        if user.role and user.role.permissions:
            permissions = list(user.role.permissions)
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role_name=user.role.name if user.role else "viewer",
            permissions=permissions,
            created_at=user.created_at,
        )

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        existing = await self.repo.get_by_email(payload.email)
        if existing:
            raise ConflictError("Email already registered")

        role = await self.repo.get_default_role()
        if role is None:
            raise ConflictError("Default role not configured")

        user = await self.repo.create_user(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role_id=role.id,
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days)
        await self.repo.create_session(
            user_id=user.id,
            refresh_token_hash=self._hash_refresh_token(refresh_token),
            expires_at=expires_at,
        )
        await self.db.commit()
        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return self._build_token_response(user, refresh_token)

    async def login(
        self,
        payload: LoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        user = await self.repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        refresh_token = create_refresh_token(subject=str(user.id))
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days)
        await self.repo.create_session(
            user_id=user.id,
            refresh_token_hash=self._hash_refresh_token(refresh_token),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.db.commit()
        logger.info("user_logged_in", user_id=str(user.id))
        return self._build_token_response(user, refresh_token)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        token_hash = self._hash_refresh_token(refresh_token)
        session = await self.repo.get_session_by_hash(token_hash)
        if session is None:
            raise UnauthorizedError("Invalid refresh token")
        if session.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Refresh token expired")

        user = session.user
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        await self.repo.revoke_session(session)
        new_refresh = create_refresh_token(subject=str(user.id))
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days)
        await self.repo.create_session(
            user_id=user.id,
            refresh_token_hash=self._hash_refresh_token(new_refresh),
            expires_at=expires_at,
        )
        await self.db.commit()
        return self._build_token_response(user, new_refresh)

    async def logout(self, refresh_token: str) -> None:
        token_hash = self._hash_refresh_token(refresh_token)
        session = await self.repo.get_session_by_hash(token_hash)
        if session:
            await self.repo.revoke_session(session)
            await self.db.commit()

    async def get_me(self, user_id: UUID) -> UserResponse:
        user = await self.repo.get_by_id_with_role(user_id)
        if user is None:
            raise UnauthorizedError("User not found")
        return self._user_response(user)

    async def google_oauth_start(self) -> OAuthStartResponse:
        if not self.settings.google_client_id:
            raise ConflictError("Google OAuth is not configured")

        state = secrets.token_urlsafe(32)
        await cache_set(f"oauth:google:{state}", "pending", ttl=600)

        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return OAuthStartResponse(
            authorization_url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}",
            state=state,
        )

    async def google_oauth_callback(
        self,
        code: str,
        state: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        cached = await cache_get(f"oauth:google:{state}")
        if cached is None:
            raise UnauthorizedError("Invalid or expired OAuth state")
        await cache_delete(f"oauth:google:{state}")

        if not self.settings.google_client_id or not self.settings.google_client_secret:
            raise ConflictError("Google OAuth is not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                logger.warning("google_token_exchange_failed", status=token_resp.status_code)
                raise UnauthorizedError("Failed to exchange OAuth code")

            access_token = token_resp.json().get("access_token")
            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise UnauthorizedError("Failed to fetch Google user info")

        profile = userinfo_resp.json()
        email = profile.get("email")
        if not email:
            raise UnauthorizedError("Google account has no email")

        user = await self.repo.get_by_email(email)
        if user is None:
            role = await self.repo.get_default_role()
            if role is None:
                raise ConflictError("Default role not configured")
            user = await self.repo.create_user(
                email=email,
                hashed_password=hash_password(secrets.token_urlsafe(32)),
                full_name=profile.get("name", email),
                role_id=role.id,
            )

        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        refresh_token = create_refresh_token(subject=str(user.id))
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days)
        await self.repo.create_session(
            user_id=user.id,
            refresh_token_hash=self._hash_refresh_token(refresh_token),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.db.commit()
        logger.info("google_oauth_login", user_id=str(user.id))
        return self._build_token_response(user, refresh_token)
