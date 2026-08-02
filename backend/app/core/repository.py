"""Generic async repository base."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, db: AsyncSession, model: type[T]) -> None:
        self.db = db
        self.model = model

    async def get_by_id(self, entity_id: str | object) -> T | None:
        key = str(entity_id)
        return await self.db.get(self.model, key)

    async def delete(self, entity: T) -> None:
        await self.db.delete(entity)
        await self.db.flush()
