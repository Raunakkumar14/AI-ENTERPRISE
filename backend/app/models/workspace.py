"""
backend/app/models/workspace.py
─────────────────────────────────
SQLAlchemy ORM models for workspaces and multi-tenant membership.

Tables
------
workspaces        : Each workspace is an isolated tenant environment.
workspace_members : Junction table linking users to workspaces with a role.

Roles (WorkspaceRole enum)
--------------------------
admin         : Full control — invite/remove members, manage workspace settings.
support_agent : Can manage support tickets and view documents.
user          : Read-only access; can run AI queries.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class WorkspacePlan(str, enum.Enum):
    """Subscription plan tier."""
    STARTER    = "starter"
    PRO        = "pro"
    ENTERPRISE = "enterprise"


class WorkspaceRole(str, enum.Enum):
    """
    Role a member holds inside a specific workspace.

    ADMIN         – full workspace control
    SUPPORT_AGENT – ticket + document management
    USER          – query-only access
    """
    ADMIN         = "admin"
    SUPPORT_AGENT = "support_agent"
    USER          = "user"


# ── Workspace ─────────────────────────────────────────────────────────────────

class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint(
            "plan IN ('starter', 'pro', 'enterprise')",
            name="ck_workspaces_plan",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str]         = mapped_column(String(255), nullable=False)
    slug: Mapped[str]         = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str]         = mapped_column(String(20), default=WorkspacePlan.STARTER.value, nullable=False)
    owner_id: Mapped[int]     = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool]   = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ──────────────────────────────────────────
    owner: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[owner_id], lazy="select"
    )
    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} slug={self.slug!r} plan={self.plan}>"


# ── WorkspaceMember ───────────────────────────────────────────────────────────

class WorkspaceMember(Base):
    """
    Junction row that records which role a user holds in a workspace.

    A user can belong to multiple workspaces with different roles.
    The (workspace_id, user_id) pair is UNIQUE — no duplicate memberships.
    """
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
        CheckConstraint(
            "role IN ('admin', 'support_agent', 'user')",
            name="ck_workspace_members_role",
        ),
    )

    id: Mapped[int]           = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id: Mapped[int]      = mapped_column(Integer, ForeignKey("users.id"),      nullable=False, index=True)
    role: Mapped[str]         = mapped_column(String(20), default=WorkspaceRole.USER.value, nullable=False)
    is_active: Mapped[bool]   = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="workspace_memberships"
    )

    # ── Helpers ────────────────────────────────────────────────
    def has_role(self, *roles: WorkspaceRole) -> bool:
        """Return True if this member's role is one of the given roles."""
        return self.role in {r.value for r in roles}

    def __repr__(self) -> str:
        return f"<WorkspaceMember ws={self.workspace_id} user={self.user_id} role={self.role}>"
