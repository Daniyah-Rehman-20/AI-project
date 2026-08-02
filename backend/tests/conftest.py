"""Pytest fixtures for API and unit tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.core.security import create_access_token
from app.database import models as _models  # noqa: F401
from app.database.models import Base, User
from app.database.seed import seed_database
from app.main import create_app

import tempfile

TEST_ADMIN_EMAIL = "admin@example.com"
TEST_ADMIN_PASSWORD = "TestAdmin123!"
_TEST_DB_PATH = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name


def get_test_settings() -> Settings:
    return Settings(
        app_env="test",
        app_secret_key="test-secret-key-at-least-32-characters-long",
        jwt_secret_key="test-jwt-secret-key-at-least-32-chars",
        database_url=f"sqlite+aiosqlite:///{_TEST_DB_PATH}",
        rate_limit_enabled=False,
        llm_provider="ollama",
        seed_admin_email=TEST_ADMIN_EMAIL,
        seed_admin_password=TEST_ADMIN_PASSWORD,
    )


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return get_test_settings()


@pytest_asyncio.fixture
async def db_engine(test_settings: Settings):
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_db(db_engine, test_settings: Settings) -> AsyncGenerator[None, None]:
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        await seed_database(session, test_settings)
        await session.commit()
    yield


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, seeded_db) -> User:
    from sqlalchemy import select

    result = await db_session.execute(
        select(User).where(User.email == TEST_ADMIN_EMAIL)
    )
    user = result.scalar_one()
    return user


@pytest.fixture
def auth_headers(admin_user: User, test_settings: Settings) -> dict[str, str]:
    token = create_access_token(
        subject=str(admin_user.id),
        extra_claims={"role": "admin"},
    )
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _noop_lifespan(app):
    yield


@pytest_asyncio.fixture
async def client(
    db_engine,
    test_settings: Settings,
    seeded_db,
) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    import app.database.session as db_session_module

    db_session_module._engine = db_engine
    db_session_module._session_factory = session_factory

    app = create_app(test_settings)
    app.router.lifespan_context = _noop_lifespan

    from app.database.session import get_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
