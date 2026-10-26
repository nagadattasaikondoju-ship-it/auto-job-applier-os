"""Auto-apply (Autopilot) controls: readiness, start/pause/resume, run now, activity and retries."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.database import async_session_maker
from packages.core.models.applications import Application, ApplicationEvent, Campaign
from packages.core.models.jobs import Company, Job
from packages.core.models.preferences import JobPreference
from packages.core.services.autopilot import DEFAULT_HYBRID_THRESHOLD, AutopilotService, today_start
from packages.core.services.discovery import discover_for_user
from packages.core.services.matching import run_matching_funnel_for_user

logger = logging.getLogger("applyon.autopilot")

router = APIRouter(prefix="/autopilot", tags=["Autopilot"])


class StartRequest(BaseModel):
    mode: Literal["review", "hybrid"] = "review"
    daily_limit: int = Field(default=10, ge=1, le=60)
    min_match_score: int | None = Field(default=None, ge=0, le=100)
    hybrid_threshold: int = Field(default=DEFAULT_HYBRID_THRESHOLD, ge=80, le=100)


def _campaign_dict(c: Campaign) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "mode": c.mode,
        "status": c.status,
        "daily_limit": c.daily_limit,
        "min_match_score": (c.schedule or {}).get("min_match_score"),
        "hybrid_threshold": (c.schedule or {}).get("hybrid_threshold", DEFAULT_HYBRID_THRESHOLD),
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "paused_reason": (c.stats or {}).get("paused_reason"),
        "preparing": bool((c.stats or {}).get("preparing")),
        "last_batch": (c.stats or {}).get("last_batch"),
    }


@router.get("")
async def get_autopilot(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Campaign state, readiness for each mode, today's counts and recent activity."""
    campaign = await AutopilotService.get_active_campaign(db, user.user_id)
    mode = campaign.mode if campaign else "review"

    counts: dict[str, int] = {}
    for st, n in (
        await db.execute(
            select(Application.status, func.count(Application.id))
            .where(Application.user_id == user.user_id, Application.created_at >= today_start())
            .group_by(Application.status)
        )
    ).all():
        counts[st] = int(n)

    recent_rows = (
        await db.execute(
            select(Application, Job.title, Company.name)
            .join(Job, Application.job_id == Job.id)
            .join(Company, Job.company_id == Company.id)
            .where(Application.user_id == user.user_id, Application.channel == "auto")
            .order_by(desc(Application.updated_at))
            .limit(25)
        )
    ).all()

    return {
        "campaign": _campaign_dict(campaign) if campaign else None,
        "readiness": {
            "review": await AutopilotService.readiness(db, user.user_id, "review"),
            "hybrid": await AutopilotService.readiness(db, user.user_id, "hybrid"),
        },
        "today": {
            "prepared": await AutopilotService.prepared_today(db, campaign) if campaign else 0,
            "limit": campaign.daily_limit if campaign else 0,
            "by_status": counts,
        },
        "activity": [
            {
                "id": str(a.id),
                "job_id": str(a.job_id),
                "job_title": title,
                "company_name": company,
                "status": a.status,
                "failure_reason": a.failure_reason,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a, title, company in recent_rows
        ],
        "current_mode": mode,
    }


@router.post("/start")
async def start_autopilot(
    body: StartRequest,
    background: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    ready = await AutopilotService.readiness(db, user.user_id, body.mode)
    if not ready["can_start"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "AUTOPILOT_NOT_READY", "message": ready["blockers"][0], "details": ready["blockers"]},
        )

    pref = (await db.execute(select(JobPreference).where(JobPreference.user_id == user.user_id))).scalar_one()
    daily_limit = min(body.daily_limit, ready["plan_daily_limit"])
    schedule = {
        "min_match_score": body.min_match_score if body.min_match_score is not None else pref.min_match_score,
        "hybrid_threshold": body.hybrid_threshold,
    }

    campaign = await AutopilotService.get_active_campaign(db, user.user_id)
    if campaign is None:
        campaign = Campaign(
            user_id=user.user_id,
            name="Auto-apply",
            preferences_snapshot={"target_roles": pref.target_roles, "locations": pref.locations},
            mode=body.mode,
            status="active",
            daily_limit=daily_limit,
            schedule=schedule,
            started_at=datetime.now(UTC),
            stats={},
        )
        db.add(campaign)
    else:
        campaign.mode = body.mode
        campaign.status = "active"
        campaign.daily_limit = daily_limit
        campaign.schedule = schedule
        campaign.stats = {k: v for k, v in (campaign.stats or {}).items() if k != "paused_reason"}
    pref.auto_submit_enabled = body.mode == "hybrid"
    pref.daily_application_limit = daily_limit
    campaign.stats = {**(campaign.stats or {}), "preparing": True}
    await db.commit()

    # Matching and tailoring can take a minute (AI calls), so the first batch runs after we reply;
    # the auto-apply page shows "preparing" until it finishes.
    background.add_task(_prepare_first_batch, user.user_id, min(3, daily_limit))
    return {
        "campaign": _campaign_dict(campaign),
        "first_batch": {"prepared": 0, "items": [], "stopped_reason": None, "preparing": True},
    }


async def _prepare_first_batch(user_id: str, max_items: int) -> None:
    """Match against jobs we already have, prepare the first applications, then look for more jobs."""
    batch: dict[str, Any] = {"prepared": 0, "stopped_reason": None}
    async with async_session_maker() as db:
        try:
            await run_matching_funnel_for_user(db, user_id)
            batch = await AutopilotService.run_batch(db, user_id, max_items=max_items)
        except Exception as e:  # never leave the campaign stuck in "preparing"
            logger.warning("First batch failed for %s: %s", user_id, e)
            await db.rollback()
            batch = {"prepared": 0, "stopped_reason": "We couldn't prepare applications just now. We'll keep trying."}
        campaign = await AutopilotService.get_active_campaign(db, user_id)
        if campaign:
            campaign.stats = {
                **(campaign.stats or {}),
                "preparing": False,
                "last_batch": {
                    "prepared": batch.get("prepared", 0),
                    "stopped_reason": batch.get("stopped_reason"),
                    "at": datetime.now(UTC).isoformat(),
                },
            }
            await db.commit()
    try:
        await discover_for_user(user_id)
    except Exception as e:
        logger.warning("Discovery after start failed for %s: %s", user_id, e)


async def _set_status(db: AsyncSession, user_id: str, new_status: str) -> dict[str, Any]:
    campaign = await AutopilotService.get_active_campaign(db, user_id)
    if not campaign:
        raise HTTPException(status_code=404, detail={"code": "NO_CAMPAIGN", "message": "Auto-apply isn't set up yet."})
    campaign.status = new_status
    if new_status == "active":
        campaign.stats = {k: v for k, v in (campaign.stats or {}).items() if k != "paused_reason"}
    await db.commit()
    return {"campaign": _campaign_dict(campaign)}


@router.post("/pause")
async def pause_autopilot(
    user: AuthenticatedUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    return await _set_status(db, user.user_id, "paused")


@router.post("/resume")
async def resume_autopilot(
    user: AuthenticatedUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    campaign = await AutopilotService.get_active_campaign(db, user.user_id)
    if campaign:
        ready = await AutopilotService.readiness(db, user.user_id, campaign.mode)
        if not ready["can_start"]:
            raise HTTPException(
                status_code=409,
                detail={"code": "AUTOPILOT_NOT_READY", "message": ready["blockers"][0], "details": ready["blockers"]},
            )
    return await _set_status(db, user.user_id, "active")


@router.post("/run-now")
async def run_autopilot_now(
    user: AuthenticatedUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Prepare up to 5 applications immediately instead of waiting for the next scheduled run."""
    return await AutopilotService.run_batch(db, user.user_id, max_items=5)


@router.post("/retry/{application_id}")
async def retry_application(
    application_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Send a failed or blocked application back to the review queue."""
    app_obj = (
        await db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user.user_id)
        )
    ).scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Application not found."})
    if app_obj.status not in ("failed", "needs_user_action"):
        raise HTTPException(
            status_code=409, detail={"code": "NOT_RETRYABLE", "message": "Only failed or blocked applications can be retried."}
        )
    old = app_obj.status
    app_obj.status = "ready_for_review"
    app_obj.failure_reason = None
    db.add(
        ApplicationEvent(
            application_id=app_obj.id,
            type="status_changed",
            actor="user",
            payload={"from": old, "to": "ready_for_review", "notes": "Retried"},
            created_at=datetime.now(UTC),
        )
    )
    await db.commit()
    return {"id": str(app_obj.id), "status": app_obj.status}
