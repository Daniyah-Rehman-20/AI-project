"""Incident management API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.core.enums import AnalysisStatus, IncidentStatus, Severity
from app.database.models import User
from app.dependencies import DbSession, require_permission
from app.modules.incidents.schemas import (
    AnalysisResultApply,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentUpdate,
    TriggerAnalysisResponse,
)
from app.modules.incidents.service import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=201,
)
async def create_incident(
    payload: IncidentCreate,
    db: DbSession,
    user: User = Depends(require_permission("incidents", "create")),
) -> IncidentResponse:
    return await IncidentService(db).create(payload, reported_by_id=user.id)


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    db: DbSession,
    user: User = Depends(require_permission("incidents", "read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: IncidentStatus | None = None,
    severity: Severity | None = None,
    analysis_status: AnalysisStatus | None = None,
    search: str | None = None,
) -> IncidentListResponse:
    return await IncidentService(db).list(
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
        analysis_status=analysis_status,
        search=search,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("incidents", "read")),
) -> IncidentResponse:
    return await IncidentService(db).get(incident_id)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    payload: IncidentUpdate,
    db: DbSession,
    user: User = Depends(require_permission("incidents", "update")),
) -> IncidentResponse:
    return await IncidentService(db).update(incident_id, payload)


@router.delete("/{incident_id}", status_code=204, response_class=Response)
async def delete_incident(
    incident_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("incidents", "delete")),
) -> Response:
    await IncidentService(db).delete(incident_id)
    return Response(status_code=204)


@router.post(
    "/{incident_id}/analyze",
    response_model=TriggerAnalysisResponse,
)
async def trigger_analysis(
    incident_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("incidents", "analyze")),
) -> TriggerAnalysisResponse:
    return await IncidentService(db).trigger_analysis(incident_id)


@router.post(
    "/{incident_id}/analysis-result",
    response_model=IncidentResponse,
)
async def apply_analysis_result(
    incident_id: UUID,
    payload: AnalysisResultApply,
    db: DbSession,
    user: User = Depends(require_permission("incidents", "analyze")),
) -> IncidentResponse:
    return await IncidentService(db).apply_analysis_result(incident_id, payload)
