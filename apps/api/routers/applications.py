"""API router for job application tracking, status updates, and history."""

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.applications import Application, ApplicationEvent
from packages.core.models.profile import Experience, Profile
from packages.core.services.applications import ApplicationsService
from packages.core.services.followups import draft_follow_up

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


@router.get("/export.csv")
async def export_applications_csv(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Every application as a CSV file (opens in Excel / Google Sheets)."""
    data = await ApplicationsService(db).list_applications(user_id=user.user_id, page=1, page_size=10000)
    buf = io.StringIO()
    fields = [
        "job_title", "company_name", "location", "status", "match_score", "source", "channel",
        "salary_min_lpa", "salary_max_lpa", "created_at", "submitted_at", "follow_up_at", "application_url",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in data["items"]:
        writer.writerow(item)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="applyon-applications.csv"'},
    )


@router.get("/follow-ups")
async def list_follow_ups(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Applications with a follow-up date: due now first, then upcoming."""
    data = await ApplicationsService(db).list_applications(
        user_id=user.user_id, status="submitted,interview", page=1, page_size=500
    )
    now = datetime.now(UTC)
    items = [i for i in data["items"] if i.get("follow_up_at")]
    items.sort(key=lambda i: i["follow_up_at"])
    due = [i for i in items if datetime.fromisoformat(i["follow_up_at"]) <= now]
    upcoming = [i for i in items if datetime.fromisoformat(i["follow_up_at"]) > now]
    return {"due": due, "upcoming": upcoming}


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


class FollowUpDraftRequest(BaseModel):
    tone: Literal["professional", "friendly", "direct"] = "professional"


class FollowUpDateRequest(BaseModel):
    follow_up_at: datetime | None = None


async def _owned_app(db: AsyncSession, user_id: str, application_id: uuid.UUID) -> Application:
    app_obj = (
        await db.execute(select(Application).where(Application.id == application_id, Application.user_id == user_id))
    ).scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Application not found."})
    return app_obj


@router.post("/{application_id}/follow-up/draft")
async def draft_application_follow_up(
    application_id: uuid.UUID,
    body: FollowUpDraftRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Draft a short follow-up email for the user to review and send themselves."""
    detail = await ApplicationsService(db).get_application_detail(user_id=user.user_id, application_id=application_id)
    app_obj = await _owned_app(db, user.user_id, application_id)
    profile = (await db.execute(select(Profile).where(Profile.user_id == user.user_id))).scalar_one_or_none()
    highlight = None
    exp = (await db.execute(select(Experience).where(Experience.user_id == user.user_id))).scalars().first()
    if exp and exp.bullets:
        b = exp.bullets[0]
        highlight = (b.get("text") if isinstance(b, dict) else str(b)) or None
    return await draft_follow_up(
        name=profile.full_name if profile else "",
        job_title=detail["job"]["title"],
        company=detail["job"]["company_name"],
        applied_on=app_obj.submitted_at,
        highlight=highlight,
        tone=body.tone,
    )


@router.post("/{application_id}/follow-up/sent")
async def mark_follow_up_sent(
    application_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record that a follow-up was sent. One more reminder is scheduled a week later, then none."""
    app_obj = await _owned_app(db, user.user_id, application_id)
    sent_before = (
        await db.execute(
            select(ApplicationEvent).where(
                ApplicationEvent.application_id == application_id, ApplicationEvent.type == "follow_up_sent"
            )
        )
    ).scalars().all()
    app_obj.follow_up_at = datetime.now(UTC) + timedelta(days=7) if not sent_before else None
    db.add(
        ApplicationEvent(
            application_id=app_obj.id,
            type="follow_up_sent",
            actor="user",
            payload={"count": len(sent_before) + 1},
            created_at=datetime.now(UTC),
        )
    )
    await db.commit()
    return {
        "id": str(app_obj.id),
        "follow_up_at": app_obj.follow_up_at.isoformat() if app_obj.follow_up_at else None,
    }


@router.patch("/{application_id}/follow-up")
async def set_follow_up_date(
    application_id: uuid.UUID,
    body: FollowUpDateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    app_obj = await _owned_app(db, user.user_id, application_id)
    app_obj.follow_up_at = body.follow_up_at
    await db.commit()
    return {"id": str(app_obj.id), "follow_up_at": body.follow_up_at.isoformat() if body.follow_up_at else None}
