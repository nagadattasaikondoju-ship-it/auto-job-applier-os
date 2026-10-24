import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.ai.client import gemini_client
from packages.ai.schemas import ParsedResumeOutput
from packages.core.config import settings
from packages.core.models.profile import (
    Education,
    Experience,
    Profile,
    Resume,
    Skill,
)
from packages.core.services.profile import create_profile_version

router = APIRouter(prefix="/resumes", tags=["Resumes"])


class ResumeTextPayload(BaseModel):
    raw_text: str
    filename: str = "resume.txt"


@router.post("")
async def upload_and_parse_resume(
    payload: ResumeTextPayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload resume text or document, parse using Gemini into structured schema, and store."""
    resume_id = uuid.uuid4()

    # Call Gemini to parse resume text into structured schema
    parsed_output = await gemini_client.generate_structured(
        model_name=settings.gemini_model_smart,
        system_instruction=(
            "You are an expert resume parser for Indian and international tech talent. "
            "Extract candidate personal info, categorized skills, and work experiences with quantifiable metrics. "
            "Do NOT hallucinate facts not present in the text."
        ),
        prompt=payload.raw_text,
        response_model=ParsedResumeOutput,
        prompt_version="v1",
    )

    resume = Resume(
        id=resume_id,
        user_id=current_user.user_id,
        file_path=f"resumes/{current_user.user_id}/{resume_id}/{payload.filename}",
        filename=payload.filename,
        raw_text=payload.raw_text,
        parsed_json=parsed_output.model_dump(),
        parse_status="succeeded",
        is_master=True,
    )
    db.add(resume)
    await db.commit()

    return {
        "id": str(resume.id),
        "status": "succeeded",
        "parsed_profile": resume.parsed_json,
    }


@router.get("/{resume_id}")
async def get_resume_parsed_data(
    resume_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get parsed resume JSON by ID."""
    stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.user_id)
    resume = (await db.execute(stmt)).scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "Resume was not found."},
        )

    return {
        "id": str(resume.id),
        "filename": resume.filename,
        "parse_status": resume.parse_status,
        "parsed_json": resume.parsed_json,
    }


@router.post("/{resume_id}/confirm")
async def confirm_resume_profile(
    resume_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Confirm candidate parsed resume data to create/update the master profile
    and capture the immutable initial ProfileVersion snapshot.
    """
    stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.user_id)
    resume = (await db.execute(stmt)).scalar_one_or_none()

    if not resume or not resume.parsed_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "Parsed resume data not available."},
        )

    data = resume.parsed_json

    # 1. Upsert Profile
    p_stmt = select(Profile).where(Profile.user_id == current_user.user_id)
    profile = (await db.execute(p_stmt)).scalar_one_or_none()

    if not profile:
        profile = Profile(
            user_id=current_user.user_id,
            full_name=data.get("full_name", "Applicant"),
            email=data.get("email", current_user.email or f"{current_user.user_id}@applyon.in"),
            phone=data.get("phone", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            country=data.get("country", "India"),
            headline=data.get("headline", ""),
            summary=data.get("summary", ""),
            current_title=data.get("current_title", ""),
            current_company=data.get("current_company", ""),
            total_experience_months=data.get("total_experience_months", 0),
        )
        db.add(profile)
    else:
        profile.full_name = data.get("full_name", profile.full_name)
        profile.phone = data.get("phone", profile.phone)
        profile.city = data.get("city", profile.city)
        profile.summary = data.get("summary", profile.summary)

    # 2. Add Experiences
    created_experiences = []
    for exp_data in data.get("experiences", []):
        exp = Experience(
            id=uuid.uuid4(),
            user_id=current_user.user_id,
            company=exp_data.get("company", ""),
            title=exp_data.get("title", ""),
            employment_type=exp_data.get("employment_type", "full-time"),
            location=exp_data.get("location", ""),
            start_date=exp_data.get("start_date", ""),
            end_date=exp_data.get("end_date"),
            is_current=exp_data.get("is_current", False),
            bullets=exp_data.get("bullets", []),
        )
        db.add(exp)
        created_experiences.append(exp)

    # 3. Add Educations
    created_educations = []
    for edu_data in data.get("educations", []):
        edu = Education(
            id=uuid.uuid4(),
            user_id=current_user.user_id,
            institution=edu_data.get("institution", ""),
            degree=edu_data.get("degree", ""),
            field=edu_data.get("field", ""),
            grade=edu_data.get("grade", ""),
        )
        db.add(edu)
        created_educations.append(edu)

    # 4. Add Skills
    created_skills = []
    for s_data in data.get("skills", []):
        skill = Skill(
            id=uuid.uuid4(),
            user_id=current_user.user_id,
            name=s_data.get("name", ""),
            normalized_name=s_data.get("normalized_name", s_data.get("name", "").lower()),
            category=s_data.get("category", "technical"),
            years=s_data.get("years", 1.0),
            proficiency=s_data.get("proficiency", "intermediate"),
            source="resume",
        )
        db.add(skill)
        created_skills.append(skill)

    await db.commit()

    # 5. Create immutable profile snapshot
    version = await create_profile_version(
        session=db,
        user_id=current_user.user_id,
        profile=profile,
        experiences=created_experiences,
        educations=created_educations,
        projects=[],
        certifications=[],
        skills=created_skills,
    )

    return {
        "status": "confirmed",
        "profile_version_id": str(version.id),
        "version_no": version.version_no,
    }
