import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from apps.api.deps.db import get_db
from apps.api.main import app
from packages.core.models.task import Task


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient) -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db

    non_existent_id = uuid.uuid4()
    response = await client.get(
        f"/v1/tasks/{non_existent_id}",
        headers={"X-Dev-User-Id": "test-user"},
    )
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "TASK_NOT_FOUND"

    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_task_success(client: AsyncClient) -> None:
    task_id = uuid.uuid4()
    mock_task = Task(
        id=task_id,
        kind="tailor_resume",
        user_id="test-user",
        status="running",
        progress=45,
        result_ref={"resume_id": "res-123"},
        error=None,
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_task
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db

    response = await client.get(
        f"/v1/tasks/{task_id}",
        headers={"X-Dev-User-Id": "test-user"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(task_id)
    assert data["kind"] == "tailor_resume"
    assert data["status"] == "running"
    assert data["progress"] == 45
    assert data["result_ref"] == {"resume_id": "res-123"}

    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_task_forbidden_for_other_user(client: AsyncClient) -> None:
    task_id = uuid.uuid4()
    mock_task = Task(
        id=task_id,
        kind="assisted_apply",
        user_id="owner-user-999",
        status="queued",
        progress=0,
        result_ref=None,
        error=None,
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_task
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db

    response = await client.get(
        f"/v1/tasks/{task_id}",
        headers={"X-Dev-User-Id": "intruder-user-111"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"

    app.dependency_overrides.pop(get_db, None)
