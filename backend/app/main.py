"""
backend/app/main.py
────────────────────
FastAPI application factory.

This module creates and configures the FastAPI app instance:
  - Lifespan context manager (startup / shutdown hooks)
  - CORS middleware (allows the React frontend to call the API)
  - API router registration under /api/v1
  - OpenAPI metadata

Run locally with:
    cd backend
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.config import settings
from app.routers import auth, documents, health, rag, workspaces

logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Async context manager that runs code on startup and shutdown.

    Startup  → runs before the server starts accepting requests.
    Shutdown → runs after the last request is handled.

    Add database table creation, model warm-up, etc. here in future phases.
    """
    # ── Startup ──────────────────────────────────────────────
    print(
        f"\n{settings.APP_NAME} v{settings.APP_VERSION} "
        f"[{settings.ENVIRONMENT}] starting up..."
    )
    print("Swagger UI: http://127.0.0.1:8000/docs")
    print("ReDoc:     http://127.0.0.1:8000/redoc\n")

    yield  # <── server is live here

    # ── Shutdown ─────────────────────────────────────────────
    print(f"\n{settings.APP_NAME} shutting down...")


# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    Returns the configured app instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-Powered Enterprise Knowledge Hub API with JWT authentication "
            "and tenant-isolated workspaces."
        ),
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────
    # Allow both local development hostnames; add the deployed frontend origin
    # to CORS_ORIGINS when moving the frontend to Render.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────
    # Each feature area gets its own router module under app/routers/.
    # Mount all routers under the /api/v1 prefix.
    app.include_router(health.router, prefix=settings.API_V1_PREFIX)
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(workspaces.router, prefix=settings.API_V1_PREFIX)
    app.include_router(documents.router, prefix=settings.API_V1_PREFIX)
    app.include_router(rag.router, prefix=settings.API_V1_PREFIX)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        del request
        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            error = exc.detail
        else:
            error = {
                "code": f"http_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
            }
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled API exception for %s %s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred",
                }
            },
        )

    return app


# ── App instance ──────────────────────────────────────────────────────────────
# Uvicorn imports this object:  uvicorn app.main:app
app: FastAPI = create_app()


# ── Root redirect (optional) ──────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Redirect hint for developers hitting the bare domain."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
