"""Matches API router: listing match decisions and triggering real-time re-matching."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.jobs import Company, Job
from packages.core.models.matching import JobMatch
from packages.core.services.matching import run_matching_funnel_for_user

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get("", response_model=dict[str, Any])
async def list_matches(
    decision: Literal["apply", "maybe", "skip"] | None = Query(default=None),
    status: Literal["new", "seen", "saved", "dismissed", "queued"] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve all match results for the authenticated user."""
    stmt = (
        select(JobMatch, Job, Company.name.label("company_name"))
        .join(Job, JobMatch.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(JobMatch.user_id == current_user.user_id, Job.is_active.is_(True))  # hide closed postings
    )

    if decision:
        stmt = stmt.where(JobMatch.decision == decision)
    if status:
        stmt = stmt.where(JobMatch.status == status)

    stmt = stmt.order_by(desc(JobMatch.match_score), desc(JobMatch.created_at)).limit(limit)
    res = await session.execute(stmt)

    items = []
    for match, job, company_name in res.all():
        items.append(
            {
                "id": str(match.id),
                "job_id": str(job.id),
                "title": job.title,
                "company": company_name,
                "location": job.location_raw,
                "match_score": match.match_score,
                "decision": match.decision,
                "fit_reasons": match.fit_reasons,
                "gaps": match.gaps,
                "resume_focus": match.resume_focus,
                "risk_flags": match.risk_flags,
                "status": match.status,
                "user_feedback": match.user_feedback,
                "application_url": job.application_url,
                "created_at": match.created_at.isoformat(),
            }
        )

    return {"items": items, "count": len(items)}


@router.post("/refresh", response_model=dict[str, Any])
async def refresh_matches(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger the multi-stage matching funnel to discover new matching jobs immediately."""
    new_matches = await run_matching_funnel_for_user(
        session=session,
        user_id=current_user.user_id,
    )
    return {
        "status": "completed",
        "new_matches_count": len(new_matches),
        "matches": [
            {
                "id": str(m.id),
                "job_id": str(m.job_id),
                "score": m.match_score,
                "decision": m.decision,
            }
            for m in new_matches
        ],
    }
