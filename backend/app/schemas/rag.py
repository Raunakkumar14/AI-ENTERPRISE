from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    conversation_id: int | None = Field(default=None, gt=0)


class CitationRead(BaseModel):
    source_id: str
    document_id: int
    document_name: str
    page_number: int | None
    chunk_index: int
    excerpt: str
    relevance_score: float


class AskResponse(BaseModel):
    conversation_id: int
    answer: str
    citations: list[CitationRead]
    insufficient_context: bool


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    citations: list[CitationRead]
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class ConversationList(BaseModel):
    items: list[ConversationRead]
    total: int
    limit: int
    offset: int
