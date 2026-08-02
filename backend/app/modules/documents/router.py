"""Document management API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile

from app.core.enums import DocumentStatus
from app.database.models import User
from app.dependencies import DbSession, require_permission
from app.modules.documents.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.modules.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    db: DbSession,
    user: User = Depends(require_permission("documents", "create")),
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
) -> DocumentUploadResponse:
    content = await file.read()
    return await DocumentService(db).upload(
        file_content=content,
        filename=file.filename or "upload.bin",
        title=title,
        content_type=file.content_type,
        uploaded_by_id=user.id,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: DbSession,
    user: User = Depends(require_permission("documents", "read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: DocumentStatus | None = None,
) -> DocumentListResponse:
    return await DocumentService(db).list(page=page, page_size=page_size, status=status)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("documents", "read")),
) -> DocumentResponse:
    return await DocumentService(db).get(document_id)


@router.delete("/{document_id}", status_code=204, response_class=Response)
async def delete_document(
    document_id: UUID,
    db: DbSession,
    user: User = Depends(require_permission("documents", "delete")),
) -> Response:
    await DocumentService(db).delete(document_id)
    return Response(status_code=204)
