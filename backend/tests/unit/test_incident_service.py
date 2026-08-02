"""Unit tests for incident service."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AnalysisStatus, IncidentStatus, Severity
from app.core.exceptions import NotFoundError
from app.database.models import Role, User
from app.modules.incidents.schemas import IncidentCreate, IncidentUpdate
from app.modules.incidents.service import IncidentService


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    role = Role(
        name="analyst",
        permissions=["incidents:read", "incidents:write"],
    )
    db_session.add(role)
    await db_session.flush()

    user = User(
        email="analyst@example.com",
        hashed_password="hashed",
        full_name="Test Analyst",
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_create_incident(db_session: AsyncSession, test_user: User):
    service = IncidentService(db_session)
    payload = IncidentCreate(
        title="Database connection timeout",
        description="Users experiencing 504 errors on API gateway",
        severity=Severity.HIGH,
    )
    result = await service.create(payload, reported_by_id=test_user.id)

    assert result.title == "Database connection timeout"
    assert result.severity == Severity.HIGH
    assert result.status == IncidentStatus.OPEN
    assert result.analysis_status in (AnalysisStatus.PENDING, AnalysisStatus.QUEUED)
    assert result.reported_by_id == test_user.id


@pytest.mark.asyncio
async def test_get_incident_not_found(db_session: AsyncSession):
    service = IncidentService(db_session)
    with pytest.raises(NotFoundError):
        await service.get(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_update_incident(db_session: AsyncSession, test_user: User):
    service = IncidentService(db_session)
    created = await service.create(
        IncidentCreate(
            title="Memory leak detected",
            description="Heap usage climbing steadily",
            severity=Severity.MEDIUM,
        ),
        reported_by_id=test_user.id,
    )

    updated = await service.update(
        created.id,
        IncidentUpdate(status=IncidentStatus.INVESTIGATING),
    )
    assert updated.status == IncidentStatus.INVESTIGATING


@pytest.mark.asyncio
async def test_list_incidents_with_filters(db_session: AsyncSession, test_user: User):
    service = IncidentService(db_session)
    await service.create(
        IncidentCreate(
            title="Critical outage",
            description="Full service down",
            severity=Severity.CRITICAL,
        ),
        reported_by_id=test_user.id,
    )
    await service.create(
        IncidentCreate(
            title="Minor UI glitch",
            description="Button misaligned",
            severity=Severity.LOW,
        ),
        reported_by_id=test_user.id,
    )

    result = await service.list(severity=Severity.CRITICAL)
    assert result.total == 1
    assert result.items[0].severity == Severity.CRITICAL
