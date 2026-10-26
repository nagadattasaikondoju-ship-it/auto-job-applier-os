"""Resume tailoring, cover letter generation, and truth verification service."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai.client import gemini_client
from packages.ai.schemas import CoverLetterOutput, ScreeningAnswersOutput, TailoredResumeOutput
from packages.ai.truth_checker import verify_resume_truthfulness
from packages.core.config import settings
from packages.core.models.jobs import Company, Job
from packages.core.models.matching import CoverLetter, ResumeVersion
from packages.core.models.preferences import JobPreference
from packages.core.models.profile import Profile, ProfileVersion
from packages.core.services.profile import create_profile_snapshot_for_user
from packages.documents.ats_optimizer import optimize_resume_for_job
from packages.documents.export import (
    build_resume_document,
    cover_letter_pdf_bytes,
    resume_pdf_bytes,
)
from packages.documents.renderer import generate_resume_filename

TONE_GUIDE = {
    "professional": "Professional and warm. Clear, confident sentences.",
    "friendly": "Friendly and conversational, still polished. Shows genuine enthusiasm.",
    "direct": "Direct and concise. Short paragraphs, lead with impact, no filler.",
}

logger = logging.getLogger("applyon.documents.tailor")



async def tailor_resume_for_job(
    session: AsyncSession,
    user_id: str,
    job_id: uuid.UUID,
) -> tuple[ResumeVersion, str]:
    """Tailor candidate resume specifically for a job with deterministic truth verification.

    Returns (ResumeVersion, pdf_file_path).
    """
    # 1. Fetch user master profile & active snapshot
    prof_stmt = select(Profile).where(Profile.user_id == user_id)
    profile = (await session.execute(prof_stmt)).scalar_one_or_none()
    if not profile:
        raise ValueError(f"Profile not found for user {user_id}")

    snap_stmt = (
        select(ProfileVersion)
        .where(ProfileVersion.user_id == str(user_id))
        .order_by(ProfileVersion.version_no.desc())
        .limit(1)
    )
    profile_version = (await session.execute(snap_stmt)).scalar_one_or_none()
    if not profile_version:
        profile_version = await create_profile_snapshot_for_user(session=session, user_id=str(user_id))

    snapshot_json = profile_version.snapshot_json

    # 2. Fetch Job and Match details
    job_stmt = select(Job).where(Job.id == job_id)
    job = (await session.execute(job_stmt)).scalar_one_or_none()
    if not job:
        raise ValueError(f"Job not found {job_id}")

    company_name = (
        await session.execute(select(Company.name).where(Company.id == job.company_id))
    ).scalar_one_or_none() or ""
    pref = (await session.execute(select(JobPreference).where(JobPreference.user_id == user_id))).scalar_one_or_none()

    # 3. Job-targeted ATS resume (AI rewrite + deterministic guards; rules-only when AI is down)
    result = await optimize_resume_for_job(
        snapshot_json,
        f"{job.title}\n{job.description_text or ''}\n{' '.join(job.required_skills or [])}",
        job_title=job.title,
        company=company_name,
        seniority=pref.seniority if pref else "",
        target_role=", ".join((pref.target_roles or [])[:3]) if pref else "",
        location=", ".join(x for x in [profile.city, profile.country] if x),
    )
    tailored = TailoredResumeOutput(**result["content"])

    # 4. Deterministic truth check
    truth_result = verify_resume_truthfulness(
        tailored_resume=tailored,
        profile_snapshot=snapshot_json,
    )

    # 5. Render an ATS-friendly PDF (single column, real text)
    pdf_bytes = resume_pdf_bytes(build_resume_document(snapshot_json, tailored.model_dump()))

    # 6. Save PDF artifact
    storage_dir = Path("artifacts") / "documents" / str(user_id) / str(job_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = generate_resume_filename(profile.full_name)
    pdf_path = storage_dir / filename
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Version sequence
    ver_count_stmt = select(ResumeVersion).where(
        ResumeVersion.user_id == user_id,
        ResumeVersion.job_id == job_id,
    )
    existing_versions = (await session.execute(ver_count_stmt)).scalars().all()
    next_ver = len(existing_versions) + 1

    resume_ver = ResumeVersion(
        user_id=user_id,
        job_id=job_id,
        profile_version_id=profile_version.id,
        content_json={
            **tailored.model_dump(),
            "source": "job_tailor",
            "report": {k: result[k] for k in (
                "before", "after", "keywords", "missing_information", "development_recommendations",
                "final_recommendation", "verdict", "ai_used",
            )},
        },
        template_id="classic_ats",
        pdf_path=str(pdf_path),
        truth_check_status=truth_result.status,
        flagged_claims=truth_result.flagged_claims,
        status="approved" if truth_result.status == "passed" else "draft",
        version_no=next_ver,
    )
    session.add(resume_ver)
    await session.commit()

    return resume_ver, str(pdf_path)


async def generate_cover_letter(
    session: AsyncSession,
    user_id: str,
    job_id: uuid.UUID,
    tone: str = "professional",
) -> CoverLetter:
    """Generate role- and company-specific cover letter (under 300 words) in the chosen tone."""
    prof_stmt = select(Profile).where(Profile.user_id == user_id)
    profile = (await session.execute(prof_stmt)).scalar_one_or_none()
    if not profile:
        raise ValueError(f"Profile not found for user {user_id}")

    job_stmt = (
        select(Job, Company.name.label("company_name"))
        .join(Company, Job.company_id == Company.id)
        .where(Job.id == job_id)
    )
    row = (await session.execute(job_stmt)).first()
    if not row:
        raise ValueError(f"Job not found {job_id}")

    job, company_name = row

    prompt = f"""Write a professional, concise cover letter (maximum 250-300 words) for:
