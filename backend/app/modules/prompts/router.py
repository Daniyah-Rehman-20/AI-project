"""Versioned prompt management."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.database.models import PromptVersion, User
from app.dependencies import DbSession, require_permission

logger = get_logger(__name__)

router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=500)


class PromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    content: str
    description: str | None
    is_active: bool
    created_by_id: UUID | None
    created_at: datetime


class PromptListResponse(BaseModel):
    items: list[PromptResponse]
    total: int


class PromptService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_prompts(
        self,
        *,
        name: str | None = None,
        active_only: bool = False,
    ) -> PromptListResponse:
        stmt = select(PromptVersion)
        count_stmt = select(func.count()).select_from(PromptVersion)

        if name:
            stmt = stmt.where(PromptVersion.name == name)
            count_stmt = count_stmt.where(PromptVersion.name == name)
        if active_only:
            stmt = stmt.where(PromptVersion.is_active.is_(True))
            count_stmt = count_stmt.where(PromptVersion.is_active.is_(True))

        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(PromptVersion.name, PromptVersion.created_at.desc())
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return PromptListResponse(
            items=[PromptResponse.model_validate(p) for p in items],
            total=total,
        )

    async def create(
        self,
        payload: PromptCreate,
        *,
        created_by_id: UUID,
    ) -> PromptResponse:
        existing = await self.db.execute(
            select(PromptVersion).where(
                PromptVersion.name == payload.name,
                PromptVersion.version == payload.version,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Prompt {payload.name} version {payload.version} already exists")

        prompt = PromptVersion(
            name=payload.name,
            version=payload.version,
            content=payload.content,
            description=payload.description,
            is_active=False,
            created_by_id=created_by_id,
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        logger.info("prompt_created", name=payload.name, version=payload.version)
        return PromptResponse.model_validate(prompt)

    async def get(self, prompt_id: UUID) -> PromptResponse:
        result = await self.db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError(f"Prompt {prompt_id} not found")
        return PromptResponse.model_validate(prompt)

    async def activate(self, prompt_id: UUID) -> PromptResponse:
        result = await self.db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError(f"Prompt {prompt_id} not found")

        await self.db.execute(
            update(PromptVersion).where(PromptVersion.name == prompt.name).values(is_active=False)
        )
        prompt.is_active = True
        await self.db.commit()
        await self.db.refresh(prompt)
        logger.info("prompt_activated", prompt_id=str(prompt_id))
        return PromptResponse.model_validate(prompt)

    async def delete(self, prompt_id: UUID) -> None:
        result = await self.db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError(f"Prompt {prompt_id} not found")
        await self.db.delete(prompt)
        await self.db.commit()


@router.get("", response_model=PromptListResponse)
async def list_prompts(
    db: DbSession,
    user: User = Depends(require_permission("prompts", "read")),
    name: str | None = None,
    active_only: bool = Query(False),
) -> PromptListResponse:
    return await PromptService(db).list_prompts(name=name, active_only=active_only)


@router.post("", response_model=PromptResponse, status_code=201)
async def create_prompt(
    payload: PromptCreate,
    db: DbSession,
    user: User = Depends(require_permission("prompts", "create")),
) -> PromptResponse:
    return await PromptService(db).create(payload, created_by_id=user.id)


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("prompts", "read")),
) -> PromptResponse:
    return await PromptService(db).get(prompt_id)


@router.post("/{prompt_id}/activate", response_model=PromptResponse)
async def activate_prompt(
    prompt_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("prompts", "update")),
) -> PromptResponse:
    return await PromptService(db).activate(prompt_id)


@router.delete("/{prompt_id}", status_code=204, response_class=Response)
async def delete_prompt(
    prompt_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("prompts", "delete")),
) -> Response:
    await PromptService(db).delete(prompt_id)
    return Response(status_code=204)
