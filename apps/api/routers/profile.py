import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.profile import (
    Certification,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)
from packages.core.services.profile import (
    compute_profile_completeness,
)

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileUpdateSchema(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    headline: str | None = None
    summary: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    current_ctc_lpa: float | None = None
    expected_ctc_lpa: float | None = None
    notice_period_days: int | None = None
    currently_serving_notice: bool | None = None
    willing_to_relocate: bool | None = None
    links: dict[str, str] | None = None


class ExperienceCreateSchema(BaseModel):
    company: str
    title: str
    employment_type: str = "full-time"
    location: str = ""
    start_date: str
    end_date: str | None = None
    is_current: bool = False
    bullets: list[dict[str, Any]] = []


class SkillCreateSchema(BaseModel):
    name: str
    category: str = "technical"
    years: float = 1.0
    proficiency: str = "intermediate"


@router.get("")
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve the full master profile including experiences, educations, and skills."""
    stmt = select(Profile).where(Profile.user_id == current_user.user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Profile has not been created yet."},
        )

    # Fetch related entities
    exp_stmt = select(Experience).where(Experience.user_id == current_user.user_id)
    edu_stmt = select(Education).where(Education.user_id == current_user.user_id)
    skill_stmt = select(Skill).where(Skill.user_id == current_user.user_id)

    experiences = (await db.execute(exp_stmt)).scalars().all()
    educations = (await db.execute(edu_stmt)).scalars().all()
    skills = (await db.execute(skill_stmt)).scalars().all()
    projects = (await db.execute(select(Project).where(Project.user_id == current_user.user_id))).scalars().all()
    certifications = (
        await db.execute(select(Certification).where(Certification.user_id == current_user.user_id))
    ).scalars().all()

    completeness = compute_profile_completeness(
        profile, list(experiences), list(educations), list(skills)
    )

    return {
        "profile": {
            "user_id": profile.user_id,
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "city": profile.city,
            "state": profile.state,
            "country": profile.country,
            "headline": profile.headline,
            "summary": profile.summary,
            "total_experience_months": profile.total_experience_months,
            "current_title": profile.current_title,
            "current_company": profile.current_company,
            "current_ctc_lpa": profile.current_ctc_lpa,
            "expected_ctc_lpa": profile.expected_ctc_lpa,
            "notice_period_days": profile.notice_period_days,
            "currently_serving_notice": profile.currently_serving_notice,
            "willing_to_relocate": profile.willing_to_relocate,
            "links": profile.links,
        },
        "experiences": [
            {
                "id": str(e.id),
                "company": e.company,
                "title": e.title,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "is_current": e.is_current,
                "bullets": e.bullets,
            }
            for e in experiences
        ],
        "educations": [
            {
                "id": str(ed.id),
                "institution": ed.institution,
                "degree": ed.degree,
                "field": ed.field,
                "grade": ed.grade,
            }
            for ed in educations
        ],
        "skills": [
            {
                "id": str(s.id),
                "name": s.name,
                "normalized_name": s.normalized_name,
                "category": s.category,
                "proficiency": s.proficiency,
            }
            for s in skills
        ],
        "projects": [
            {"id": str(p.id), "title": p.title, "description": p.description, "url": p.url, "skills": p.skills}
            for p in projects
        ],
        "certifications": [
            {"id": str(c.id), "name": c.name, "issuer": c.issuer, "issue_date": c.issue_date}
            for c in certifications
        ],
        "completeness": completeness,
    }


@router.put("")
async def update_my_profile(
    payload: ProfileUpdateSchema,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Create or update attributes on the master profile."""
    stmt = select(Profile).where(Profile.user_id == current_user.user_id)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    if not profile:
        profile = Profile(
            user_id=current_user.user_id,
            email=current_user.email or f"{current_user.user_id}@applyon.in",
            full_name=payload.full_name or "Applicant",
        )
        db.add(profile)

    # Update fields provided in payload
    for k, v in payload.model_dump(exclude_unset=True).items():
        if hasattr(profile, k) and v is not None:
            setattr(profile, k, v)

    await db.commit()
    return {"status": "ok", "message": "Profile updated successfully"}


@router.get("/completeness")
async def get_completeness_score(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return profile completeness percentage and readiness for Autopilot (>= 80)."""
    stmt = select(Profile).where(Profile.user_id == current_user.user_id)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    exp_stmt = select(Experience).where(Experience.user_id == current_user.user_id)
    edu_stmt = select(Education).where(Education.user_id == current_user.user_id)
    skill_stmt = select(Skill).where(Skill.user_id == current_user.user_id)

    experiences = (await db.execute(exp_stmt)).scalars().all()
    educations = (await db.execute(edu_stmt)).scalars().all()
    skills = (await db.execute(skill_stmt)).scalars().all()

    return compute_profile_completeness(profile, list(experiences), list(educations), list(skills))


@router.post("/experiences")
async def add_experience(
    payload: ExperienceCreateSchema,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add a work experience item."""
    exp = Experience(
        id=uuid.uuid4(),
        user_id=current_user.user_id,
        company=payload.company,
        title=payload.title,
        employment_type=payload.employment_type,
        location=payload.location,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
        bullets=payload.bullets,
    )
    db.add(exp)
    await db.commit()
    return {"id": str(exp.id), "status": "created"}


@router.post("/skills")
async def add_skill(
    payload: SkillCreateSchema,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add a skill item."""
    skill = Skill(
        id=uuid.uuid4(),
        user_id=current_user.user_id,
        name=payload.name,
        normalized_name=payload.name.strip().lower(),
        category=payload.category,
        years=payload.years,
        proficiency=payload.proficiency,
        source="user",
    )
    db.add(skill)
    await db.commit()
    return {"id": str(skill.id), "status": "created"}
