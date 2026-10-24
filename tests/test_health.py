from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "env" in data


@pytest.mark.asyncio
async def test_health_ready_all_connected(client: AsyncClient) -> None:
    with (
        patch("apps.api.routers.health.check_db_health", new_callable=AsyncMock) as mock_db,
        patch("apps.api.routers.health.check_redis_health", new_callable=AsyncMock) as mock_redis,
    ):
        mock_db.return_value = True
        mock_redis.return_value = True

        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
        assert data["redis"] == "connected"


@pytest.mark.asyncio
async def test_health_ready_degraded(client: AsyncClient) -> None:
    with (
        patch("apps.api.routers.health.check_db_health", new_callable=AsyncMock) as mock_db,
        patch("apps.api.routers.health.check_redis_health", new_callable=AsyncMock) as mock_redis,
    ):
        mock_db.return_value = False
        mock_redis.return_value = True

        response = await client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
