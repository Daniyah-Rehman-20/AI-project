"""FastAPI dependency injection helpers for auth and RBAC."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import Settings, get_settings
from app.core.enums import RoleName, expand_role_permissions, role_has_permission
from app.core.exceptions import AuthenticationError, AuthorizationError, ForbiddenError
from app.core.security import decode_access_token, verify_api_key
from app.database.models import ApiKey, User
from app.database.session import get_db, get_db_session

bearer_scheme = HTTPBearer(auto_error=False)

API_KEY_HEADER = "X-API-Key"
_WRITE_ACTIONS = frozenset({"create", "update", "delete", "write", "analyze"})


async def _load_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(
        select(User).options(joinedload(User.role)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def _authenticate_api_key(
    session: AsyncSession,
    api_key: str,
) -> tuple[User, list[str]]:
    key_prefix = api_key[:12]
    result = await session.execute(
        select(ApiKey)
        .options(joinedload(ApiKey.user).joinedload(User.role))
        .where(ApiKey.key_prefix == key_prefix, ApiKey.is_active.is_(True))
    )
    for candidate in result.scalars().all():
        if verify_api_key(api_key, candidate.key_hash):
            if candidate.expires_at and candidate.expires_at < datetime.now(UTC):
                raise AuthenticationError("API key has expired")
            user = candidate.user
            if user is None or not user.is_active:
                raise AuthenticationError("API key owner is inactive")
            candidate.last_used_at = datetime.now(UTC)
            await session.flush()
            return user, list(candidate.permissions or [])
    raise AuthenticationError("Invalid API key")


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> User:
    """Resolve the current user from a Bearer JWT or API key header."""
    if x_api_key:
        user, api_key_permissions = await _authenticate_api_key(session, x_api_key)
        request.state.auth_method = "api_key"
        request.state.api_key_permissions = api_key_permissions
        request.state.current_user = user
        return user

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Missing or invalid authorization header")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc

    user = await _load_user_by_id(session, str(user_id))
    if user is None:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    request.state.auth_method = "jwt"
    request.state.api_key_permissions = []
    request.state.current_user = user
    return user


async def get_optional_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> User | None:
    if credentials is None and not x_api_key:
        return None
    try:
        return await get_current_user(request, session, credentials, x_api_key)
    except AuthenticationError:
        return None


def _effective_permissions(request: Request, user: User) -> set[str]:
    extra = getattr(request.state, "api_key_permissions", None) or []
    return expand_role_permissions(user.role_name, extra)


def _normalize_permissions(*permissions: str) -> tuple[str, ...]:
    if len(permissions) == 2 and ":" not in permissions[0]:
        return (f"{permissions[0]}:{permissions[1]}",)
    return permissions


def require_permission(*permissions: str) -> Callable:
    """Dependency factory enforcing RBAC permissions.

    Supports both forms::

        user: User = Depends(require_permission("incidents", "read"))
        user: User = Depends(require_permission("incidents:read"))
    """
    required = _normalize_permissions(*permissions)

    async def _dependency(
        request: Request,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        grants = _effective_permissions(request, user)
        if "admin:all" in grants:
            return user

        role_name = user.role_name
        extra = list(getattr(request.state, "api_key_permissions", None) or [])

        for permission in required:
            if permission in grants:
                return user
            resource, _, action = permission.partition(":")
            candidates = [permission]
            if action in _WRITE_ACTIONS:
                candidates.append(f"{resource}:write")
            if any(role_has_permission(role_name, candidate, extra) for candidate in candidates):
                return user
            if permission in extra:
                return user

        raise ForbiddenError(
            f"Missing required permission(s): {', '.join(required)}",
            details={"required": list(required), "role": role_name},
        )

    return _dependency


def require_roles(*roles: RoleName | str) -> Callable:
    normalized = {role.value if isinstance(role, RoleName) else role for role in roles}

    async def _dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role_name not in normalized:
            raise AuthorizationError(
                f"Requires one of roles: {', '.join(sorted(normalized))}",
                details={"role": user.role_name, "required_roles": sorted(normalized)},
            )
        return user

    return _dependency


async def get_admin_user(user: Annotated[User, Depends(require_roles(RoleName.ADMIN))]) -> User:
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

__all__ = [
    "API_KEY_HEADER",
    "AdminUser",
    "CurrentUser",
    "DbSession",
    "SettingsDep",
    "get_admin_user",
    "get_current_user",
    "get_db",
    "get_optional_user",
    "require_permission",
    "require_roles",
]
