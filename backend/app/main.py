"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.kafka import close_kafka, init_kafka
from app.core.cache import close_redis, init_redis
from app.core.logging import get_logger
from app.core.storage import init_storage
from app.database.seed import seed_database
from app.database.session import close_db, init_db
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.documents.router import router as documents_router
from app.modules.incidents.router import router as incidents_router
from app.modules.integrations.router import router as integrations_router
from app.modules.logs.router import router as logs_router
from app.modules.notifications.router import router as notifications_router
from app.modules.prompts.router import router as prompts_router
from app.modules.reports.router import router as reports_router
from app.modules.users import (
    apikeys_router,
    audit_router,
    feedback_router,
    health_router,
    search_router,
    users_router,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("app_starting", env=settings.app_env)

    await init_db()
    await seed_database()
    await init_redis()
    try:
        import asyncio

        await asyncio.wait_for(init_kafka(), timeout=5.0)
    except Exception as exc:
        logger.warning("kafka_init_skipped", error=str(exc))
    await init_storage()

    yield

    await close_kafka()
    await close_redis()
    await close_db()
    logger.info("app_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Enterprise AI Incident Intelligence Platform API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware)

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.error_code},
        )

    prefix = settings.app_api_prefix

    app.include_router(health_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(incidents_router, prefix=prefix)
    app.include_router(logs_router, prefix=prefix)
    app.include_router(documents_router, prefix=prefix)
    app.include_router(reports_router, prefix=prefix)
    app.include_router(notifications_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    app.include_router(search_router, prefix=prefix)
    app.include_router(feedback_router, prefix=prefix)
    app.include_router(audit_router, prefix=prefix)
    app.include_router(apikeys_router, prefix=prefix)
    app.include_router(integrations_router, prefix=prefix)
    app.include_router(prompts_router, prefix=prefix)

    return app


app = create_app()
