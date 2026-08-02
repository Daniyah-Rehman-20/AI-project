"""LangGraph multi-agent incident analysis workflow."""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import AnalysisStatus
from app.core.logging import get_logger
from app.database.models import Incident, LogEntry
from app.modules.embeddings.service import get_chat_model
from app.modules.notifications.service import NotificationService
from app.modules.rag.pipeline import RAGPipeline
from app.modules.reports.schemas import ReportCreateFromAI
from app.modules.reports.service import ReportService

logger = get_logger(__name__)


class AgentState(TypedDict, total=False):
    incident_id: str
    title: str
    description: str
    severity: str
    logs: list[dict[str, Any]]
    classification: dict[str, Any]
    root_cause: dict[str, Any]
    retrieved_context: list[dict[str, Any]]
    recommendations: list[str]
    report_markdown: str
    error: str | None


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass
    return {"raw": text}


async def classify_node(state: AgentState) -> dict[str, Any]:
    llm = get_chat_model()
    prompt = (
        "Classify this incident. Respond with JSON: "
        '{"category": "...", "confidence": 0.0-1.0, "summary": "..."}\n\n'
        f"Title: {state.get('title', '')}\n"
        f"Description: {state.get('description', '')}\n"
        f"Severity: {state.get('severity', '')}"
    )
    try:
        response = await llm.ainvoke(prompt)
        classification = _parse_json(str(response.content))
    except Exception as exc:
        logger.warning("classify_node_failed", error=str(exc))
        classification = {
            "category": "unknown",
            "confidence": 0.5,
            "summary": state.get("title", "Incident"),
        }
    return {"classification": classification}


async def root_cause_node(state: AgentState) -> dict[str, Any]:
    llm = get_chat_model()
    logs_text = "\n".join(
        f"[{log.get('level', 'INFO')}] {log.get('message', '')}"
        for log in state.get("logs", [])[:50]
    )
    prompt = (
        "Analyze root cause. Respond with JSON: "
        '{"root_cause": "...", "confidence": 0.0-1.0, "evidence": ["..."]}\n\n'
        f"Title: {state.get('title', '')}\n"
        f"Description: {state.get('description', '')}\n"
        f"Classification: {json.dumps(state.get('classification', {}))}\n"
        f"Logs:\n{logs_text or 'No logs available'}"
    )
    try:
        response = await llm.ainvoke(prompt)
        root_cause = _parse_json(str(response.content))
    except Exception as exc:
        logger.warning("root_cause_node_failed", error=str(exc))
        root_cause = {
            "root_cause": "Unable to determine root cause automatically.",
            "confidence": 0.3,
            "evidence": [],
        }
    return {"root_cause": root_cause}


async def retrieve_node(state: AgentState, db: AsyncSession) -> dict[str, Any]:
    query = f"{state.get('title', '')} {state.get('description', '')}"
    try:
        pipeline = RAGPipeline(db)
        result = await pipeline.search(query, top_k=5)
        return {"retrieved_context": result.get("citations", [])}
    except Exception as exc:
        logger.warning("retrieve_node_failed", error=str(exc))
        return {"retrieved_context": []}


async def recommend_node(state: AgentState) -> dict[str, Any]:
    llm = get_chat_model()
    context = json.dumps(state.get("retrieved_context", [])[:3])
    prompt = (
        "Recommend remediation steps. Respond with JSON: "
        '{"recommendations": ["step1", "step2", ...]}\n\n'
        f"Root cause: {json.dumps(state.get('root_cause', {}))}\n"
        f"Context: {context}"
    )
    try:
        response = await llm.ainvoke(prompt)
        parsed = _parse_json(str(response.content))
        recommendations = parsed.get("recommendations", [])
        if isinstance(recommendations, str):
            recommendations = [recommendations]
    except Exception as exc:
        logger.warning("recommend_node_failed", error=str(exc))
        recommendations = [
            "Review recent deployments and configuration changes",
            "Check service health dashboards",
            "Escalate to on-call if issue persists",
        ]
    return {"recommendations": recommendations}


