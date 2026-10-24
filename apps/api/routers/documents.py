"""Documents API router: resume tailoring, PDF generation, and cover letters."""

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.matching import CoverLetter, ResumeVersion
from packages.documents.tailor import generate_cover_letter, tailor_resume_for_job

router = APIRouter(tags=["Documents"])


@router.post(
    "/jobs/{job_id}/tailor", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED
)
async def tailor_documents_for_job(
    job_id: uuid.UUID,
    include_cover_letter: bool = True,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate tailored resume and cover letter specifically for a target job."""
    try:
        resume_ver, pdf_path = await tailor_resume_for_job(
            session=session,
            user_id=current_user.id,
            job_id=job_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    cl_data = None
    if include_cover_letter:
        try:
            cl = await generate_cover_letter(
                session=session,
                user_id=current_user.id,
                job_id=job_id,
            )
            cl_data = {
                "id": str(cl.id),
                "text": cl.content_text,
                "pdf_path": cl.pdf_path,
            }
        except Exception:
            pass

    return {
        "status": "ready",
        "resume_version": {
            "id": str(resume_ver.id),
            "version_no": resume_ver.version_no,
            "truth_check_status": resume_ver.truth_check_status,
            "flagged_claims": resume_ver.flagged_claims,
            "content": resume_ver.content_json,
            "pdf_url": f"/v1/resume-versions/{resume_ver.id}/pdf",
        },
        "cover_letter": cl_data,
    }


@router.get("/resume-versions/{resume_id}", response_model=dict[str, Any])
async def get_resume_version_detail(
    resume_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full details of a tailored resume version."""
    stmt = select(ResumeVersion).where(
        ResumeVersion.id == resume_id,
        ResumeVersion.user_id == current_user.id,
    )
    res = await session.execute(stmt)
    ver = res.scalar_one_or_none()
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        )

    return {
        "id": str(ver.id),
        "job_id": str(ver.job_id) if ver.job_id else None,
        "version_no": ver.version_no,
        "truth_check_status": ver.truth_check_status,
        "flagged_claims": ver.flagged_claims,
        "content": ver.content_json,
        "status": ver.status,
        "pdf_url": f"/v1/resume-versions/{ver.id}/pdf",
        "created_at": ver.created_at.isoformat(),
    }


@router.get("/resume-versions/{resume_id}/pdf")
async def download_resume_pdf(
    resume_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Download compiled ATS-friendly PDF document."""
    stmt = select(ResumeVersion).where(
        ResumeVersion.id == resume_id,
        ResumeVersion.user_id == current_user.id,
    )
    res = await session.execute(stmt)
    ver = res.scalar_one_or_none()
    if not ver or not ver.pdf_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume PDF not found")

    file_path = Path(ver.pdf_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF artifact missing on disk"
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )


@router.get("/cover-letters/{cl_id}", response_model=dict[str, Any])
async def get_cover_letter_detail(
    cl_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve details of a generated cover letter."""
    stmt = select(CoverLetter).where(
        CoverLetter.id == cl_id,
        CoverLetter.user_id == str(current_user.id),
    )
    res = await session.execute(stmt)
    cl = res.scalar_one_or_none()
    if not cl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter not found")

    return {
        "id": str(cl.id),
        "job_id": str(cl.job_id),
        "text": cl.content_text,
        "created_at": cl.created_at.isoformat(),
    }
