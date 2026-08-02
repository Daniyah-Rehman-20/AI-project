"""Notification API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.database.models import User
from app.dependencies import DbSession, require_permission
from app.modules.notifications.service import (
    NotificationListResponse,
    NotificationResponse,
    NotificationService,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    db: DbSession,
    user: User = Depends(require_permission("notifications", "read")),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
) -> NotificationListResponse:
    return await NotificationService(db).list_notifications(
        user.id,
        unread_only=unread_only,
        limit=limit,
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("notifications", "read")),
) -> NotificationResponse:
    return await NotificationService(db).mark_read(notification_id, user.id)


@router.post("/read-all")
async def mark_all_notifications_read(
    db: DbSession,
    user: User = Depends(require_permission("notifications", "read")),
) -> dict[str, int]:
    count = await NotificationService(db).mark_all_read(user.id)
    return {"marked_read": count}
