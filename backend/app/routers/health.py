"""Health-check router.

Exposes liveness and database-readiness endpoints under the /health prefix.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import prisma

router = APIRouter(prefix="/health", tags=["health"])

APP_VERSION = "0.1.0"


@router.get(
    "",
    summary="Liveness check",
    response_description="Basic application status",
)
async def health() -> dict[str, str]:
    """Return a simple liveness payload including the app name and version."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": APP_VERSION,
    }


@router.get(
    "/db",
    summary="Database readiness check",
    response_description="Database connectivity status",
)
async def health_db() -> JSONResponse:
    """Probe the database with a trivial query and report connectivity."""
    try:
        await prisma.query_raw("SELECT 1")
        return JSONResponse(
            content={"database": "connected"},
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        return JSONResponse(
            content={"database": "disconnected"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
