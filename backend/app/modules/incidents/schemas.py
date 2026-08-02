"""Pydantic schemas for incident management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AnalysisStatus, IncidentStatus, Severity


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    severity: Severity = Severity.MEDIUM
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: IncidentStatus | None = None
    severity: Severity | None = None
    assigned_to_id: str | None = None
    metadata: dict[str, Any] | None = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    status: IncidentStatus
    severity: Severity
    analysis_status: AnalysisStatus
    root_cause: str | None
    recommendations: list[str] | None
    reported_by_id: str | None
    assigned_to_id: str | None
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int


class AnalysisResultApply(BaseModel):
    root_cause: str
    recommendations: list[str] = Field(default_factory=list)
    classification: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TriggerAnalysisResponse(BaseModel):
    incident_id: str
    analysis_status: AnalysisStatus
    message: str