Applicant: {profile.full_name} ({profile.headline or "Professional"})
Company: {company_name}
Target Role: {job.title}
Key Job Requirements: {job.description_text[:600]}
Candidate Summary & Experience: {profile.summary}

Tone: {TONE_GUIDE.get(tone, TONE_GUIDE["professional"])}
Open with what the company is trying to achieve in this role, then connect it to the candidate's
real achievements. Use only facts from the candidate's profile. No corporate clichés.
"""
    cl_output: CoverLetterOutput = await gemini_client.generate_structured(
        model_name=settings.gemini_model_smart,
        system_instruction="Write an authentic, highly tailored cover letter under 300 words strictly based on real candidate experience.",
        prompt=prompt,
        response_model=CoverLetterOutput,
        prompt_version="v1_cover_letter",
    )

    # Render HTML and PDF
    # Fetch profile version for reference
    snap_stmt = (
        select(ProfileVersion)
        .where(ProfileVersion.user_id == str(user_id))
        .order_by(ProfileVersion.version_no.desc())
        .limit(1)
    )
    profile_version = (await session.execute(snap_stmt)).scalar_one_or_none()
    if not profile_version:
        profile_version = await create_profile_snapshot_for_user(session=session, user_id=str(user_id))

    context = {
        "profile": {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "city": profile.city,
            "country": profile.country,
        },
        "company_name": company_name,
        "date_str": datetime.utcnow().strftime("%B %d, %Y"),
        "cover_letter_body": cl_output.cover_letter_text,
    }
    pdf_bytes = cover_letter_pdf_bytes(
        profile.full_name,
        [x for x in [profile.email, profile.phone, profile.city] if x],
        str(context["cover_letter_body"]),
    )

    storage_dir = Path("artifacts") / "documents" / str(user_id) / str(job_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = storage_dir / "Cover_Letter.pdf"
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    cover_letter = CoverLetter(
        user_id=str(user_id),
        job_id=job_id,
        profile_version_id=profile_version.id,
        content_text=cl_output.cover_letter_text,
        pdf_path=str(pdf_path),
    )
    session.add(cover_letter)
    await session.commit()

    return cover_letter


async def generate_screening_answers(
    questions: list[dict[str, Any]],
    user_context: str,
) -> ScreeningAnswersOutput:
    """Generate few-shot screening question answers with confidence scores."""
    prompt = f"""Candidate Background:
{user_context}

Application Questions to Answer:
{questions}

Answer each question accurately and professionally. Return confidence score (0.0 - 1.0).
"""
    return await gemini_client.generate_structured(
        model_name=settings.gemini_model_fast,
        system_instruction="Answer screening questions concisely and accurately using candidate facts.",
        prompt=prompt,
        response_model=ScreeningAnswersOutput,
        prompt_version="v1_screening",
    )
