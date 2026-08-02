"""Analytics dashboard and event tracking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AnalysisStatus, IncidentStatus, Severity
from app.core.logging import get_logger
from app.database.models import AnalyticsEvent, Incident, ModelUsage

logger = get_logger(__name__)


class DashboardStats(BaseModel):
    total_incidents: int
    open_incidents: int
    critical_incidents: int
    analysis_pending: int
    analysis_completed: int
    incidents_by_severity: dict[str, int]
    incidents_by_status: dict[str, int]
    recent_incidents_7d: int


class AIUsageStats(BaseModel):
    total_requests: int
    total_tokens_in: int
    total_tokens_out: int
    by_provider: dict[str, int]
    by_model: dict[str, int]
    by_operation: dict[str, int]


class TrackEventRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_dashboard_stats(self) -> DashboardStats:
        total_stmt = select(func.count()).select_from(Incident)
        total = int((await self.db.execute(total_stmt)).scalar_one())

        open_stmt = (
            select(func.count()).select_from(Incident).where(Incident.status == IncidentStatus.OPEN.value)
        )
        open_count = int((await self.db.execute(open_stmt)).scalar_one())

        critical_stmt = (
            select(func.count()).select_from(Incident).where(Incident.severity == Severity.CRITICAL.value)
        )
        critical_count = int((await self.db.execute(critical_stmt)).scalar_one())

        pending_stmt = (
            select(func.count())
            .select_from(Incident)
            .where(
                Incident.analysis_status.in_(
                    [
                        AnalysisStatus.PENDING.value,
                        AnalysisStatus.QUEUED.value,
                        AnalysisStatus.IN_PROGRESS.value,
                    ]
                )
            )
        )
        pending_count = int((await self.db.execute(pending_stmt)).scalar_one())

        completed_stmt = (
            select(func.count())
            .select_from(Incident)
            .where(Incident.analysis_status == AnalysisStatus.COMPLETED.value)
        )
        completed_count = int((await self.db.execute(completed_stmt)).scalar_one())

        severity_rows = await self.db.execute(
            select(Incident.severity, func.count()).group_by(Incident.severity)
        )
        by_severity = {str(row[0]): row[1] for row in severity_rows}

        status_rows = await self.db.execute(
            select(Incident.status, func.count()).group_by(Incident.status)
        )
        by_status = {str(row[0]): row[1] for row in status_rows}

        week_ago = datetime.now(UTC) - timedelta(days=7)
        recent_stmt = (
            select(func.count()).select_from(Incident).where(Incident.created_at >= week_ago)
        )
        recent_count = int((await self.db.execute(recent_stmt)).scalar_one())

        return DashboardStats(
            total_incidents=total,
            open_incidents=open_count,
            critical_incidents=critical_count,
            analysis_pending=pending_count,
            analysis_completed=completed_count,
            incidents_by_severity=by_severity,
            incidents_by_status=by_status,
            recent_incidents_7d=recent_count,
        )

    async def get_ai_usage(
        self,
        *,
        days: int = 30,
    ) -> AIUsageStats:
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = select(ModelUsage).where(ModelUsage.created_at >= since)
        result = await self.db.execute(stmt)
        usages = list(result.scalars().all())

        by_provider: dict[str, int] = {}
        by_model: dict[str, int] = {}
        by_operation: dict[str, int] = {}
        total_tokens_in = 0
        total_tokens_out = 0

        for usage in usages:
            by_provider[usage.provider] = by_provider.get(usage.provider, 0) + 1
            by_model[usage.model] = by_model.get(usage.model, 0) + 1
            by_operation[usage.operation] = by_operation.get(usage.operation, 0) + 1
            total_tokens_in += usage.tokens_in or 0
            total_tokens_out += usage.tokens_out or 0

        return AIUsageStats(
            total_requests=len(usages),
            total_tokens_in=total_tokens_in,
            total_tokens_out=total_tokens_out,
            by_provider=by_provider,
            by_model=by_model,
            by_operation=by_operation,
        )

    async def track_event(
        self,
        *,
        event_type: str,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            metadata=metadata or {},
        )
        self.db.add(event)
        await self.db.commit()
        logger.info("analytics_event_tracked", event_type=event_type)
