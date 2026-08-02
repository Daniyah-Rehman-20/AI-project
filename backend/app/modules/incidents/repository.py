"""Data access layer for incidents."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AnalysisStatus, IncidentStatus, Severity
from app.core.repository import BaseRepository
from app.database.models import Incident


class IncidentRepository(BaseRepository[Incident]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Incident)

    async def list_incidents(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: IncidentStatus | None = None,
        severity: Severity | None = None,
        analysis_status: AnalysisStatus | None = None,
        search: str | None = None,
        reported_by_id: str | None = None,
    ) -> tuple[list[Incident], int]:
        stmt = select(Incident)
        count_stmt = select(func.count()).select_from(Incident)

        if status is not None:
            status_val = status.value if hasattr(status, "value") else status
            stmt = stmt.where(Incident.status == status_val)
            count_stmt = count_stmt.where(Incident.status == status_val)
        if severity is not None:
            sev_val = severity.value if hasattr(severity, "value") else severity
            stmt = stmt.where(Incident.severity == sev_val)
            count_stmt = count_stmt.where(Incident.severity == sev_val)
        if analysis_status is not None:
            as_val = analysis_status.value if hasattr(analysis_status, "value") else analysis_status
            stmt = stmt.where(Incident.analysis_status == as_val)
            count_stmt = count_stmt.where(Incident.analysis_status == as_val)
        if reported_by_id is not None:
            stmt = stmt.where(Incident.reported_by_id == reported_by_id)
            count_stmt = count_stmt.where(Incident.reported_by_id == reported_by_id)
        if search:
            pattern = f"%{search}%"
            search_filter = or_(
                Incident.title.ilike(pattern),
                Incident.description.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one())

        offset = (page - 1) * page_size
        stmt = stmt.order_by(Incident.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def create_incident(
        self,
        *,
        title: str,
        description: str,
        severity: Severity,
        reported_by_id: str,
        metadata: dict | None = None,
    ) -> Incident:
        incident = Incident(
            title=title,
            description=description,
            severity=severity.value if hasattr(severity, "value") else severity,
            status=IncidentStatus.OPEN.value,
            analysis_status=AnalysisStatus.PENDING.value,
            reported_by_id=reported_by_id,
            metadata=metadata or {},
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def update_incident(
        self,
        incident: Incident,
        **fields: object,
    ) -> Incident:
        for key, value in fields.items():
            if value is not None and hasattr(incident, key):
                if hasattr(value, "value"):
                    value = value.value
                setattr(incident, key, value)
        incident.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def apply_analysis(
        self,
        incident: Incident,
        *,
        root_cause: str,
        recommendations: list[str],
        classification: str | None = None,
        metadata: dict | None = None,
    ) -> Incident:
        incident.root_cause = root_cause
        incident.recommended_fix = "\n".join(recommendations) if recommendations else None
        incident.analysis_status = AnalysisStatus.COMPLETED.value
        if classification:
            merged = dict(incident.metadata or {})
            merged["classification"] = classification
            incident.metadata = merged
        if metadata:
            merged = dict(incident.metadata or {})
            merged.update(metadata)
            incident.metadata = merged
        incident.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(incident)
        return incident
