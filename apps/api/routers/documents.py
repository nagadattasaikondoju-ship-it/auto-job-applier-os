"""Documents API router: resume tailoring, resume versions, PDF/DOCX export and cover letters."""

import re
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.ai.client import AIUnavailableError
from packages.core.models.jobs import Company, Job
from packages.core.models.matching import CoverLetter, ResumeVersion
from packages.core.models.profile import ProfileVersion
from packages.core.services.ats import analyze_resume
from packages.documents.export import (
    build_resume_document,
    cover_letter_pdf_bytes,
    document_text,
    resume_docx_bytes,
    resume_pdf_bytes,
)
from packages.documents.renderer import generate_resume_filename
from packages.documents.tailor import generate_cover_letter, tailor_resume_for_job

router = APIRouter(tags=["Documents"])

Tone = Literal["professional", "friendly", "direct"]


def _ai_down() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "AI_UNAVAILABLE",
            "message": "The AI service isn't responding right now, so we couldn't write this. Please try again in a minute.",
        },
    )


def _version_dict(ver: ResumeVersion) -> dict[str, Any]:
    return {
        "id": str(ver.id),
        "job_id": str(ver.job_id) if ver.job_id else None,
        "version_no": ver.version_no,
        "truth_check_status": ver.truth_check_status,
        "flagged_claims": ver.flagged_claims,
        "content": ver.content_json,
        "status": ver.status,
        "pdf_url": f"/v1/resume-versions/{ver.id}/pdf",
        "docx_url": f"/v1/resume-versions/{ver.id}/docx",
        "created_at": ver.created_at.isoformat() if ver.created_at else None,
    }


