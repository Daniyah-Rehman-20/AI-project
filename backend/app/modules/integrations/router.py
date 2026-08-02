"""External integrations: GitHub, Jira, Prometheus, Slack."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.core.logging import get_logger
from app.database.models import User
from app.dependencies import DbSession, require_permission
from app.modules.notifications.service import NotificationService, SlackNotifyRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


class JiraIssue(BaseModel):
    key: str
    summary: str
    status: str
    priority: str | None = None
    url: str | None = None


class JiraListResponse(BaseModel):
    issues: list[JiraIssue]
    total: int


class PrometheusQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    time: str | None = None


class PrometheusQueryResponse(BaseModel):
    status: str
    data: dict[str, Any]


class SlackNotifyBody(BaseModel):
    text: str = Field(min_length=1)
    channel: str | None = None


@router.post("/github/webhook")
async def github_webhook(
    request: Request,
    db: DbSession,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    body = await request.body()

    if settings.github_webhook_secret:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing signature")
        expected = (
            "sha256="
            + hmac.new(
                settings.github_webhook_secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
        )
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    action = payload.get("action", "unknown")
    repo = payload.get("repository", {}).get("full_name", "unknown")

    logger.info(
        "github_webhook_received",
        event=x_github_event,
        action=action,
        repo=repo,
    )

    if x_github_event == "issues" and action in ("opened", "reopened"):
        issue = payload.get("issue", {})
        title = issue.get("title", "GitHub Issue")
        await NotificationService(db, settings).send_slack(
            SlackNotifyRequest(
                text=f"GitHub issue {action}: {title} ({repo})",
            )
        )

    return {"status": "accepted", "event": x_github_event or "unknown"}


@router.get("/jira/issues", response_model=JiraListResponse)
async def list_jira_issues(
    db: DbSession,
    user: User = Depends(require_permission("integrations", "read")),
    jql: str = "order by created DESC",
    max_results: int = 20,
    settings: Settings = Depends(get_settings),
) -> JiraListResponse:
    if not settings.jira_base_url or not settings.jira_email or not settings.jira_api_token:
        return JiraListResponse(issues=[], total=0)

    url = f"{settings.jira_base_url.rstrip('/')}/rest/api/3/search"
    params = {"jql": jql, "maxResults": max_results, "fields": "summary,status,priority"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url,
            params=params,
            auth=(settings.jira_email, settings.jira_api_token),
        )
        if response.status_code != 200:
            logger.warning("jira_fetch_failed", status=response.status_code)
            raise HTTPException(status_code=502, detail="Failed to fetch Jira issues")

    data = response.json()
    issues: list[JiraIssue] = []
    for item in data.get("issues", []):
        fields = item.get("fields", {})
        status = fields.get("status", {}).get("name", "Unknown")
        priority = fields.get("priority", {})
        issues.append(
            JiraIssue(
                key=item.get("key", ""),
                summary=fields.get("summary", ""),
                status=status,
                priority=priority.get("name") if priority else None,
                url=f"{settings.jira_base_url}/browse/{item.get('key', '')}",
            )
        )

    return JiraListResponse(issues=issues, total=data.get("total", len(issues)))


@router.post("/prometheus/query", response_model=PrometheusQueryResponse)
async def prometheus_query(
    payload: PrometheusQueryRequest,
    db: DbSession,
    user: User = Depends(require_permission("integrations", "read")),
    settings: Settings = Depends(get_settings),
) -> PrometheusQueryResponse:
    if not settings.prometheus_url:
        raise HTTPException(status_code=503, detail="Prometheus not configured")

    url = f"{settings.prometheus_url.rstrip('/')}/api/v1/query"
    params: dict[str, str] = {"query": payload.query}
    if payload.time:
        params["time"] = payload.time

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Prometheus query failed")

    data = response.json()
    return PrometheusQueryResponse(status=data.get("status", "unknown"), data=data.get("data", {}))


@router.post("/slack/notify")
async def slack_notify(
    payload: SlackNotifyBody,
    db: DbSession,
    user: User = Depends(require_permission("integrations", "create")),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    return await NotificationService(db, settings).send_slack(
        SlackNotifyRequest(text=payload.text, channel=payload.channel)
    )
