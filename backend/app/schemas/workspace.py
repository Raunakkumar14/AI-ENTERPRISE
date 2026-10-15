from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.workspace import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Workspace name must not be blank")
        return normalized


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Workspace name must not be blank")
        return normalized


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    plan: str
    is_active: bool
    created_at: datetime


class WorkspaceListItem(WorkspaceRead):
    role: WorkspaceRole


class MemberCreate(BaseModel):
    email: EmailStr = Field(max_length=255)
    role: WorkspaceRole = WorkspaceRole.USER

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class MemberRoleUpdate(BaseModel):
    role: WorkspaceRole


class MemberRead(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: WorkspaceRole
    is_active: bool
    joined_at: datetime


class WorkspaceAnalytics(BaseModel):
    document_count: int
    documents_by_status: dict[str, int]
    conversation_count: int
    active_member_count: int
