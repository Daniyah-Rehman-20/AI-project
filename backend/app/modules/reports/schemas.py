"""Pydantic schemas for incident reports."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    incident_id: UUID
    title: str = Field(min_length=1, max_length=500)
    content_markdown: str = Field(min_length=1)


class ReportCreateFromAI(BaseModel):
    incident_id: UUID
    title: str = Field(min_length=1, max_length=500)
    content_markdown: str = Field(min_length=1)
    metadata: dict | None = None


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    title: str
    content_markdown: str
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
