"""
backend/app/config.py
─────────────────────
Central configuration using Pydantic Settings.
All values are read from the .env file (or real environment variables).

Usage:
    from app.config import settings
    print(settings.DATABASE_URL)
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.

    Pydantic-settings automatically reads the .env file located at
    backend/.env  (one level above the app/ package).
    """

    # ── Application ───────────────────────────────────────────
    APP_NAME: str = "AI Knowledge Hub"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ── API ───────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────
    # Must use the asyncpg driver prefix: postgresql+asyncpg://
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/knowledge_hub"
    )

    # ── CORS ──────────────────────────────────────────────────
    # Stored as a comma-separated string in .env; parsed into a list below.
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    # ── AI / LLM ──────────────────────────────────────────────
    # Groq — set GROQ_API_KEY in .env to enable
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.8-27b"

    # Google Gemini — set GEMINI_API_KEY in .env to enable
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── Document ingestion ────────────────────────────────────
    MAX_DOCUMENT_SIZE_MB: int = Field(default=10, gt=0, le=100)
    MAX_EXTRACTED_TEXT_CHARS: int = Field(default=5_000_000, gt=0)
    DOCUMENT_CHUNK_SIZE: int = Field(default=1200, gt=0)
    DOCUMENT_CHUNK_OVERLAP: int = Field(default=200, ge=0)
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    RAG_LLM_PROVIDER: str = "gemini"
    RAG_TOP_K: int = Field(default=5, ge=1, le=20)
    RAG_RELEVANCE_THRESHOLD: float = Field(default=0.35, ge=0.0, le=1.0)
    RAG_MAX_CONTEXT_CHARS: int = Field(default=16000, gt=0)
    RAG_IVFFLAT_PROBES: int = Field(default=10, ge=1, le=100)

    # ── Authentication / JWT ──────────────────────────────────
    # Generate a strong secret: openssl rand -hex 32
    # NEVER commit a real secret to version control.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        return value

    @field_validator("DOCUMENT_CHUNK_OVERLAP")
    @classmethod
    def validate_chunk_overlap(cls, value: int, info) -> int:
        chunk_size = info.data.get("DOCUMENT_CHUNK_SIZE", 1200)
        if value >= chunk_size:
            raise ValueError("DOCUMENT_CHUNK_OVERLAP must be smaller than DOCUMENT_CHUNK_SIZE")
        return value

    @field_validator("RAG_LLM_PROVIDER")
    @classmethod
    def validate_rag_llm_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"gemini", "groq"}:
            raise ValueError("RAG_LLM_PROVIDER must be gemini or groq")
        return normalized

    # ── Pydantic-settings config ───────────────────────────────
    model_config = SettingsConfigDict(
        # Look for .env in the backend/ directory (parent of app/)
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",          # silently ignore unknown env vars
    )

    # ── Computed helpers ──────────────────────────────────────
    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS_ORIGINS as a Python list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    Using lru_cache means the .env file is read only once per process.
    FastAPI dependency injection example:

        from fastapi import Depends
        from app.config import get_settings, Settings

        @router.get("/info")
        def info(settings: Settings = Depends(get_settings)):
            return {"app": settings.APP_NAME}
    """
    return Settings()


# Module-level singleton for direct imports
settings: Settings = get_settings()
