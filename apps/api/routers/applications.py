"""API router for job application tracking, status updates, and history."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.services.applications import ApplicationsService

router = APIRouter(prefix="/applications", tags=["Applications"])


class CreateApplicationRequest(BaseModel):
    job_id: uuid.UUID
    channel: str = "extension"
    campaign_id: uuid.UUID | None = None


class UpdateStatusRequest(BaseModel):
    status: str
    notes: str | None = None
    failure_reason: str | None = None


@router.post("", status_code=201)
async def create_application(
    body: CreateApplicationRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start tracking or prepare a new job application."""
    svc = ApplicationsService(db)
    app_obj, plan = await svc.create_or_get_application(
        user_id=user.user_id,
        job_id=body.job_id,
        channel=body.channel,
        campaign_id=body.campaign_id,
    )
    return {
        "id": str(app_obj.id),
        "status": app_obj.status,
        "channel": app_obj.channel,
        "application_url": app_obj.application_url,
        "unresolved_count": plan.unresolved_count,
        "can_auto_submit": plan.can_auto_submit,
    }


@router.get("")
async def list_applications(
    status: str | None = Query(None, description="Filter by application status"),
    search: str | None = Query(None, description="Search by title or company"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List applications for tracker with pagination and search."""
    svc = ApplicationsService(db)
    return await svc.list_applications(
        user_id=user.user_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{application_id}")
async def get_application(
    application_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get full application detail including timeline and resolved form."""
    svc = ApplicationsService(db)
    return await svc.get_application_detail(user_id=user.user_id, application_id=application_id)


@router.patch("/{application_id}/status")
async def update_application_status(
    application_id: uuid.UUID,
    body: UpdateStatusRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Transition application status (e.g. submitted, interviewing, rejected)."""
    svc = ApplicationsService(db)
    app_obj = await svc.update_status(
        user_id=user.user_id,
        application_id=application_id,
        new_status=body.status,
        actor="user",
        notes=body.notes,
        failure_reason=body.failure_reason,
    )
    return {"id": str(app_obj.id), "status": app_obj.status}


@router.delete("/{application_id}", status_code=204)
async def withdraw_application(
    application_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Withdraw or archive an application."""
    svc = ApplicationsService(db)
    await svc.update_status(
        user_id=user.user_id,
        application_id=application_id,
        new_status="withdrawn",
        actor="user",
        notes="Withdrawn by candidate",
    )
