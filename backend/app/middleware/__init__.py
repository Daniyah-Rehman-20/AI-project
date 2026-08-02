"""HTTP middleware for request context and rate limiting."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import Settings, get_settings
from app.core.cache import get_cache
from app.core.logging import bind_request_context, clear_request_context, get_logger

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request ID, timing, and structured logging context."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.perf_counter()

        bind_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled_request_error", request_id=request_id)
            raise
        finally:
            clear_request_context()

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed rate limiter with in-memory fallback."""

    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self._settings = settings or get_settings()
        self._memory_buckets: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_exempt(self, request: Request) -> bool:
        path = request.url.path
        return path.endswith("/health") or path.endswith("/metrics") or path.startswith("/docs")

    async def _check_redis(self, key: str) -> bool:
        cache = get_cache()
        if not cache.is_available:
            await cache.connect()
        if not cache.is_available:
            return self._check_memory(key)

        redis_key = f"rate_limit:{key}"
        count = await cache.incr(redis_key, ttl=60)
        if count is None:
            return self._check_memory(key)
        return count <= self._settings.rate_limit_requests_per_minute

    def _check_memory(self, key: str) -> bool:
        now = time.time()
        window_start = now - 60
        bucket = self._memory_buckets[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= self._settings.rate_limit_requests_per_minute:
            return False
        bucket.append(now)
        return True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._settings.rate_limit_enabled or self._is_exempt(request):
            return await call_next(request)

        client_key = self._client_key(request)
        allowed = await self._check_redis(client_key)
        if not allowed:
            logger.warning("rate_limit_exceeded", client_key=client_key, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                },
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


__all__ = ["RateLimitMiddleware", "RequestContextMiddleware"]