async def report_node(state: AgentState) -> dict[str, Any]:
    llm = get_chat_model()
    prompt = (
        "Write an incident postmortem in Markdown format.\n\n"
        f"Title: {state.get('title', '')}\n"
        f"Classification: {json.dumps(state.get('classification', {}))}\n"
        f"Root Cause: {json.dumps(state.get('root_cause', {}))}\n"
        f"Recommendations: {json.dumps(state.get('recommendations', []))}\n"
        f"Retrieved Context: {json.dumps(state.get('retrieved_context', [])[:2])}"
    )
    try:
        response = await llm.ainvoke(prompt)
        report_markdown = str(response.content)
    except Exception as exc:
        logger.warning("report_node_failed", error=str(exc))
        report_markdown = (
            f"# Postmortem: {state.get('title', 'Incident')}\n\n"
            f"## Root Cause\n{state.get('root_cause', {}).get('root_cause', 'TBD')}\n\n"
            f"## Recommendations\n" + "\n".join(f"- {r}" for r in state.get("recommendations", []))
        )
    return {"report_markdown": report_markdown}


async def notify_node(state: AgentState, db: AsyncSession) -> dict[str, Any]:
    incident_id = state.get("incident_id")
    if not incident_id:
        return {}

    stmt = (
        select(Incident).options(selectinload(Incident.reporter)).where(Incident.id == incident_id)
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if incident is None or incident.reporter is None:
        return {}

    try:
        service = NotificationService(db)
        await service.notify_user(
            user_id=incident.reporter.id,
            title=f"Analysis complete: {incident.title}",
            message=(f"Root cause: {state.get('root_cause', {}).get('root_cause', 'See report')}"),
            incident_id=incident.id,
            send_slack=True,
        )
    except Exception as exc:
        logger.warning("notify_node_failed", error=str(exc))

    return {}


def build_incident_graph(db: AsyncSession):
    graph = StateGraph(AgentState)

    async def retrieve_wrapper(state: AgentState) -> dict[str, Any]:
        return await retrieve_node(state, db)

    async def notify_wrapper(state: AgentState) -> dict[str, Any]:
        return await notify_node(state, db)

    graph.add_node("classify", classify_node)
    graph.add_node("root_cause", root_cause_node)
    graph.add_node("retrieve", retrieve_wrapper)
    graph.add_node("recommend", recommend_node)
    graph.add_node("report", report_node)
    graph.add_node("notify", notify_wrapper)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "root_cause")
    graph.add_edge("root_cause", "retrieve")
    graph.add_edge("retrieve", "recommend")
    graph.add_edge("recommend", "report")
    graph.add_edge("report", "notify")
    graph.add_edge("notify", END)

    return graph.compile()


async def run_incident_analysis(
    db: AsyncSession,
    incident_id: str,
) -> dict[str, Any]:
    stmt = select(Incident).options(selectinload(Incident.log_entries)).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if incident is None:
        raise ValueError(f"Incident {incident_id} not found")

    incident.analysis_status = AnalysisStatus.IN_PROGRESS.value
    await db.flush()

    logs_stmt = (
        select(LogEntry)
        .where(LogEntry.incident_id == incident.id)
        .order_by(LogEntry.timestamp.desc())
        .limit(100)
    )
    logs_result = await db.execute(logs_stmt)
    logs = [
        {"level": log.level.value, "message": log.message, "source": log.source}
        for log in logs_result.scalars().all()
    ]

    initial_state: AgentState = {
        "incident_id": str(incident.id),
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity if isinstance(incident.severity, str) else incident.severity,
        "logs": logs,
    }

    graph = build_incident_graph(db)
    final_state = await graph.ainvoke(initial_state)

    root_cause_data = final_state.get("root_cause", {})
    recommendations = final_state.get("recommendations", [])

    incident.root_cause = root_cause_data.get("root_cause", "")
    incident.recommended_fix = (
        "\n".join(recommendations) if recommendations else incident.recommended_fix
    )
    incident.analysis_status = AnalysisStatus.COMPLETED.value
    metadata = dict(incident.metadata or {})
    metadata["classification"] = final_state.get("classification", {})
    incident.metadata = metadata

    report_service = ReportService(db)
    await report_service.create_from_ai(
        ReportCreateFromAI(
            incident_id=incident.id,
            title=f"Postmortem: {incident.title}",
            content_markdown=final_state.get("report_markdown", ""),
        )
    )

    await db.commit()
    logger.info("incident_analysis_completed", incident_id=incident_id)

    return {
        "incident_id": incident_id,
        "classification": final_state.get("classification"),
        "root_cause": root_cause_data,
        "recommendations": recommendations,
        "report_markdown": final_state.get("report_markdown"),
    }
