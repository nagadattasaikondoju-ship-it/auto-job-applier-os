import os

# Before the app is imported: test settings (dev logins allowed, no connection pooling across event loops)
os.environ["APP_ENV"] = "test"

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Test client for API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_auth_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="test-user-123",
        email="test@applyon.in",
        role="authenticated",
        claims={"sub": "test-user-123", "email": "test@applyon.in"},
    )


@pytest.fixture
def authenticated_client(mock_auth_user: AuthenticatedUser) -> AsyncGenerator[AsyncClient, None]:
    """Test client with mocked authentication dependency."""
    app.dependency_overrides[get_current_user] = lambda: mock_auth_user
    transport = ASGITransport(app=app)

    async def _get_client() -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    yield _get_client()
    app.dependency_overrides.pop(get_current_user, None)
