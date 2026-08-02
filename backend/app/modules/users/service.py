"""Admin user management service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.repository import BaseRepository
from app.core.security import hash_password
from app.database.models import Role, User
from app.modules.users.schemas import (
    AdminUserResponse,
    UserCreate,
    UserListResponse,
    UserUpdate,
)

logger = get_logger(__name__)


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).options(selectinload(User.role)).where(User.email == email.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_role(self, user_id: UUID) -> User | None:
        stmt = select(User).options(selectinload(User.role)).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        stmt = select(User).options(selectinload(User.role))
        count_stmt = select(func.count()).select_from(User)

        if search:
            pattern = f"%{search}%"
            filter_expr = User.email.ilike(pattern) | User.full_name.ilike(pattern)
            stmt = stmt.where(filter_expr)
            count_stmt = count_stmt.where(filter_expr)

        total = int((await self.db.execute(count_stmt)).scalar_one())
        offset = (page - 1) * page_size
        stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total


class UserAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)

    def _to_response(self, user: User) -> AdminUserResponse:
        return AdminUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_name=user.role.name if user.role else "viewer",
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def create(self, payload: UserCreate) -> AdminUserResponse:
        existing = await self.repo.get_by_email(payload.email)
        if existing:
            raise ConflictError("Email already registered")

        role = await self.repo.get_role_by_name(payload.role_name)
        if role is None:
            raise NotFoundError(f"Role '{payload.role_name}' not found")

        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role_id=role.id,
            is_active=payload.is_active,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user, attribute_names=["role"])
        await self.db.commit()
        logger.info("admin_user_created", user_id=str(user.id))
        return self._to_response(user)

    async def get(self, user_id: UUID) -> AdminUserResponse:
        user = await self.repo.get_with_role(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return self._to_response(user)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> UserListResponse:
        items, total = await self.repo.list_users(
            page=page,
            page_size=page_size,
            search=search,
        )
        return UserListResponse(
            items=[self._to_response(u) for u in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(self, user_id: UUID, payload: UserUpdate) -> AdminUserResponse:
        user = await self.repo.get_with_role(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")

        if payload.email is not None:
            existing = await self.repo.get_by_email(payload.email)
            if existing and existing.id != user_id:
                raise ConflictError("Email already in use")
            user.email = payload.email.lower()

        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.password is not None:
            user.hashed_password = hash_password(payload.password)
        if payload.role_name is not None:
            role = await self.repo.get_role_by_name(payload.role_name)
            if role is None:
                raise NotFoundError(f"Role '{payload.role_name}' not found")
            user.role_id = role.id

        await self.db.flush()
        await self.db.refresh(user, attribute_names=["role"])
        await self.db.commit()
        return self._to_response(user)

    async def delete(self, user_id: UUID) -> None:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        await self.repo.delete(user)
        await self.db.commit()
        logger.info("admin_user_deleted", user_id=str(user_id))
