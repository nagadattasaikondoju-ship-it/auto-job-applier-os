import re
import uuid
from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.ai.client import AIUnavailableError, gemini_client
from packages.ai.schemas import ParsedResumeOutput
from packages.core.config import settings
from packages.core.models.preferences import JobPreference
from packages.core.models.profile import (
    Certification,
    Education,
    Experience,
    Profile,
    Project,
    Resume,
    Skill,
)
from packages.core.services.ats import (
    UnsupportedFileError,
    analyze_resume,
    extract_text,
    heuristic_parse,
)
from packages.core.services.logistics import apply_pending_logistics
from packages.core.services.match_rules import estimate_experience_years
from packages.core.services.profile import create_profile_version

router = APIRouter(prefix="/resumes", tags=["Resumes"])


class ResumeTextPayload(BaseModel):
    raw_text: str
    filename: str = "resume.txt"


async def _parse_resume_text(raw_text: str) -> dict[str, Any]:
    """AI parse when a Gemini key is configured; otherwise a rule-based parse of the real text."""
    if gemini_client.is_mock:
        return _tidy(heuristic_parse(raw_text))
    try:
        parsed_output = await gemini_client.generate_structured(
            model_name=settings.gemini_model_smart,
            system_instruction=(
                "You are an expert resume parser for Indian and international tech talent. "
                "Extract personal info, a short headline (the person's role, never contact details), work "
                "experience with every bullet copied word for word, education (degree, field, institution, "
                "years, grade), projects, certifications and skills. Write names in normal capitalisation. "
                "Keep the company name separate from its city. Give every experience bullet a unique id "
                "(b1, b2, ...). Do NOT invent or reword facts that are not in the text."
            ),
            prompt=raw_text,
            response_model=ParsedResumeOutput,
            prompt_version="v2",
        )
    except AIUnavailableError:
        # Never block onboarding on the AI provider: read the real text with rules instead.
        return _tidy(heuristic_parse(raw_text))
    return _sanity_check(parsed_output.model_dump(), raw_text)


def _sanity_check(parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
    """Guard against degenerate AI output: impossible numbers and sections dropped by the model.

    Any section the AI left empty but the rule-based parser found is taken from the rules,
    so the user never loses data that is visibly in their resume.
    """
    rules = heuristic_parse(raw_text)
    for key in ("experiences", "educations", "skills", "projects", "certifications"):
        if not parsed.get(key) and rules.get(key):
            parsed[key] = rules[key]
    months = parsed.get("total_experience_months") or 0
    if not isinstance(months, int) or months < 0 or months > 600:
        parsed["total_experience_months"] = 0
    for key in ("full_name", "email", "phone", "city", "headline", "summary", "current_title", "current_company"):
        if not parsed.get(key) and rules.get(key):
            parsed[key] = rules[key]
    parsed["links"] = {**rules.get("links", {}), **(parsed.get("links") or {})}
    return _tidy(parsed)


def _months_from_dates(experiences: list[dict[str, Any]]) -> int:
    """Months of non-internship work, from start/end dates."""
    work = [
        SimpleNamespace(**{k: e.get(k) for k in ("start_date", "end_date", "is_current")})
        for e in experiences
        if not re.search(r"\b(intern|internship|trainee)\b", e.get("title") or "", re.I)
    ]
    return round(estimate_experience_years(work) * 12)


def _tidy(parsed: dict[str, Any]) -> dict[str, Any]:
    """Small cleanups both parsers need, e.g. a grade repeated inside the institution name."""
    # The model's experience total is often wrong; the dates on the resume are the source of truth
    from_dates = _months_from_dates(parsed.get("experiences") or [])
    if from_dates:
        parsed["total_experience_months"] = from_dates
    for ed in parsed.get("educations") or []:
        grade, inst = (ed.get("grade") or "").strip(), ed.get("institution") or ""
        if grade and grade in inst:
            ed["institution"] = inst.replace(grade, "").strip(" ,-|·")
    return parsed


async def _store_parsed_resume(
    db: AsyncSession, user_id: str, raw_text: str, filename: str
) -> dict[str, Any]:
    parsed = await _parse_resume_text(raw_text)
    resume_id = uuid.uuid4()
    # Earlier uploads stop being the master resume
    for old in (await db.execute(select(Resume).where(Resume.user_id == user_id))).scalars().all():
        old.is_master = False
    resume = Resume(
        id=resume_id,
        user_id=user_id,
        file_path=f"resumes/{user_id}/{resume_id}/{filename}",
        filename=filename,
        raw_text=raw_text,
        parsed_json=parsed,
        parse_status="succeeded",
        is_master=True,
    )
    db.add(resume)
    await db.commit()

    pref = (await db.execute(select(JobPreference).where(JobPreference.user_id == user_id))).scalar_one_or_none()
    report = analyze_resume(raw_text, target_roles=pref.target_roles if pref else [])
    return {"id": str(resume.id), "status": "succeeded", "parsed_profile": parsed, "ats": report}


@router.post("")
async def upload_and_parse_resume(
    payload: ResumeTextPayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Parse pasted resume text into the structured profile schema and run an ATS scan."""
    if len(payload.raw_text.strip()) < 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "RESUME_TOO_SHORT", "message": "Paste your full resume text (at least 100 characters)."},
        )
    return await _store_parsed_resume(db, current_user.user_id, payload.raw_text, payload.filename)


@router.post("/upload")
async def upload_resume_file(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a PDF, DOCX or text resume, extract its text on the server, parse it and scan it."""
    data = await file.read()
    try:
        raw_text = extract_text(file.filename or "resume.pdf", data)
    except UnsupportedFileError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "UNSUPPORTED_RESUME", "message": str(e)},
        ) from e
    return await _store_parsed_resume(db, current_user.user_id, raw_text, file.filename or "resume")


