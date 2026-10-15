"""
backend/app/routers/health.py
──────────────────────────────
Health-check router — the first working API endpoint.

Endpoint:  GET /api/v1/health
Purpose:   Liveness probe to confirm the service is running.
           Also used by load-balancers, Docker HEALTHCHECK, and CI pipelines.

No database call is made here intentionally; this endpoint should respond
even when the DB is down so that the process itself can be confirmed alive.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["Health"],          # groups this endpoint in Swagger UI
)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness probe",
    description=(
        "Returns HTTP 200 with basic application metadata when the service "
        "is running. Does **not** check database connectivity."
    ),
)
async def health_check() -> HealthResponse:
    """
    Liveness probe endpoint.

    Returns
    -------
    HealthResponse
        JSON object with status, app name, version, and environment.
    """
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
