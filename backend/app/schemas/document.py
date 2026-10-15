from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    uploaded_by_id: int
    filename: str
    file_type: str
    file_size_bytes: int
    sha256: str
    embedding_model: str | None
    status: DocumentStatus
    page_count: int | None
    chunk_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentChunkRead(BaseModel):
    id: int
    chunk_index: int
    page_number: int | None
    content: str


class DocumentDetail(DocumentRead):
    chunks: list[DocumentChunkRead]


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int
    limit: int
    offset: int