@router.get("/master")
async def get_master_resume(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """The most recent uploaded resume (text and parse), if any."""
    resume = (
        await db.execute(
            select(Resume)
            .where(Resume.user_id == current_user.user_id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESUME_NOT_FOUND", "message": "No resume uploaded yet."},
        )
    return {
        "id": str(resume.id),
        "filename": resume.filename,
        "parse_status": resume.parse_status,
        "parsed_json": resume.parsed_json,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
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
            links=data.get("links") or {},
        )
        db.add(profile)
        await apply_pending_logistics(db, profile)
    else:
        profile.full_name = data.get("full_name", profile.full_name)
        profile.phone = data.get("phone", profile.phone)
        profile.city = data.get("city", profile.city)
        profile.summary = data.get("summary", profile.summary)
        profile.headline = data.get("headline") or profile.headline
        profile.current_title = data.get("current_title") or profile.current_title
        profile.current_company = data.get("current_company") or profile.current_company
        profile.links = {**(profile.links or {}), **(data.get("links") or {})}

    # Confirming a resume replaces the previous resume-derived sections instead of duplicating them
    for model in (Experience, Education, Skill, Project, Certification):
        await db.execute(delete(model).where(model.user_id == current_user.user_id))

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
            start_date=edu_data.get("start_date") or "",
            end_date=edu_data.get("end_date") or "",
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

    # 5. Projects and certifications
    created_projects = [
        Project(
            id=uuid.uuid4(),
            user_id=current_user.user_id,
            title=(p.get("title") or "")[:128],
            description=p.get("description") or "",
            role=p.get("role") or "",
            url=p.get("url"),
            skills=p.get("skills") or [],
        )
        for p in data.get("projects", [])
        if p.get("title")
    ]
    created_certifications = [
        Certification(
            id=uuid.uuid4(),
            user_id=current_user.user_id,
            name=(c.get("name") or "")[:255],
            issuer=(c.get("issuer") or "")[:128],
            issue_date=c.get("issue_date") or "",
            credential_url=c.get("credential_url"),
        )
        for c in data.get("certifications", [])
        if c.get("name")
    ]
    db.add_all([*created_projects, *created_certifications])

    await db.commit()

    # 6. Create immutable profile snapshot
    version = await create_profile_version(
        session=db,
        user_id=current_user.user_id,
        profile=profile,
        experiences=created_experiences,
        educations=created_educations,
        projects=created_projects,
        certifications=created_certifications,
        skills=created_skills,
    )

    return {
        "status": "confirmed",
        "profile_version_id": str(version.id),
        "version_no": version.version_no,
    }