async def _job_jd(session: AsyncSession, job_id: uuid.UUID | None) -> str | None:
    if not job_id:
        return None
    job = (await session.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if not job:
        return None
    text = f"{job.title}\n{job.description_text or ''}\n{' '.join(job.required_skills or [])}"
    # The hiring company's own name isn't a keyword the candidate is missing
    company = (await session.execute(select(Company.name).where(Company.id == job.company_id))).scalar_one_or_none()
    for name in {company or "", *(company or "").split()}:
        if len(name) > 2:
            text = re.sub(rf"\b{re.escape(name)}\b", " ", text, flags=re.I)
    return text


async def _owned_version(session: AsyncSession, user_id: str, resume_id: uuid.UUID) -> ResumeVersion:
    ver = (
        await session.execute(
            select(ResumeVersion).where(ResumeVersion.id == resume_id, ResumeVersion.user_id == user_id)
        )
    ).scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")
    return ver


async def _printable(session: AsyncSession, ver: ResumeVersion) -> dict[str, Any]:
    snap = (
        await session.execute(select(ProfileVersion).where(ProfileVersion.id == ver.profile_version_id))
    ).scalar_one_or_none()
    return build_resume_document(snap.snapshot_json if snap else {}, ver.content_json)


@router.post(
    "/jobs/{job_id}/tailor", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED
)
async def tailor_documents_for_job(
    job_id: uuid.UUID,
    include_cover_letter: bool = True,
    tone: Tone = "professional",
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate tailored resume and cover letter specifically for a target job."""
    try:
        resume_ver, _ = await tailor_resume_for_job(
            session=session,
            user_id=current_user.user_id,
            job_id=job_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except AIUnavailableError as e:
        raise _ai_down() from e

    cl_data = None
    if include_cover_letter:
        try:
            cl = await generate_cover_letter(
                session=session,
                user_id=current_user.user_id,
                job_id=job_id,
                tone=tone,
            )
            cl_data = {"id": str(cl.id), "text": cl.content_text, "pdf_url": f"/v1/cover-letters/{cl.id}/pdf"}
        except Exception:
            cl_data = None

    data = _version_dict(resume_ver)
    data["ats"] = analyze_resume(
        document_text(await _printable(session, resume_ver)), jd_text=await _job_jd(session, job_id)
    )
    return {"status": "ready", "resume_version": data, "cover_letter": cl_data}


@router.post("/jobs/{job_id}/cover-letter", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def regenerate_cover_letter(
    job_id: uuid.UUID,
    tone: Tone = "professional",
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Write a new cover letter for a job in the chosen tone."""
    try:
        cl = await generate_cover_letter(session=session, user_id=current_user.user_id, job_id=job_id, tone=tone)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except AIUnavailableError as e:
        raise _ai_down() from e
    return {"id": str(cl.id), "text": cl.content_text, "pdf_url": f"/v1/cover-letters/{cl.id}/pdf"}


@router.get("/jobs/{job_id}/documents", response_model=dict[str, Any])
async def get_job_documents(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Latest tailored resume and cover letter for a job, so the tailor page can reopen them."""
    ver = (
        await session.execute(
            select(ResumeVersion)
            .where(ResumeVersion.user_id == current_user.user_id, ResumeVersion.job_id == job_id)
            .order_by(ResumeVersion.version_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    cl = (
        await session.execute(
            select(CoverLetter)
            .where(CoverLetter.user_id == current_user.user_id, CoverLetter.job_id == job_id)
            .order_by(CoverLetter.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    resume_data = None
    if ver:
        resume_data = _version_dict(ver)
        resume_data["ats"] = analyze_resume(
            document_text(await _printable(session, ver)), jd_text=await _job_jd(session, job_id)
        )
    return {
        "resume_version": resume_data,
        "cover_letter": (
            {"id": str(cl.id), "text": cl.content_text, "pdf_url": f"/v1/cover-letters/{cl.id}/pdf"} if cl else None
        ),
    }


@router.get("/resume-versions", response_model=dict[str, Any])
async def list_resume_versions(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """All resume versions: ATS-optimized master versions and job-tailored versions."""
    rows = (
        await session.execute(
            select(ResumeVersion, Job.title, Company.name)
            .outerjoin(Job, ResumeVersion.job_id == Job.id)
            .outerjoin(Company, Job.company_id == Company.id)
            .where(ResumeVersion.user_id == current_user.user_id)
            .order_by(ResumeVersion.created_at.desc())
            .limit(limit)
        )
    ).all()
    items = []
    for ver, job_title, company in rows:
        d = _version_dict(ver)
        d.pop("content", None)
        content = ver.content_json or {}
        # Job-optimized versions made from a pasted job description carry the job in their content
        d["job_title"] = job_title or content.get("job_title")
        d["company"] = company or content.get("company")
        d["kind"] = "tailored" if ver.job_id or content.get("source") == "ats_job_optimizer" else "optimized"
        items.append(d)
    return {"items": items}


@router.get("/resume-versions/{resume_id}", response_model=dict[str, Any])
async def get_resume_version_detail(
    resume_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full details of a resume version."""
    return _version_dict(await _owned_version(session, current_user.user_id, resume_id))


@router.get("/resume-versions/{resume_id}/pdf")
async def download_resume_pdf(
    resume_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """ATS-friendly PDF, rendered from the stored version (no dependency on local disk)."""
    ver = await _owned_version(session, current_user.user_id, resume_id)
    doc = await _printable(session, ver)
    filename = generate_resume_filename(doc["name"])
    return Response(
        content=resume_pdf_bytes(doc),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/resume-versions/{resume_id}/docx")
async def download_resume_docx(
    resume_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Editable DOCX version of a resume."""
    ver = await _owned_version(session, current_user.user_id, resume_id)
    doc = await _printable(session, ver)
    filename = generate_resume_filename(doc["name"]).replace(".pdf", ".docx")
    return Response(
        content=resume_docx_bytes(doc),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cover-letters/{cl_id}", response_model=dict[str, Any])
async def get_cover_letter_detail(
    cl_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve details of a generated cover letter."""
    cl = (
        await session.execute(
            select(CoverLetter).where(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.user_id)
        )
    ).scalar_one_or_none()
    if not cl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter not found")
    return {
        "id": str(cl.id),
        "job_id": str(cl.job_id),
        "text": cl.content_text,
        "pdf_url": f"/v1/cover-letters/{cl.id}/pdf",
        "created_at": cl.created_at.isoformat(),
    }


@router.get("/cover-letters/{cl_id}/pdf")
async def download_cover_letter_pdf(
    cl_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    cl = (
        await session.execute(
            select(CoverLetter).where(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.user_id)
        )
    ).scalar_one_or_none()
    if not cl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter not found")
    snap = (
        await session.execute(select(ProfileVersion).where(ProfileVersion.id == cl.profile_version_id))
    ).scalar_one_or_none()
    p = (snap.snapshot_json if snap else {}).get("profile", {})
    pdf = cover_letter_pdf_bytes(
        p.get("full_name") or "Candidate",
        [x for x in [p.get("email"), p.get("phone"), p.get("city")] if x],
        cl.content_text,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Cover_Letter.pdf"'},
    )
