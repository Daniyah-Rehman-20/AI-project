"""Document upload and management service."""

from __future__ import annotations

import mimetypes
import uuid
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DocumentStatus
from app.core.exceptions import NotFoundError
from app.core.kafka import publish_event
from app.core.logging import get_logger
from app.core.repository import BaseRepository
from app.core.storage import get_storage
from app.database.models import Document
from app.modules.documents.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

logger = get_logger(__name__)

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Document)

    async def list_documents(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: DocumentStatus | None = None,
        uploaded_by_id: UUID | None = None,
    ) -> tuple[list[Document], int]:
        stmt = select(Document)
        count_stmt = select(func.count()).select_from(Document)

        if status is not None:
            stmt = stmt.where(Document.status == status)
            count_stmt = count_stmt.where(Document.status == status)
        if uploaded_by_id is not None:
            stmt = stmt.where(Document.uploaded_by_id == uploaded_by_id)
            count_stmt = count_stmt.where(Document.uploaded_by_id == uploaded_by_id)

        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one())

        offset = (page - 1) * page_size
        stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def create_document(
        self,
        *,
        title: str,
        filename: str,
        content_type: str,
        storage_key: str,
        size_bytes: int,
        uploaded_by_id: str,
    ) -> Document:
        doc = Document(
            title=title,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            size_bytes=size_bytes,
            status=DocumentStatus.PENDING.value,
            uploaded_by=uploaded_by_id,
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DocumentRepository(db)
        self.storage = get_storage()

    def _validate_content_type(self, content_type: str, filename: str) -> str:
        resolved = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if resolved not in ALLOWED_CONTENT_TYPES:
            base = resolved.split(";")[0].strip()
            if base not in ALLOWED_CONTENT_TYPES:
                raise ValueError(
                    f"Unsupported content type: {resolved}. "
                    f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
                )
            return base
        return resolved

    async def upload(
        self,
        *,
        file_content: bytes,
        filename: str,
        title: str | None,
        content_type: str | None,
        uploaded_by_id: UUID,
    ) -> DocumentUploadResponse:
        resolved_type = self._validate_content_type(content_type or "", filename)
        doc_id = uuid.uuid4()
        storage_key = f"documents/{doc_id}/{filename}"

        await self.storage.put_object(
            key=storage_key,
            data=file_content,
            content_type=resolved_type,
        )

        document = await self.repo.create_document(
            title=title or filename,
            filename=filename,
            content_type=resolved_type,
            storage_key=storage_key,
            size_bytes=len(file_content),
            uploaded_by_id=uploaded_by_id,
        )
        await self.db.commit()

        await publish_event(
            "documents_uploaded",
            {
                "document_id": str(document.id),
                "storage_key": storage_key,
                "content_type": resolved_type,
                "filename": filename,
            },
        )
        logger.info("document_uploaded", document_id=str(document.id))
        return DocumentUploadResponse(document=DocumentResponse.model_validate(document))

    async def get(self, document_id: UUID) -> DocumentResponse:
        doc = await self.repo.get_by_id(document_id)
        if doc is None:
            raise NotFoundError(f"Document {document_id} not found")
        return DocumentResponse.model_validate(doc)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: DocumentStatus | None = None,
        uploaded_by_id: UUID | None = None,
    ) -> DocumentListResponse:
        items, total = await self.repo.list_documents(
            page=page,
            page_size=page_size,
            status=status,
            uploaded_by_id=uploaded_by_id,
        )
        return DocumentListResponse(
            items=[DocumentResponse.model_validate(d) for d in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def delete(self, document_id: UUID) -> None:
        doc = await self.repo.get_by_id(document_id)
        if doc is None:
            raise NotFoundError(f"Document {document_id} not found")

        try:
            await self.storage.delete_object(doc.storage_key)
        except Exception as exc:
            logger.warning(
                "document_storage_delete_failed",
                document_id=str(document_id),
                error=str(exc),
            )

        await self.repo.delete(doc)
        await self.db.commit()
        logger.info("document_deleted", document_id=str(document_id))
