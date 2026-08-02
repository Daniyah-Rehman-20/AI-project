"""Data access layer for authentication."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository
from app.database.models import Role, Session, User


class AuthRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).options(selectinload(User.role)).where(User.email == email.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_role(self, user_id: UUID) -> User | None:
        stmt = select(User).options(selectinload(User.role)).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_role(self) -> Role | None:
        stmt = select(Role).where(Role.name == "viewer")
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str,
        role_id: UUID,
    ) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            role_id=role_id,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user, attribute_names=["role"])
        return user

    async def create_session(
        self,
        *,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> Session:
        session = Session(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session_by_hash(self, refresh_token_hash: str) -> Session | None:
        stmt = (
            select(Session)
            .options(selectinload(Session.user).selectinload(User.role))
            .where(Session.refresh_token_hash == refresh_token_hash)
            .where(Session.revoked_at.is_(None))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_session(self, session: Session) -> None:
        session.revoked_at = datetime.now(UTC)
        await self.db.flush()

    async def revoke_all_user_sessions(self, user_id: UUID) -> int:
        stmt = select(Session).where(
            Session.user_id == user_id,
            Session.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        now = datetime.now(UTC)
        for session in sessions:
            session.revoked_at = now
        await self.db.flush()
        return len(sessions)
