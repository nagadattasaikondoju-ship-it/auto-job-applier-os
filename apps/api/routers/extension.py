"""API router for Chrome Extension (MV3) fill-plan generation and proof-of-submission recording."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.applications import Application
from packages.core.models.jobs import Job
from packages.core.services.applications import ApplicationsService
from packages.jobs_sources.detector import detect_ats
from packages.jobs_sources.manual import ManualUrlImporter

router = APIRouter(prefix="/extension", tags=["Chrome Extension"])


class MarkSubmittedRequest(BaseModel):
    application_id: uuid.UUID
    proof_url: str | None = None
    proof_text: str | None = None
    submission_metadata: dict[str, Any] = {}


@router.get("/fill-plan")
async def get_fill_plan(
    url: str = Query(..., description="Job application page URL"),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Provide structured autofill plan with resolved answers, tailored resume link, and confidence flags."""
    # 1. Detect ATS vendor
    detected_ats = detect_ats(url)

    # 2. Look up existing job by application_url or import
    stmt = select(Job).where(Job.application_url == url)
    res = await db.execute(stmt)
    job = res.scalars().first()

    if not job:
        # Auto-import job
        importer = ManualUrlImporter(db)
        job = await importer.import_from_url(url=url, user_id=user.user_id)

    # 3. Create or get application & resolved plan
    svc = ApplicationsService(db)
    app_obj, plan = await svc.create_or_get_application(
        user_id=user.user_id,
        job_id=job.id,
        channel="extension",
    )

    company_title = getattr(job, "company_name", None)
    if not company_title and getattr(job, "company", None):
        company_title = job.company.name

    return {
        "application_id": str(app_obj.id),
        "job_id": str(job.id),
        "company_name": company_title or "Company",
        "job_title": job.title,
        "ats_type": detected_ats,
        "can_auto_submit": plan.can_auto_submit,
        "unresolved_count": plan.unresolved_count,
        "fields": [f.model_dump() for f in plan.fields],
        "resume_download_url": f"/v1/resume-versions/{app_obj.resume_version_id}/pdf"
        if app_obj.resume_version_id
        else None,
    }


@router.post("/mark-submitted")
async def mark_submitted(
    body: MarkSubmittedRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record proof of submission detected by Chrome extension content script."""
    svc = ApplicationsService(db)

    # Verify application ownership
    stmt = select(Application).where(
        Application.id == body.application_id, Application.user_id == user.user_id
    )
    res = await db.execute(stmt)
    app_obj = res.scalars().first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")

    notes_str = f"Submitted via Extension on {body.proof_url or app_obj.application_url}"
    updated_app = await svc.update_status(
        user_id=user.user_id,
        application_id=body.application_id,
        new_status="submitted",
        actor="extension",
        notes=notes_str,
    )

    return {
        "id": str(updated_app.id),
        "status": updated_app.status,
        "submitted_at": updated_app.submitted_at.isoformat() if updated_app.submitted_at else None,
        "success": True,
    }
