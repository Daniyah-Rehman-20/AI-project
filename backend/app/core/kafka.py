"""Kafka producer and consumer worker utilities."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from app.config import Settings, get_settings
from app.core.exceptions import KafkaError
from app.core.logging import get_logger

logger = get_logger(__name__)

MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class KafkaProducer:
    """Async Kafka producer with JSON serialization."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._producer: AIOKafkaProducer | None = None
        self._available = True

    @property
    def is_available(self) -> bool:
        return self._available and self._producer is not None

    async def start(self) -> None:
        if self._producer is not None:
            return
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._settings.kafka_brokers,
                value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
                key_serializer=lambda key: key.encode("utf-8") if key else None,
                acks="all",
                enable_idempotence=True,
            )
            await self._producer.start()
            self._available = True
            logger.info("kafka_producer_started", brokers=self._settings.kafka_brokers)
        except KafkaConnectionError as exc:
            self._available = False
            self._producer = None
            logger.warning("kafka_producer_unavailable", error=str(exc))
        except Exception as exc:
            self._available = False
            self._producer = None
            logger.warning("kafka_producer_start_failed", error=str(exc))

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        key: str | None = None,
        raise_on_error: bool = False,
    ) -> bool:
        if not self.is_available:
            await self.start()
        if not self.is_available or self._producer is None:
            if raise_on_error:
                raise KafkaError("Kafka producer is unavailable")
            logger.warning("kafka_publish_skipped", topic=topic)
            return False
        try:
            await self._producer.send_and_wait(topic, payload, key=key)
            logger.debug("kafka_message_published", topic=topic, key=key)
            return True
        except Exception as exc:
            logger.warning("kafka_publish_failed", topic=topic, error=str(exc))
            if raise_on_error:
                raise KafkaError(f"Failed to publish to {topic}: {exc}") from exc
            return False


class KafkaConsumerWorker:
    """Long-running Kafka consumer that dispatches messages to handlers."""

    def __init__(
        self,
        topics: list[str],
        handler: MessageHandler,
        *,
        settings: Settings | None = None,
        group_id: str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._topics = topics
        self._handler = handler
        self._group_id = group_id or self._settings.kafka_consumer_group
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._settings.kafka_brokers,
            group_id=self._group_id,
            auto_offset_reset=self._settings.kafka_auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            key_deserializer=lambda key: key.decode("utf-8") if key else None,
        )
        await self._consumer.start()
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("kafka_consumer_started", topics=self._topics, group_id=self._group_id)

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        logger.info("kafka_consumer_stopped", topics=self._topics)

    async def _consume_loop(self) -> None:
        assert self._consumer is not None
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                topic = message.topic
                payload = message.value
                if not isinstance(payload, dict):
                    logger.warning("kafka_invalid_payload", topic=topic)
                    continue
                try:
                    await self._handler(topic, payload)
                except Exception as exc:
                    logger.exception(
                        "kafka_handler_failed",
                        topic=topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(exc),
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("kafka_consume_loop_failed", error=str(exc))
            self._running = False


_producer_instance: KafkaProducer | None = None


def get_kafka_producer() -> KafkaProducer:
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = KafkaProducer()
    return _producer_instance


async def init_kafka() -> None:
    await get_kafka_producer().start()


async def close_kafka() -> None:
    await get_kafka_producer().stop()


async def publish_event(topic: str, payload: dict[str, Any], *, key: str | None = None) -> bool:
    return await get_kafka_producer().publish(topic, payload, key=key)


async def create_consumer(topics: list[str]) -> AIOKafkaConsumer | None:
    settings = get_settings()
    try:
        consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=settings.kafka_brokers,
            group_id=settings.kafka_consumer_group,
            auto_offset_reset=settings.kafka_auto_offset_reset,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        await consumer.start()
        return consumer
    except Exception as exc:
        logger.warning("kafka_consumer_create_failed", error=str(exc))
        return None


def create_consumer_worker(
    topics: list[str],
    handler: MessageHandler,
    *,
    group_id: str | None = None,
) -> KafkaConsumerWorker:
    return KafkaConsumerWorker(topics, handler, group_id=group_id)
