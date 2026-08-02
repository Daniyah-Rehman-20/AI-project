"""Redis cache client with graceful degradation."""

from __future__ import annotations

import json
import time
from typing import Any

import redis.asyncio as aioredis
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Async Redis cache wrapper with JSON serialization."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: aioredis.Redis | None = None
        self._available = True
        self._memory_cache: dict[str, tuple[str, float | None]] = {}

    @property
    def is_available(self) -> bool:
        return self._available and self._client is not None

    async def connect(self) -> None:
        if self._client is not None:
            return
        try:
            self._client = aioredis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            await self._client.ping()
            self._available = True
            logger.info("redis_connected", url=self._settings.redis_url)
        except Exception as exc:
            self._available = False
            self._client = None
            logger.warning("redis_connection_failed", error=str(exc))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _default_ttl(self, ttl: int | None) -> int:
        return ttl if ttl is not None else self._settings.redis_cache_ttl

    async def get(self, key: str) -> Any | None:
        if self.is_available:
            try:
                raw = await self._client.get(key)  # type: ignore[union-attr]
                if raw is not None:
                    return json.loads(raw)
            except Exception as exc:
                logger.warning("redis_get_failed", key=key, error=str(exc))
        return await self._memory_get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        serialized = json.dumps(value, default=str)
        if self.is_available:
            try:
                await self._client.set(key, serialized, ex=self._default_ttl(ttl))  # type: ignore[union-attr]
                return True
            except Exception as exc:
                logger.warning("redis_set_failed", key=key, error=str(exc))
        await self._memory_set(key, serialized, ttl)
        return True

    async def delete(self, key: str) -> bool:
        if self.is_available:
            try:
                await self._client.delete(key)  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning("redis_delete_failed", key=key, error=str(exc))
        self._memory_cache.pop(key, None)
        return True

    async def exists(self, key: str) -> bool:
        if self.is_available:
            try:
                return bool(await self._client.exists(key))  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning("redis_exists_failed", key=key, error=str(exc))
        return key in self._memory_cache

    async def incr(self, key: str, ttl: int | None = None) -> int | None:
        if self.is_available:
            try:
                pipe = self._client.pipeline()  # type: ignore[union-attr]
                pipe.incr(key)
                pipe.expire(key, self._default_ttl(ttl))
                results = await pipe.execute()
                return int(results[0])
            except Exception as exc:
                logger.warning("redis_incr_failed", key=key, error=str(exc))
        current = int((await self._memory_get(key)) or 0) + 1
        await self._memory_set(key, str(current), ttl)
        return current

    async def _memory_get(self, key: str) -> Any | None:
        entry = self._memory_cache.get(key)
        if entry is None:
            return None
        value, expires = entry
        if expires is not None and time.time() > expires:
            del self._memory_cache[key]
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def _memory_set(self, key: str, value: str, ttl: int | None) -> None:
        expires = time.time() + ttl if ttl else None
        self._memory_cache[key] = (value, expires)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    async def ping(self) -> bool:
        if self._client is None:
            await self.connect()
        if self._client is None:
            return False
        await self._client.ping()
        return True


_cache_instance: RedisCache | None = None


def get_cache() -> RedisCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


def get_redis() -> RedisCache:
    return get_cache()


async def init_redis() -> None:
    await get_cache().connect()


async def close_redis() -> None:
    await get_cache().close()


async def cache_get(key: str) -> str | None:
    value = await get_cache().get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    await get_cache().set(key, value, ttl)


async def cache_delete(key: str) -> None:
    await get_cache().delete(key)


async def cache_get_json(key: str) -> Any | None:
    return await get_cache().get(key)
