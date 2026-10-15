from __future__ import annotations

import hashlib
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.responses import Response

from app.config import settings
from app.core.auth import get_workspace_membership, require_document_manager
from app.core.errors import api_error
from app.database import AsyncSessionLocal, get_db
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.workspace import WorkspaceMember
from app.schemas.document import (
    DocumentChunkRead,
    DocumentDetail,
    DocumentList,
    DocumentRead,
)
from app.services.document_ingestion import process_uploaded_document
from app.services.embeddings import EmbeddingProvider, get_embedding_provider

router = APIRouter(
    prefix="/workspaces/{workspace_id}/documents",
    tags=["Documents"],
)

_SUPPORTED_TYPES = {
    ".pdf": "pdf",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
}


def get_document_session_factory() -> async_sessionmaker[AsyncSession]:
    return AsyncSessionLocal


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and ingest a document",
)
async def upload_document(
    workspace_id: int,
    background_tasks: BackgroundTasks,
    _manager: Annotated[WorkspaceMember, Depends(require_document_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_document_session_factory),
    ],
    file: Annotated[UploadFile, File(description="PDF, Markdown, or UTF-8 plain text")],
) -> Document:
    filename = _safe_filename(file.filename)
    suffix = PurePosixPath(filename).suffix.lower()
    file_type = _SUPPORTED_TYPES.get(suffix)
    if file_type is None:
        raise api_error(
            415,
            "unsupported_file_type",
            "Only PDF, Markdown, and plain-text files are supported",
        )

    max_bytes = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise api_error(
            413,
            "file_too_large",
            f"Document exceeds the {settings.MAX_DOCUMENT_SIZE_MB} MB size limit",
        )
    if not content:
        raise api_error(422, "empty_file", "The uploaded file is empty")

    normalized_type = file_type
    if normalized_type == "pdf" and b"%PDF-" not in content[:1024]:
        raise api_error(422, "invalid_file", "The uploaded file is not a valid PDF")

    document = Document(
        workspace_id=workspace_id,
        uploaded_by_id=_manager.user_id,
        filename=filename,
        file_type=normalized_type,
        file_size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        embedding_model=settings.EMBEDDING_MODEL,
        status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    await db.flush()
    await db.commit()

    background_tasks.add_task(
        process_uploaded_document,
        document.id,
        filename,
        content,
        embedding_provider,
        session_factory,
    )
    return document


@router.get("", response_model=DocumentList, summary="List workspace documents")
async def list_documents(
    workspace_id: int,
    _membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentList:
    total_result = await db.execute(
        select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
    )
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return DocumentList(
        items=list(result.scalars().all()),
        total=total_result.scalar_one(),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get document details and extracted chunks",
)
async def get_document(
    workspace_id: int,
    document_id: int,
    _membership: Annotated[WorkspaceMember, Depends(get_workspace_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentDetail:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise api_error(404, "document_not_found", "Document not found")

    chunk_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return DocumentDetail(
        **DocumentRead.model_validate(document).model_dump(),
        chunks=[
            DocumentChunkRead(
                id=chunk.id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                content=chunk.content,
            )
            for chunk in chunk_result.scalars().all()
        ],
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and its chunks",
)
async def delete_document(
    workspace_id: int,
    document_id: int,
    _manager: Annotated[WorkspaceMember, Depends(require_document_manager)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise api_error(404, "document_not_found", "Document not found")

    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _safe_filename(filename: str | None) -> str:
    if not filename:
        raise api_error(422, "invalid_filename", "A filename is required")
    safe_name = PurePosixPath(filename.replace("\\", "/")).name
    if safe_name in {"", ".", ".."} or len(safe_name) > 255:
        raise api_error(422, "invalid_filename", "The filename is invalid")
    return safe_name
