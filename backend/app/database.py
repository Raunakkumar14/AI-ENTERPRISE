"""
backend/app/database.py
────────────────────────
Async SQLAlchemy engine, session factory, and dependency helpers.

Key concepts:
  - AsyncEngine   : The connection pool (one per process).
  - AsyncSession  : A unit-of-work; request-scoped in FastAPI.
  - get_db()      : FastAPI dependency that yields a session per request
                    and auto-commits/rolls-back + closes it.

pgvector note:
  Before applying the document-ingestion migration, ensure the pgvector
  extension is installed in PostgreSQL. The migration enables it when
  the database role has permission; otherwise create it as an administrator:
      CREATE EXTENSION IF NOT EXISTS vector;
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# echo=True prints all SQL to stdout in development — very handy for debugging.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # disable in production
    pool_pre_ping=True,           # check connection health before using it
    pool_size=5,                  # concurrent connections kept open
    max_overflow=10,              # extra connections allowed under load
)

# ── Session factory ───────────────────────────────────────────────────────────
# expire_on_commit=False prevents lazy-loading errors after commit in async code
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session for a single request.

    Usage in a router:
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.database import get_db

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
