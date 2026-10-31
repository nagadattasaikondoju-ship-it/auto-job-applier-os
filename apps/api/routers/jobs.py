"""Jobs API router: feed, detail, manual import, and user feedback."""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.jobs import Company, Job
from packages.core.models.matching import JobMatch
from packages.core.services.apply_mode import apply_mode
from packages.core.services.jobs import get_jobs_feed, ingest_normalized_job
from packages.jobs_sources.manual import ManualUrlImporter

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobImportRequest(BaseModel):
    url: str
    optional_text: str = ""


class JobFeedbackRequest(BaseModel):
    feedback: Literal["good", "bad", "dismissed"]
    reason: str | None = None


@router.get("", response_model=dict[str, Any])
async def list_jobs_feed(
    cursor: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    min_match_score: int | None = Query(default=None, ge=0, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve keyset-paginated jobs feed with match calculations for the current user."""
    jobs = await get_jobs_feed(
        session=session,
        user_id=current_user.user_id,
        cursor=cursor,
        limit=limit,
        min_match_score=min_match_score,
    )
    next_cursor = None
    if jobs:
        last_job_posted = jobs[-1].get("posted_at")
        if last_job_posted:
            next_cursor = last_job_posted

    return {
        "items": jobs,
        "next_cursor": next_cursor,
        "count": len(jobs),
    }


@router.post("/discover", response_model=dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def discover_jobs_now(
    background: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Search job sources for this user's roles and cities now, then re-run matching (in the background)."""
    from packages.core.services.discovery import discover_for_user

    background.add_task(discover_for_user, current_user.user_id)
    return {"status": "started", "message": "Searching job sources. New matches appear in a minute or two."}


@router.get("/{job_id}", response_model=dict[str, Any])
async def get_job_detail(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get complete job details and fit analysis."""
    stmt = (
        select(Job, Company.name.label("company_name"))
        .join(Company, Job.company_id == Company.id)
        .where(Job.id == job_id)
    )
    res = await session.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    job, company_name = row

    # Fetch user match if exists
    m_stmt = select(JobMatch).where(
        JobMatch.job_id == job_id,
        JobMatch.user_id == current_user.user_id,
    )
    m_res = await session.execute(m_stmt)
    match = m_res.scalar_one_or_none()

    return {
        "id": str(job.id),
        "title": job.title,
        "company": company_name,
        "location": job.location_raw,
        "locations": job.locations,
        "remote_mode": job.remote_mode,
        "employment_type": job.employment_type,
        "description_html": job.description_html,
        "description_text": job.description_text,
        "salary_min_lpa": job.salary_min_lpa,
        "salary_max_lpa": job.salary_max_lpa,
        "experience_min": job.experience_min,
        "experience_max": job.experience_max,
        "required_skills": job.required_skills,
        "application_url": job.application_url,
        "ats_type": job.ats_type,
        "apply_mode": apply_mode(job.ats_type, job.application_url),
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "match": (
            {
                "score": match.match_score,
                "decision": match.decision,
                "fit_reasons": match.fit_reasons,
                "gaps": match.gaps,
                "resume_focus": match.resume_focus,
                "risk_flags": match.risk_flags,
                "user_feedback": match.user_feedback,
                "status": match.status,
            }
            if match
            else None
        ),
    }


@router.post("/import", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def import_job_from_url(
    req: JobImportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Import and normalize any job URL (Greenhouse, Lever, Ashby, or career page)."""
    importer = ManualUrlImporter()
    normalized = await importer.import_url(url=req.url, optional_text=req.optional_text)

    job, is_new = await ingest_normalized_job(session=session, job_in=normalized)
    await session.commit()

    return {
        "job_id": str(job.id),
        "title": job.title,
        "company": normalized.company_name,
        "ats_type": job.ats_type,
        "is_new": is_new,
        "application_url": job.application_url,
    }


@router.post("/{job_id}/feedback", response_model=dict[str, Any])
async def submit_job_feedback(
    job_id: uuid.UUID,
    req: JobFeedbackRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record user thumbs up/down or dismiss decision on a matched job."""
    stmt = select(JobMatch).where(
        JobMatch.job_id == job_id,
        JobMatch.user_id == current_user.user_id,
    )
    res = await session.execute(stmt)
    match = res.scalar_one_or_none()

    if not match:
        # Create match entry to record dismissal
        match = JobMatch(
            user_id=current_user.user_id,
            job_id=job_id,
            filter_passed=True,
            match_score=50,
            decision="skip",
            status="dismissed" if req.feedback == "dismissed" else "seen",
            user_feedback=req.feedback,
        )
        session.add(match)
    else:
        match.user_feedback = req.feedback
        if req.feedback == "dismissed":
            match.status = "dismissed"

    await session.commit()
    return {"status": "ok", "job_id": str(job_id), "feedback": req.feedback}


@router.post("/{job_id}/save", response_model=dict[str, Any])
async def toggle_saved_job(
    job_id: uuid.UUID,
    saved: bool = True,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Save a job for later (or unsave it)."""
    match = (
        await session.execute(
            select(JobMatch).where(JobMatch.job_id == job_id, JobMatch.user_id == current_user.user_id)
        )
    ).scalar_one_or_none()
    if not match:
        match = JobMatch(
            user_id=current_user.user_id,
            job_id=job_id,
            filter_passed=True,
            match_score=0,
            decision="maybe",
            status="saved" if saved else "seen",
        )
        session.add(match)
    else:
        match.status = "saved" if saved else "seen"
    await session.commit()
    return {"job_id": str(job_id), "saved": saved}
