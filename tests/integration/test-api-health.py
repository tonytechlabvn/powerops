"""Integration tests for GET /api/health endpoint."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Import app after patching DB so lifespan doesn't fail in CI
from backend.api.main import create_app


@pytest.fixture
async def client():
    """Async test client with DB lifecycle mocked out."""
    with (
        patch("backend.db.database.init_db", new_callable=AsyncMock),
        patch("backend.db.database.close_db", new_callable=AsyncMock),
    ):
        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


@pytest.mark.integration
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.integration
async def test_health_response_has_required_fields(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "terraform" in data


@pytest.mark.integration
async def test_health_status_is_string(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    data = response.json()
    assert isinstance(data["status"], str)
    assert data["status"] in ("ok", "degraded")


@pytest.mark.integration
async def test_health_database_field_is_string(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    data = response.json()
    assert isinstance(data["database"], str)


@pytest.mark.integration
async def test_health_terraform_field_is_string(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    data = response.json()
    assert isinstance(data["terraform"], str)
