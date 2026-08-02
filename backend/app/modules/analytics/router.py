"""Analytics API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.database.models import User
from app.dependencies import DbSession, require_permission
from app.modules.analytics.service import (
    AIUsageStats,
    AnalyticsService,
    DashboardStats,
    TrackEventRequest,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: DbSession,
    user: User = Depends(require_permission("analytics", "read")),
) -> DashboardStats:
    return await AnalyticsService(db).get_dashboard_stats()


@router.get("/ai-usage", response_model=AIUsageStats)
async def get_ai_usage(
    db: DbSession,
    user: User = Depends(require_permission("analytics", "read")),
    days: int = Query(30, ge=1, le=365),
) -> AIUsageStats:
    return await AnalyticsService(db).get_ai_usage(days=days)


@router.post("/events", status_code=204, response_class=Response)
async def track_event(
    payload: TrackEventRequest,
    db: DbSession,
    user: User = Depends(require_permission("analytics", "create")),
) -> Response:
    await AnalyticsService(db).track_event(
        event_type=payload.event_type,
        user_id=user.id,
        metadata=payload.metadata,
    )
    return Response(status_code=204)
