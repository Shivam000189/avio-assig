"""Tests for the health-check endpoints.

These tests run against the FastAPI test client without requiring a live
database — the Prisma client is either not connected or mocked.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

app = create_app()


@pytest.mark.anyio
async def test_health_returns_ok() -> None:
    """GET /api/v1/health should return 200 with status 'ok'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert "app" in body


@pytest.mark.anyio
async def test_health_db_disconnected() -> None:
    """GET /api/v1/health/db should return 503 when the DB is unreachable.

    We patch the module-level `prisma` object in the health router to use
    a mock whose `query_raw` raises, so the test never requires a running
    PostgreSQL instance.
    """
    mock_prisma = AsyncMock()
    mock_prisma.query_raw.side_effect = ConnectionError("Simulated DB failure")

    with patch("app.routers.health.prisma", mock_prisma):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/db")

    assert response.status_code == 503
    assert response.json()["database"] == "disconnected"
