"""API router for candidate review queue, approvals, and inline answer edits."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.services.applications import ApplicationsService

router = APIRouter(prefix="/review-queue", tags=["Review Queue"])


class EditAnswerRequest(BaseModel):
    field_id: str
    new_value: Any
    save_to_answer_bank: bool = False


@router.get("")
async def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve all pending applications awaiting candidate approval or input."""
    svc = ApplicationsService(db)
    # Fetch ready_for_review and needs_user_action applications
    res1 = await svc.list_applications(
        user_id=user.user_id, status="ready_for_review", page=page, page_size=page_size
    )
    res2 = await svc.list_applications(
        user_id=user.user_id, status="needs_user_action", page=page, page_size=page_size
    )

    combined_items = res1["items"] + res2["items"]
    # Enhance each item with detail/fields
    detailed_items = []
    for item in combined_items:
        app_detail = await svc.get_application_detail(
            user_id=user.user_id, application_id=uuid.UUID(item["id"])
        )
        detailed_items.append(app_detail)

    return {
        "items": detailed_items,
        "total": res1["total"] + res2["total"],
        "page": page,
        "page_size": page_size,
    }


@router.post("/applications/{application_id}/approve")
async def approve_application(
    application_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Candidate approves the application for submission."""
    svc = ApplicationsService(db)
    app_obj = await svc.update_status(
        user_id=user.user_id,
        application_id=application_id,
        new_status="approved",
        actor="user",
        notes="Candidate approved application in review queue",
    )
    return {"id": str(app_obj.id), "status": app_obj.status, "approved": True}


@router.post("/applications/{application_id}/reject")
async def reject_application(
    application_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Candidate dismisses the application from the review queue."""
    svc = ApplicationsService(db)
    app_obj = await svc.update_status(
        user_id=user.user_id,
        application_id=application_id,
        new_status="withdrawn",
        actor="user",
        notes="Candidate rejected from review queue",
    )
    return {"id": str(app_obj.id), "status": app_obj.status, "rejected": True}


@router.post("/applications/{application_id}/edit-answer")
async def edit_application_answer(
    application_id: uuid.UUID,
    body: EditAnswerRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Edit answer inline, optionally storing in AnswerBank for future applications."""
    svc = ApplicationsService(db)
    updated_plan = await svc.edit_answer(
        user_id=user.user_id,
        application_id=application_id,
        field_id=body.field_id,
        new_value=body.new_value,
        save_to_answer_bank=body.save_to_answer_bank,
    )
    return {"updated": True, "plan": updated_plan}
