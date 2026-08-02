"""Report repository and service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.repository import BaseRepository
from app.database.models import Incident, Report
from app.modules.reports.schemas import (
    ReportCreate,
    ReportCreateFromAI,
    ReportListResponse,
    ReportResponse,
)

logger = get_logger(__name__)


class ReportRepository(BaseRepository[Report]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Report)

    async def list_reports(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        incident_id: UUID | None = None,
    ) -> tuple[list[Report], int]:
        stmt = select(Report)
        count_stmt = select(func.count()).select_from(Report)

        if incident_id is not None:
            stmt = stmt.where(Report.incident_id == incident_id)
            count_stmt = count_stmt.where(Report.incident_id == incident_id)

        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one())

        offset = (page - 1) * page_size
        stmt = stmt.order_by(Report.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def create_report(
        self,
        *,
        incident_id: UUID,
        title: str,
        content_markdown: str,
        created_by_id: UUID | None = None,
    ) -> Report:
        report = Report(
            incident_id=incident_id,
            title=title,
            content_markdown=content_markdown,
            created_by_id=created_by_id,
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ReportRepository(db)

    async def _ensure_incident(self, incident_id: UUID) -> None:
        stmt = select(Incident).where(Incident.id == incident_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise NotFoundError(f"Incident {incident_id} not found")

    async def create(
        self,
        payload: ReportCreate,
        *,
        created_by_id: UUID,
    ) -> ReportResponse:
        await self._ensure_incident(payload.incident_id)
        report = await self.repo.create_report(
            incident_id=payload.incident_id,
            title=payload.title,
            content_markdown=payload.content_markdown,
            created_by_id=created_by_id,
        )
        await self.db.commit()
        logger.info("report_created", report_id=str(report.id))
        return ReportResponse.model_validate(report)

    async def create_from_ai(self, payload: ReportCreateFromAI) -> ReportResponse:
        await self._ensure_incident(payload.incident_id)
        report = await self.repo.create_report(
            incident_id=payload.incident_id,
            title=payload.title,
            content_markdown=payload.content_markdown,
            created_by_id=None,
        )
        await self.db.commit()
        logger.info("report_created_from_ai", report_id=str(report.id))
        return ReportResponse.model_validate(report)

    async def get(self, report_id: UUID) -> ReportResponse:
        report = await self.repo.get_by_id(report_id)
        if report is None:
            raise NotFoundError(f"Report {report_id} not found")
        return ReportResponse.model_validate(report)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        incident_id: UUID | None = None,
    ) -> ReportListResponse:
        items, total = await self.repo.list_reports(
            page=page,
            page_size=page_size,
            incident_id=incident_id,
        )
        return ReportListResponse(
            items=[ReportResponse.model_validate(r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
        )
