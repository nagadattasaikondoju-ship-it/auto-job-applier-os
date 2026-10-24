import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.profile import (
    Certification,
    Education,
    Experience,
    Profile,
    ProfileVersion,
    Project,
    Skill,
)


def compute_profile_completeness(
    profile: Profile | None,
    experiences: list[Experience] | None = None,
    educations: list[Education] | None = None,
    skills: list[Skill] | None = None,
) -> dict[str, Any]:
    """
    Compute profile completeness score (0-100) and identify missing elements.
    Spec Section 5: Autopilot can only start when completeness >= 80.
    """
    if not profile:
        return {
            "score": 0,
            "can_start_autopilot": False,
            "missing_fields": ["profile_not_created"],
            "breakdown": {},
        }

    missing_fields: list[str] = []
    points = 0

    # 1. Basic Info (25 pts)
    if profile.full_name and profile.email:
        points += 10
    else:
        missing_fields.append("name_or_email")

    if profile.phone:
        points += 5
    else:
        missing_fields.append("phone_number")

    if profile.city:
        points += 5
    else:
        missing_fields.append("current_city")

    if profile.headline and profile.summary:
        points += 5
    else:
        missing_fields.append("headline_and_summary")

    # 2. Logistics & Compensation (25 pts)
    if profile.expected_ctc_lpa is not None and profile.expected_ctc_lpa > 0:
        points += 10
    else:
        missing_fields.append("expected_ctc")

    if profile.notice_period_days is not None:
        points += 10
    else:
        missing_fields.append("notice_period")

    if profile.work_authorization:
        points += 5
    else:
        missing_fields.append("work_authorization")

    # 3. Work Experience (20 pts)
    if experiences and len(experiences) > 0:
        points += 20
    else:
        missing_fields.append("work_experience")

    # 4. Education (15 pts)
    if educations and len(educations) > 0:
        points += 15
    else:
        missing_fields.append("education")

    # 5. Skills (15 pts)
    if skills and len(skills) >= 3:
        points += 15
    elif skills and len(skills) > 0:
        points += 8
        missing_fields.append("minimum_3_skills")
    else:
        missing_fields.append("skills")

    score = min(100, points)
    return {
        "score": score,
        "can_start_autopilot": score >= 80,
        "missing_fields": missing_fields,
    }


async def create_profile_version(
    session: AsyncSession,
    user_id: str,
    profile: Profile,
    experiences: list[Experience],
    educations: list[Education],
    projects: list[Project],
    certifications: list[Certification],
    skills: list[Skill],
) -> ProfileVersion:
    """Create an immutable snapshot of the user's master profile."""
    # Get latest version number
    stmt = select(func.max(ProfileVersion.version_no)).where(ProfileVersion.user_id == user_id)
    result = await session.execute(stmt)
    latest_version = result.scalar_one_or_none() or 0
    new_version_no = latest_version + 1

    snapshot = {
        "version_no": new_version_no,
        "profile": {
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
            "work_authorization": profile.work_authorization,
            "links": profile.links,
            "languages": profile.languages,
        },
        "experiences": [
            {
                "id": str(exp.id),
                "company": exp.company,
                "title": exp.title,
                "employment_type": exp.employment_type,
                "location": exp.location,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "is_current": exp.is_current,
                "bullets": exp.bullets,
            }
            for exp in experiences
        ],
        "educations": [
            {
                "id": str(edu.id),
                "institution": edu.institution,
                "degree": edu.degree,
                "field": edu.field,
                "start_date": edu.start_date,
                "end_date": edu.end_date,
                "grade": edu.grade,
                "board": edu.board,
            }
            for edu in educations
        ],
        "projects": [
            {
                "id": str(proj.id),
                "title": proj.title,
                "description": proj.description,
                "role": proj.role,
                "url": proj.url,
                "skills": proj.skills,
            }
            for proj in projects
        ],
        "certifications": [
            {
                "id": str(cert.id),
                "name": cert.name,
                "issuer": cert.issuer,
                "issue_date": cert.issue_date,
                "credential_url": cert.credential_url,
            }
            for cert in certifications
        ],
        "skills": [
            {
                "id": str(skill.id),
                "name": skill.name,
                "normalized_name": skill.normalized_name,
                "category": skill.category,
                "years": skill.years,
                "proficiency": skill.proficiency,
            }
            for skill in skills
        ],
    }

    profile_version = ProfileVersion(
        id=uuid.uuid4(),
        user_id=user_id,
        version_no=new_version_no,
        snapshot_json=snapshot,
    )
    session.add(profile_version)
    await session.commit()
    return profile_version


async def create_profile_snapshot_for_user(session: AsyncSession, user_id: str) -> ProfileVersion:
    """Fetch complete profile components and build an immutable ProfileVersion snapshot."""
    prof_stmt = select(Profile).where(Profile.user_id == user_id)
    profile = (await session.execute(prof_stmt)).scalar_one_or_none()
    if not profile:
        profile = Profile(id=uuid.uuid4(), user_id=user_id, full_name="Candidate")
        session.add(profile)
        await session.flush()

    exp_stmt = select(Experience).where(Experience.user_id == user_id)
    experiences = list((await session.execute(exp_stmt)).scalars().all())

    edu_stmt = select(Education).where(Education.user_id == user_id)
    educations = list((await session.execute(edu_stmt)).scalars().all())

    proj_stmt = select(Project).where(Project.user_id == user_id)
    projects = list((await session.execute(proj_stmt)).scalars().all())

    cert_stmt = select(Certification).where(Certification.user_id == user_id)
    certifications = list((await session.execute(cert_stmt)).scalars().all())

    skill_stmt = select(Skill).where(Skill.user_id == user_id)
    skills = list((await session.execute(skill_stmt)).scalars().all())

    return await create_profile_version(
        session=session,
        user_id=user_id,
        profile=profile,
        experiences=experiences,
        educations=educations,
        projects=projects,
        certifications=certifications,
        skills=skills,
    )
