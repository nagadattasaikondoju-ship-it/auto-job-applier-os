import uuid
from typing import Any

from sqlalchemy import select

from apps.workers.celery_app import celery_app
from packages.core.async_utils import run_async
from packages.core.database import async_session_maker
from packages.core.models.task import Task


async def _async_update_task_progress(
    task_id_str: str,
    progress: int,
    status: str | None = None,
    result_ref: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    async with async_session_maker() as session:
        task_id = uuid.UUID(task_id_str)
        stmt = select(Task).where(Task.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            return None

        task.progress = progress
        if status:
            task.status = status
        if result_ref is not None:
            task.result_ref = result_ref
        if error is not None:
            task.error = error

        await session.commit()
        return task.to_dict()


@celery_app.task(name="tasks.update_progress", queue="maintenance")
def update_task_progress(
    task_id: str,
    progress: int,
    status: str | None = None,
    result_ref: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Synchronous Celery task that calls the async domain update logic via run_async."""
    return run_async(
        _async_update_task_progress(
            task_id_str=task_id,
            progress=progress,
            status=status,
            result_ref=result_ref,
            error=error,
        )
    )
