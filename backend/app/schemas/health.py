"""
backend/app/schemas/health.py
──────────────────────────────
Pydantic response schema for the health-check endpoint.

Pydantic models (schemas) are used to:
  - Validate request bodies (input)
  - Serialize response data   (output)
They are separate from SQLAlchemy models (database tables).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Response body returned by GET /api/v1/health.

    Attributes
    ----------
    status : str
        "ok" when the service is healthy.
    app_name : str
        Human-readable application name from settings.
    version : str
        Semantic version string (e.g. "0.1.0").
    environment : str
        Deployment environment ("development", "staging", "production").
    """

    status: str = Field(..., examples=["ok"])
    app_name: str = Field(..., examples=["AI Knowledge Hub"])
    version: str = Field(..., examples=["0.1.0"])
    environment: str = Field(..., examples=["development"])

    model_config = {"json_schema_extra": {"example": {
        "status": "ok",
        "app_name": "AI Knowledge Hub",
        "version": "0.1.0",
        "environment": "development",
    }}}
