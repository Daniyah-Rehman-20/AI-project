"""Scheduled maintenance tasks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database.models import Session

logger = get_logger(__name__)


class MaintenanceScheduler:
    """Handles periodic cleanup of expired sessions and stale data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def cleanup_expired_sessions(self, *, batch_size: int = 500) -> int:
        now = datetime.now(UTC)
        stmt = select(Session).where(Session.expires_at < now).limit(batch_size)
        result = await self.db.execute(stmt)
        sessions = list(result.scalars().all())

        if not sessions:
            return 0

        session_ids = [s.id for s in sessions]
        await self.db.execute(delete(Session).where(Session.id.in_(session_ids)))
        await self.db.commit()
        logger.info("expired_sessions_cleaned", count=len(session_ids))
        return len(session_ids)

    async def cleanup_revoked_sessions(
        self,
        *,
        older_than_days: int = 30,
        batch_size: int = 500,
    ) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        stmt = (
            select(Session)
            .where(
                Session.revoked_at.isnot(None),
                Session.revoked_at < cutoff,
            )
            .limit(batch_size)
        )
        result = await self.db.execute(stmt)
        sessions = list(result.scalars().all())

        if not sessions:
            return 0

        session_ids = [s.id for s in sessions]
        await self.db.execute(delete(Session).where(Session.id.in_(session_ids)))
        await self.db.commit()
        logger.info("revoked_sessions_cleaned", count=len(session_ids))
        return len(session_ids)

    async def run_maintenance(self) -> dict[str, int]:
        expired = await self.cleanup_expired_sessions()
        revoked = await self.cleanup_revoked_sessions()
        return {"expired_sessions": expired, "revoked_sessions": revoked}
