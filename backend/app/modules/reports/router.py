"""Report management API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.database.models import User
from app.dependencies import DbSession, require_permission
from app.modules.reports.schemas import (
    ReportCreate,
    ReportCreateFromAI,
    ReportListResponse,
    ReportResponse,
)
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=ReportListResponse)
async def list_reports(
    db: DbSession,
    user: User = Depends(require_permission("reports", "read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    incident_id: UUID | None = None,
) -> ReportListResponse:
    return await ReportService(db).list(
        page=page,
        page_size=page_size,
        incident_id=incident_id,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("reports", "read")),
) -> ReportResponse:
    return await ReportService(db).get(report_id)


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    payload: ReportCreate,
    db: DbSession,
    user: User = Depends(require_permission("reports", "create")),
) -> ReportResponse:
    return await ReportService(db).create(payload, created_by_id=user.id)


@router.post("/from-ai", response_model=ReportResponse, status_code=201)
async def create_report_from_ai(
    payload: ReportCreateFromAI,
    db: DbSession,
    user: User = Depends(require_permission("reports", "create")),
) -> ReportResponse:
    """Internal endpoint for worker agents to persist AI-generated postmortems."""
    return await ReportService(db).create_from_ai(payload)
