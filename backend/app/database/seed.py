"""Database seed data for roles and bootstrap admin user."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.enums import RBAC_PERMISSIONS, RoleName
from app.core.logging import get_logger
from app.core.security import hash_password
from app.database.models import Role, User

logger = get_logger(__name__)

ROLE_DESCRIPTIONS: dict[RoleName, str] = {
    RoleName.ADMIN: "Full platform administrator",
    RoleName.ANALYST: "Incident analyst with AI workflow access",
    RoleName.ENGINEER: "Engineering responder with incident write access",
    RoleName.VIEWER: "Read-only stakeholder access",
}


async def seed_roles(session: AsyncSession) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for role_name in RoleName:
        result = await session.execute(select(Role).where(Role.name == role_name.value))
        role = result.scalar_one_or_none()
        permissions = sorted(RBAC_PERMISSIONS[role_name])
        if role is None:
            role = Role(
                name=role_name.value,
                description=ROLE_DESCRIPTIONS[role_name],
                permissions=permissions,
            )
            session.add(role)
            logger.info("role_created", role=role_name.value)
        else:
            role.description = ROLE_DESCRIPTIONS[role_name]
            role.permissions = permissions
        roles[role_name.value] = role

    await session.flush()
    return roles


async def seed_admin_user(session: AsyncSession, settings: Settings | None = None) -> User | None:
    settings = settings or get_settings()
    roles = await seed_roles(session)
    admin_role = roles[RoleName.ADMIN.value]

    result = await session.execute(select(User).where(User.email == settings.seed_admin_email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        logger.debug("admin_user_exists", email=settings.seed_admin_email)
        return existing

    admin_user = User(
        email=settings.seed_admin_email,
        hashed_password=hash_password(settings.seed_admin_password),
        full_name=settings.seed_admin_name,
        role_id=admin_role.id,
        is_active=True,
        is_verified=True,
    )
    session.add(admin_user)
    await session.flush()
    logger.info("admin_user_created", email=settings.seed_admin_email)
    return admin_user


async def seed_database(
    session: AsyncSession | None = None,
    settings: Settings | None = None,
) -> None:
    """Seed roles and bootstrap admin user."""
    settings = settings or get_settings()
    if session is not None:
        await seed_roles(session)
        await seed_admin_user(session, settings)
        return

    from app.database.session import get_session_factory

    factory = get_session_factory()
    async with factory() as managed_session:
        await seed_roles(managed_session)
        await seed_admin_user(managed_session, settings)
        await managed_session.commit()
