"""User admin, health, search, feedback, audit, and API key routes."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.cache import get_redis
from app.core.exceptions import NotFoundError
from app.core.kafka import get_kafka_producer
from app.core.logging import get_logger
from app.core.security import hash_password
from app.database.models import ApiKey, AuditLog, Feedback, User
from app.dependencies import DbSession, require_permission
from app.modules.rag.pipeline import RAGPipeline
from app.modules.users.schemas import (
    AdminUserResponse,
    UserCreate,
    UserListResponse,
    UserUpdate,
)
from app.modules.users.service import UserAdminService

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Users (admin CRUD)
# ---------------------------------------------------------------------------

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    user: User = Depends(require_permission("users", "read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
) -> UserListResponse:
    return await UserAdminService(db).list(page=page, page_size=page_size, search=search)


@users_router.post("", response_model=AdminUserResponse, status_code=201)
async def create_user(
    payload: UserCreate,
    db: DbSession,
    user: User = Depends(require_permission("users", "create")),
) -> AdminUserResponse:
    return await UserAdminService(db).create(payload)


@users_router.get("/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("users", "read")),
) -> AdminUserResponse:
    return await UserAdminService(db).get(user_id)


@users_router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    user: User = Depends(require_permission("users", "update")),
) -> AdminUserResponse:
    return await UserAdminService(db).update(user_id, payload)


@users_router.delete("/{user_id}", status_code=204, response_class=Response)
async def delete_user(
    user_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("users", "delete")),
) -> Response:
    await UserAdminService(db).delete(user_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Health & metrics
# ---------------------------------------------------------------------------

health_router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        timestamp=datetime.now(UTC),
    )


@health_router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check(db: DbSession) -> ReadinessResponse:
    checks: dict[str, str] = {}

    try:
        await db.execute(select(1))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    try:
        producer = get_kafka_producer()
        checks["kafka"] = "ok" if producer else "unavailable"
    except Exception as exc:
        checks["kafka"] = f"error: {exc}"

    all_ok = all(v == "ok" or v == "unavailable" for v in checks.values())
    return ReadinessResponse(
        status="ready" if all_ok else "degraded",
        checks=checks,
    )


@health_router.get("/metrics")
async def metrics(db: DbSession) -> Response:
    from sqlalchemy import func as sqlfunc

    from app.database.models import Incident

    total_incidents = int(
        (await db.execute(select(sqlfunc.count()).select_from(Incident))).scalar_one()
    )
    total_users = int((await db.execute(select(sqlfunc.count()).select_from(User))).scalar_one())

    body = (
        "# HELP incident_intel_incidents_total Total incidents\n"
        "# TYPE incident_intel_incidents_total gauge\n"
        f"incident_intel_incidents_total {total_incidents}\n"
        "# HELP incident_intel_users_total Total users\n"
        "# TYPE incident_intel_users_total gauge\n"
        f"incident_intel_users_total {total_users}\n"
    )
    return Response(content=body, media_type="text/plain; version=0.0.4")


# ---------------------------------------------------------------------------
# Search (RAG)
# ---------------------------------------------------------------------------

search_router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class Citation(BaseModel):
    document_id: str
    chunk_index: int
    content: str
    score: float


class SearchResponse(BaseModel):
    answer: str
    citations: list[Citation]
    query: str


@search_router.post("", response_model=SearchResponse)
async def rag_search(
    payload: SearchRequest,
    db: DbSession,
    user: User = Depends(require_permission("search", "read")),
) -> SearchResponse:
    result = await RAGPipeline(db).search(payload.query, top_k=payload.top_k)
    return SearchResponse(
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
        query=payload.query,
    )


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

feedback_router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    context: dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    rating: int
    comment: str | None
    context: dict[str, Any] | None
    created_at: datetime


@feedback_router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    payload: FeedbackCreate,
    db: DbSession,
    user: User = Depends(require_permission("feedback", "create")),
) -> FeedbackResponse:
    feedback = Feedback(
        user_id=user.id,
        rating=payload.rating,
        comment=payload.comment,
        context=payload.context,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)


@feedback_router.get("", response_model=list[FeedbackResponse])
async def list_feedback(
    db: DbSession,
    user: User = Depends(require_permission("feedback", "read")),
    limit: int = Query(50, ge=1, le=200),
) -> list[FeedbackResponse]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return [FeedbackResponse.model_validate(f) for f in result.scalars().all()]


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

audit_router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int


@audit_router.get("", response_model=AuditListResponse)
async def list_audit_logs(
    db: DbSession,
    user: User = Depends(require_permission("audit", "read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = None,
    resource_type: str | None = None,
) -> AuditListResponse:
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
        count_stmt = count_stmt.where(AuditLog.resource_type == resource_type)

    total = int((await db.execute(count_stmt)).scalar_one())
    offset = (page - 1) * page_size
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return AuditListResponse(
        items=[AuditLogResponse.model_validate(a) for a in items],
        total=total,
    )


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

apikeys_router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int | None = Field(default=90, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    prefix: str
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreateResponse(ApiKeyResponse):
    key: str


def _generate_api_key() -> tuple[str, str, str]:
    raw_key = f"ii_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:11]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, prefix, key_hash


@apikeys_router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def create_api_key(
    payload: ApiKeyCreate,
    db: DbSession,
    user: User = Depends(require_permission("api_keys", "create")),
) -> ApiKeyCreateResponse:
    raw_key, prefix, key_hash = _generate_api_key()
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=payload.expires_in_days)

    api_key = ApiKey(
        user_id=user.id,
        name=payload.name,
        key_hash=key_hash,
        prefix=prefix,
        scopes=payload.scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        scopes=api_key.scopes or [],
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        key=raw_key,
    )


@apikeys_router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db: DbSession,
    user: User = Depends(require_permission("api_keys", "read")),
) -> list[ApiKeyResponse]:
    stmt = select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    result = await db.execute(stmt)
    return [ApiKeyResponse.model_validate(k) for k in result.scalars().all()]


@apikeys_router.delete("/{key_id}", status_code=204, response_class=Response)
async def revoke_api_key(
    key_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("api_keys", "delete")),
) -> Response:
    stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise NotFoundError(f"API key {key_id} not found")
    await db.delete(api_key)
    await db.commit()
    return Response(status_code=204)
