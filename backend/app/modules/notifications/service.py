"""Notification service with Slack webhook support."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.enums import NotificationChannel, NotificationStatus
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.repository import BaseRepository
from app.database.models import Notification

logger = get_logger(__name__)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    incident_id: str | None
    title: str
    message: str
    channel: str
    is_read: bool
    created_at: datetime

    @classmethod
    def from_model(cls, notification: Notification) -> NotificationResponse:
        return cls(
            id=notification.id,
            user_id=notification.user_id,
            incident_id=notification.incident_id,
            title=notification.subject,
            message=notification.body,
            channel=notification.channel,
            is_read=notification.status == NotificationStatus.READ.value,
            created_at=notification.created_at,
        )


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class SlackNotifyRequest(BaseModel):
    text: str = Field(min_length=1)
    channel: str | None = None


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Notification)

    async def list_for_user(
        self,
        user_id: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.status != NotificationStatus.READ.value)
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        unread_stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status != NotificationStatus.READ.value,
            )
        )
        unread_result = await self.db.execute(unread_stmt)
        unread_count = int(unread_result.scalar_one())
        return items, unread_count

    async def create_notification(
        self,
        *,
        user_id: str,
        title: str,
        message: str,
        channel: str = NotificationChannel.IN_APP.value,
        incident_id: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            subject=title,
            body=message,
            channel=channel,
            incident_id=incident_id,
            status=NotificationStatus.SENT.value,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification


class NotificationService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repo = NotificationRepository(db)

    async def list_notifications(
        self,
        user_id: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> NotificationListResponse:
        items, unread_count = await self.repo.list_for_user(
            user_id,
            unread_only=unread_only,
            limit=limit,
        )
        return NotificationListResponse(
            items=[NotificationResponse.from_model(n) for n in items],
            total=len(items),
            unread_count=unread_count,
        )

    async def mark_read(self, notification_id: str, user_id: str) -> NotificationResponse:
        notification = await self.repo.get_by_id(notification_id)
        if notification is None or notification.user_id != user_id:
            raise NotFoundError(f"Notification {notification_id} not found")
        notification.status = NotificationStatus.READ.value
        await self.db.flush()
        await self.db.commit()
        return NotificationResponse.from_model(notification)

    async def mark_all_read(self, user_id: str) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status != NotificationStatus.READ.value,
            )
            .values(status=NotificationStatus.READ.value)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount or 0

    async def send_slack(self, payload: SlackNotifyRequest) -> dict[str, str]:
        webhook_url = self.settings.slack_webhook_url
        if not webhook_url:
            logger.warning("slack_webhook_not_configured")
            return {"status": "skipped", "reason": "Slack webhook not configured"}

        body: dict[str, str] = {"text": payload.text}
        if payload.channel:
            body["channel"] = payload.channel

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(webhook_url, json=body)
            if response.status_code >= 400:
                logger.warning(
                    "slack_webhook_failed",
                    status=response.status_code,
                    body=response.text,
                )
                return {"status": "error", "reason": f"HTTP {response.status_code}"}

        logger.info("slack_notification_sent")
        return {"status": "sent"}

    async def notify_user(
        self,
        *,
        user_id: str,
        title: str,
        message: str,
        incident_id: str | None = None,
        send_slack: bool = False,
    ) -> NotificationResponse:
        notification = await self.repo.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            incident_id=incident_id,
        )
        await self.db.commit()

        if send_slack:
            await self.send_slack(SlackNotifyRequest(text=f"*{title}*\n{message}"))

        return NotificationResponse.from_model(notification)
