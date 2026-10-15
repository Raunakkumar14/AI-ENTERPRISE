"""
backend/app/models/user.py
───────────────────────────
SQLAlchemy ORM model for the `users` table.

Columns
-------
id              : Auto-increment integer primary key.
email           : Unique, indexed — used as the login identifier.
hashed_password : bcrypt hash. Raw passwords are NEVER stored.
full_name       : Display name.
is_active       : False = account disabled (soft-delete alternative).
is_superuser    : True = platform-level admin (future use).
created_at      : Set by DB on INSERT (from TimestampMixin).
updated_at      : Updated by DB on every UPDATE (from TimestampMixin).
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # ── Identity ──────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    # ── Flags ─────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # ── Relationships ─────────────────────────────────────────
    # A user can be a member of many workspaces.
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
