"""Security utilities: passwords, JWT, API keys, prompt sanitization."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

API_KEY_PREFIX = "iik_"
API_KEY_RANDOM_BYTES = 32

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions"),
    re.compile(r"(?i)disregard\s+(all\s+)?(previous|prior|system)\s+(instructions|prompts)"),
    re.compile(r"(?i)you\s+are\s+now\s+(?:a|an)\s+"),
    re.compile(r"(?i)system\s*:\s*"),
    re.compile(r"(?i)assistant\s*:\s*"),
    re.compile(r"(?i)reveal\s+(the\s+)?(system\s+)?prompt"),
    re.compile(r"(?i)jailbreak"),
    re.compile(r"<\s*/?\s*(system|assistant|user)\s*>"),
    re.compile(r"```\s*(system|assistant)"),
)


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    *,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str,
    *,
    session_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token bound to an optional session."""
    settings = get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising JWTError on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode an access token and ensure it has the correct type."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode a refresh token and ensure it has the correct type."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")
    return payload


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate an API key returning (full_key, key_prefix, key_hash)."""
    random_part = secrets.token_urlsafe(API_KEY_RANDOM_BYTES)
    full_key = f"{API_KEY_PREFIX}{random_part}"
    key_prefix = full_key[:12]
    key_hash = hash_api_key(full_key)
    return full_key, key_prefix, key_hash


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    settings = get_settings()
    digest = hashlib.sha256()
    digest.update(settings.app_secret_key.encode("utf-8"))
    digest.update(api_key.encode("utf-8"))
    return digest.hexdigest()


def verify_api_key(api_key: str, key_hash: str) -> bool:
    """Constant-time comparison of an API key against its stored hash."""
    return secrets.compare_digest(hash_api_key(api_key), key_hash)


def sanitize_prompt_input(text: str, *, max_length: int = 32_000) -> str:
    if not text:
        return ""

    cleaned = text.replace("\x00", "")
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    cleaned = cleaned.strip()

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered]", cleaned)

    return cleaned


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Extract and validate user ID from the Authorization bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = decode_access_token(credentials.credentials)
        return str(payload["sub"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
