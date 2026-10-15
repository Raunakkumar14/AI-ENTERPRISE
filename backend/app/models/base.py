"""
backend/app/models/base.py
───────────────────────────
Shared SQLAlchemy declarative base and reusable mixins.

All ORM model classes (e.g. Document, User, Chunk) should inherit
from `Base` defined here.  TimestampMixin adds created_at / updated_at
columns that are managed automatically by the database.

Example usage in a future model file:
    from app.models.base import Base, TimestampMixin

    class Document(Base, TimestampMixin):
        __tablename__ = "documents"
        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str] = mapped_column(String(255))
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.x declarative base.

    All models import and subclass this `Base`.
    Alembic's env.py also imports it so that `autogenerate` can
    detect schema changes automatically.
    """
    pass


class TimestampMixin:
    """
    Mixin that adds `created_at` and `updated_at` columns to any model.

    - created_at : Set once at INSERT time by the database server.
    - updated_at : Refreshed on every UPDATE by the database server.

    Using server_default / onupdate means these are managed by PostgreSQL,
    not Python, so they are always accurate even for bulk operations.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),   # PostgreSQL NOW()
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),         # auto-updated on every UPDATE
        nullable=False,
    )
