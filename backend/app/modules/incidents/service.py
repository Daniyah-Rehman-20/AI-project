"""Incident business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AnalysisStatus, IncidentStatus, Severity
from app.core.exceptions import NotFoundError
from app.core.kafka import publish_event
from app.core.logging import get_logger
from app.modules.incidents.repository import IncidentRepository
from app.modules.incidents.schemas import (
    AnalysisResultApply,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentUpdate,
    TriggerAnalysisResponse,
)

logger = get_logger(__name__)


class IncidentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncidentRepository(db)

    def _to_response(self, incident) -> IncidentResponse:
        return IncidentResponse(
            id=incident.id,
            title=incident.title,
            description=incident.description or "",
            status=IncidentStatus(incident.status),
            severity=Severity(incident.severity),
            analysis_status=AnalysisStatus(incident.analysis_status),
            root_cause=incident.root_cause,
            recommendations=incident.recommendations,
            reported_by_id=incident.reporter_id,
            assigned_to_id=incident.assignee_id,
            metadata=incident.metadata_json,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
        )

    async def create(
        self,
        payload: IncidentCreate,
        *,
        reported_by_id: str,
    ) -> IncidentResponse:
        incident = await self.repo.create_incident(
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            reported_by_id=reported_by_id,
            metadata=payload.metadata,
        )
        await self.db.commit()
        logger.info("incident_created", incident_id=str(incident.id))
        return self._to_response(incident)

    async def get(self, incident_id: str) -> IncidentResponse:
        incident = await self.repo.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError(f"Incident {incident_id} not found")
        return self._to_response(incident)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: IncidentStatus | None = None,
        severity: Severity | None = None,
        analysis_status: AnalysisStatus | None = None,
        search: str | None = None,
        reported_by_id: str | None = None,
    ) -> IncidentListResponse:
        items, total = await self.repo.list_incidents(
            page=page,
            page_size=page_size,
            status=status,
            severity=severity,
            analysis_status=analysis_status,
            search=search,
            reported_by_id=reported_by_id,
        )
        return IncidentListResponse(
            items=[self._to_response(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(
        self,
        incident_id: str,
        payload: IncidentUpdate,
    ) -> IncidentResponse:
        incident = await self.repo.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError(f"Incident {incident_id} not found")

        update_data = payload.model_dump(exclude_unset=True)
        incident = await self.repo.update_incident(incident, **update_data)
        await self.db.commit()
        return self._to_response(incident)

    async def delete(self, incident_id: str) -> None:
        incident = await self.repo.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError(f"Incident {incident_id} not found")
        await self.repo.delete(incident)
        await self.db.commit()
        logger.info("incident_deleted", incident_id=str(incident_id))

    async def trigger_analysis(self, incident_id: str) -> TriggerAnalysisResponse:
        incident = await self.repo.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError(f"Incident {incident_id} not found")

        incident = await self.repo.update_incident(
            incident,
            analysis_status=AnalysisStatus.QUEUED.value,
        )
        await self.db.commit()

        await publish_event(
            "incident_created",
            {
                "incident_id": str(incident.id),
                "title": incident.title,
                "severity": incident.severity if isinstance(incident.severity, str) else incident.severity.value,
                "description": incident.description,
            },
        )
        logger.info("incident_analysis_triggered", incident_id=str(incident_id))
        return TriggerAnalysisResponse(
            incident_id=incident.id,
            analysis_status=AnalysisStatus.QUEUED,
            message="Analysis queued for processing",
        )
    async def apply_analysis_result(
        self,
        incident_id: str,
        payload: AnalysisResultApply,
    ) -> IncidentResponse:
        incident = await self.repo.get_by_id(incident_id)
        if incident is None:
            raise NotFoundError(f"Incident {incident_id} not found")

        incident = await self.repo.apply_analysis(
            incident,
            root_cause=payload.root_cause,
            recommendations=payload.recommendations,
            classification=payload.classification,
            metadata=payload.metadata,
        )
        await self.db.commit()
        logger.info("incident_analysis_applied", incident_id=str(incident_id))
        return self._to_response(incident)
