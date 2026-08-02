"""API integration tests for auth and incidents."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "full_name": "New User",
        },
    )
    assert register_resp.status_code == 201
    data = register_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
        },
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_admin(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "TestAdmin123!",
        },
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@example.com"
    assert data["role_name"] == "admin"


@pytest.mark.asyncio
async def test_create_incident(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/incidents",
        headers=auth_headers,
        json={
            "title": "API latency spike",
            "description": "P99 latency exceeded 2s threshold",
            "severity": "high",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "API latency spike"
    assert data["severity"] == "high"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_list_incidents(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/incidents",
        headers=auth_headers,
        json={
            "title": "Test incident for listing",
            "description": "Listing test incident",
            "severity": "low",
        },
    )

    resp = await client.get("/api/v1/incidents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_trigger_analysis(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/api/v1/incidents",
        headers=auth_headers,
        json={
            "title": "Analysis trigger test",
            "description": "Testing analysis queue",
            "severity": "medium",
        },
    )
    incident_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/incidents/{incident_id}/analyze",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["analysis_status"] == "queued"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
