"""Qdrant vector store client."""

from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Async Qdrant wrapper for document chunk vectors."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: AsyncQdrantClient | None = None

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key or None,
            )
        return self._client

    @property
    def collection_name(self) -> str:
        return self.settings.qdrant_collection

    async def ensure_collection(self) -> None:
        collections = await self.client.get_collections()
        names = [c.name for c in collections.collections]
        if self.collection_name not in names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.settings.embedding_dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            logger.info("qdrant_collection_created", collection=self.collection_name)

    async def upsert(
        self,
        *,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> list[str]:
        await self.ensure_collection()
        point_ids = ids or [str(uuid.uuid4()) for _ in vectors]
        points = [
            qmodels.PointStruct(id=pid, vector=vec, payload=pl)
            for pid, vec, pl in zip(point_ids, vectors, payloads, strict=True)
        ]
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info("qdrant_upserted", count=len(points))
        return point_ids

    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        await self.ensure_collection()

        query_filter = None
        if filter_conditions:
            must = [
                qmodels.FieldCondition(
                    key=key,
                    match=qmodels.MatchValue(value=value),
                )
                for key, value in filter_conditions.items()
            ]
            query_filter = qmodels.Filter(must=must)

        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )

        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results
        ]

    async def delete_by_document(self, document_id: str) -> int:
        await self.ensure_collection()
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
        logger.info("qdrant_deleted_by_document", document_id=document_id)
        return 1

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
