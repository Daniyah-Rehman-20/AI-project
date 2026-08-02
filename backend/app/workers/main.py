"""Kafka worker consumers for async processing."""

from __future__ import annotations

import asyncio
import json
import signal
import uuid
from typing import Any

from app.config import get_settings
from app.core.kafka import create_consumer, publish_event
from app.core.logging import get_logger
from app.database.session import async_session_factory, init_db
from app.modules.agents.graph import run_incident_analysis
from app.modules.logs.service import LogService
from app.modules.logs.schemas import LogIngestRequest
from app.modules.rag.pipeline import RAGPipeline
from app.core.enums import LogLevel

logger = get_logger(__name__)

TOPICS = ["documents_uploaded", "incident_created", "application_logs"]


class WorkerManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._running = True
        self._tasks: list[asyncio.Task] = []

    def _handle_signal(self) -> None:
        self._running = False
        logger.info("worker_shutdown_requested")

    async def _process_documents_uploaded(self, payload: dict[str, Any]) -> None:
        document_id = payload.get("document_id")
        if not document_id:
            logger.warning("documents_uploaded_missing_id", payload=payload)
            return

        async with async_session_factory() as db:
            pipeline = RAGPipeline(db)
            result = await pipeline.process_document(uuid.UUID(document_id))
            logger.info("document_indexed", **result)

        await publish_event(
            "embeddings_created",
            {"document_id": document_id, "status": result.get("status")},
        )

    async def _process_incident_created(self, payload: dict[str, Any]) -> None:
        incident_id = payload.get("incident_id")
        if not incident_id:
            logger.warning("incident_created_missing_id", payload=payload)
            return

        async with async_session_factory() as db:
            result = await run_incident_analysis(db, incident_id)
            logger.info("incident_analysis_done", incident_id=incident_id)

        await publish_event(
            "analysis_completed",
            {
                "incident_id": incident_id,
                "root_cause": result.get("root_cause", {}).get("root_cause"),
            },
        )

    async def _process_application_logs(self, payload: dict[str, Any]) -> None:
        incident_id = payload.get("incident_id")
        message = payload.get("message", "")
        level_str = payload.get("level", "info")

        try:
            level = LogLevel(level_str)
        except ValueError:
            level = LogLevel.INFO

        async with async_session_factory() as db:
            service = LogService(db)
            await service.ingest(
                LogIngestRequest(
                    message=message,
                    level=level,
                    source=payload.get("source"),
                    incident_id=uuid.UUID(incident_id) if incident_id else None,
                ),
                publish=False,
            )

    async def _handle_message(self, topic: str, raw_value: bytes | dict) -> None:
        try:
            if isinstance(raw_value, dict):
                payload = raw_value
            else:
                payload = json.loads(raw_value.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("worker_message_decode_failed", topic=topic, error=str(exc))
            return

        handlers = {
            "documents_uploaded": self._process_documents_uploaded,
            "incident_created": self._process_incident_created,
            "application_logs": self._process_application_logs,
        }
        handler = handlers.get(topic)
        if handler is None:
            logger.warning("worker_unknown_topic", topic=topic)
            return

        try:
            await handler(payload)
        except Exception as exc:
            logger.error(
                "worker_handler_failed",
                topic=topic,
                error=str(exc),
                exc_info=True,
            )

    async def _consume_topic(self, topic: str) -> None:
        consumer = await create_consumer([topic])
        if consumer is None:
            logger.warning("kafka_consumer_unavailable", topic=topic)
            return

        logger.info("worker_consuming", topic=topic)
        try:
            async for message in consumer:
                if not self._running:
                    break
                await self._handle_message(topic, message.value)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("worker_consumer_error", topic=topic, error=str(exc))
        finally:
            await consumer.stop()

    async def run(self) -> None:
        await init_db()
        logger.info("worker_started", topics=TOPICS, concurrency=self.settings.worker_concurrency)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_signal)

        self._tasks = [asyncio.create_task(self._consume_topic(topic)) for topic in TOPICS]

        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass
        finally:
            for task in self._tasks:
                task.cancel()
            logger.info("worker_stopped")


async def main() -> None:
    manager = WorkerManager()
    await manager.run()


if __name__ == "__main__":
    asyncio.run(main())
