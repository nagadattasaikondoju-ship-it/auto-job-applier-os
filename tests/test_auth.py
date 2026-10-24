import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_me_endpoint_dev_user(client: AsyncClient) -> None:
    # Test dev bypass via header
    response = await client.get("/v1/me", headers={"X-Dev-User-Id": "custom-dev-user"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "custom-dev-user"
    assert data["email"] == "custom-dev-user@example.com"


@pytest.mark.asyncio
async def test_auth_error_format(client: AsyncClient) -> None:
    # When sending an invalid bearer token
    response = await client.get(
        "/v1/me",
        headers={"Authorization": "Bearer totally-invalid-token-here"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_TOKEN"
    assert "message" in data["error"]
