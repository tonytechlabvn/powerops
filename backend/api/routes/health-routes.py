"""Health check route — GET /api/health.

Reports database connectivity and terraform binary availability.
"""
from __future__ import annotations

import asyncio
import shutil

from fastapi import APIRouter

from backend.api.schemas.response_schemas import HealthResponse
from backend.db.database import get_session

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return system health status."""
    db_status = await _check_database()
    tf_status = _check_terraform()
    overall = "ok" if db_status == "connected" and tf_status == "available" else "degraded"
    return HealthResponse(status=overall, database=db_status, terraform=tf_status)


async def _check_database() -> str:
    try:
        async with get_session() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return "connected"
    except Exception:
        return "error"


def _check_terraform() -> str:
    return "available" if shutil.which("terraform") else "not_found"
