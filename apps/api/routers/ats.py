"""ATS optimizer: scan a resume, suggest truthful bullet rewrites, and save an optimized version."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.ai.client import AIUnavailableError, gemini_client
from packages.ai.schemas import BulletRewriteOutput
from packages.core.config import settings
from packages.core.models.jobs import Job
from packages.core.models.matching import ResumeVersion
from packages.core.models.preferences import JobPreference
from packages.core.models.profile import Experience, Profile, ProfileVersion, Resume, Skill
from packages.core.services.ats import (
    ACTION_VERBS,
    WEAK_PHRASES,
    analyze_resume,
    has_metric,
    profile_snapshot_to_text,
    verify_rewrite,
)
from packages.core.services.profile import create_profile_snapshot_for_user

router = APIRouter(prefix="/ats", tags=["ATS Optimizer"])


class ScanRequest(BaseModel):
    resume_id: uuid.UUID | None = None
    use_profile: bool = False
    job_id: uuid.UUID | None = None
    jd_text: str | None = Field(default=None, max_length=20000)


class BulletRef(BaseModel):
    experience_id: str
    bullet_id: str
    text: str


class RewriteRequest(BaseModel):
    job_id: uuid.UUID | None = None
    jd_text: str | None = Field(default=None, max_length=20000)
    bullets: list[BulletRef] | None = None


class ApplyRequest(BaseModel):
    bullet_updates: list[BulletRef] = []
    summary: str | None = Field(default=None, max_length=2000)
    add_skills: list[str] = []


def _ai_available() -> bool:
    return not gemini_client.is_mock


def _tips(targets: list["BulletRef"]) -> dict[str, Any]:
    return {
        "ai_available": False,
        "suggestions": [
            {
                "experience_id": t.experience_id,
                "bullet_id": t.bullet_id,
                "original": t.text,
                "rewritten": None,
                "reason": "Start with an action verb and add a real, measurable result if you have one.",
                "blocked_reason": None,
            }
            for t in targets
        ],
    }


def _bullet_id(exp: Experience, index: int, bullet: Any) -> str:
    if isinstance(bullet, dict) and bullet.get("id"):
        return str(bullet["id"])
    return f"{exp.id}:{index}"


async def _jd_text(db: AsyncSession, job_id: uuid.UUID | None, jd_text: str | None) -> str | None:
    if jd_text and jd_text.strip():
        return jd_text
    if job_id:
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found."})
        return f"{job.title}\n{job.description_text or ''}\n{' '.join(job.required_skills or [])}"
    return None


async def _latest_snapshot(db: AsyncSession, user_id: str) -> dict[str, Any]:
    ver = (
        await db.execute(
            select(ProfileVersion)
            .where(ProfileVersion.user_id == user_id)
            .order_by(ProfileVersion.version_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if ver is None:
        ver = await create_profile_snapshot_for_user(db, user_id)
    return ver.snapshot_json


@router.post("/scan")
async def scan_resume(
    body: ScanRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Score a resume for ATS compatibility, optionally against a specific job."""
    text: str | None = None
    source = "profile"
    if body.resume_id:
        resume = (
            await db.execute(select(Resume).where(Resume.id == body.resume_id, Resume.user_id == user.user_id))
        ).scalar_one_or_none()
        if not resume:
            raise HTTPException(status_code=404, detail={"code": "RESUME_NOT_FOUND", "message": "Resume not found."})
        text, source = resume.raw_text, "upload"
    elif not body.use_profile:
        resume = (
            await db.execute(
                select(Resume).where(Resume.user_id == user.user_id).order_by(Resume.created_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if resume:
            text, source = resume.raw_text, "upload"

    if text is None:
        profile = (await db.execute(select(Profile).where(Profile.user_id == user.user_id))).scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=404,
                detail={"code": "PROFILE_NOT_FOUND", "message": "Upload a resume first."},
            )
        text = profile_snapshot_to_text(await _latest_snapshot(db, user.user_id))

    pref = (await db.execute(select(JobPreference).where(JobPreference.user_id == user.user_id))).scalar_one_or_none()
    report = analyze_resume(
        text,
        jd_text=await _jd_text(db, body.job_id, body.jd_text),
        target_roles=pref.target_roles if pref else [],
    )
    report["source"] = source
    return report


@router.post("/rewrite-bullets")
async def rewrite_bullets(
    body: RewriteRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Suggest stronger versions of profile bullets. Rewrites that add facts are blocked."""
    experiences = list((await db.execute(select(Experience).where(Experience.user_id == user.user_id))).scalars().all())
    skills = [s.name for s in (await db.execute(select(Skill).where(Skill.user_id == user.user_id))).scalars().all()]

    if body.bullets:
        targets = body.bullets
    else:
        # Default to the bullets the scanner considers weak
        targets = []
        for exp in experiences:
            for i, b in enumerate(exp.bullets or []):
                text = b.get("text", "") if isinstance(b, dict) else str(b)
                if not text.strip():
                    continue
                first = text.split()[0].lower().strip(",.")
                if first not in ACTION_VERBS or any(w in text.lower() for w in WEAK_PHRASES) or not has_metric(text):
                    targets.append(BulletRef(experience_id=str(exp.id), bullet_id=_bullet_id(exp, i, b), text=text))
        targets = targets[:12]

    if not targets:
        return {"ai_available": _ai_available(), "suggestions": []}

    if not _ai_available():
        return _tips(targets)

    jd = await _jd_text(db, body.job_id, body.jd_text)
    listing = "\n".join(f"[{t.bullet_id}] {t.text}" for t in targets)
    try:
        result: BulletRewriteOutput = await gemini_client.generate_structured(
            model_name=settings.gemini_model_fast,
            system_instruction=(
                "You rewrite resume bullets to be ATS-friendly: start with a strong action verb, be specific, "
                "15-30 words. Use ONLY facts in the original bullet. Never add numbers, tools, companies, "
                "team sizes or results that are not in the original. If the original has no number, do not invent one."
            ),
            prompt=(
                (f"Target job:\n{jd[:1500]}\n\n" if jd else "")
                + f"Rewrite each bullet. Keep the id in brackets.\n{listing}"
            ),
            response_model=BulletRewriteOutput,
            prompt_version="v1_bullet_rewrite",
        )
    except AIUnavailableError:
        return _tips(targets)
    by_id = {r.bullet_id: r for r in result.rewrites}
    suggestions = []
    for t in targets:
        r = by_id.get(t.bullet_id)
        rewritten = r.rewritten.strip() if r else None
        blocked = verify_rewrite(t.text, rewritten, skills) if rewritten else None
        suggestions.append(
            {
                "experience_id": t.experience_id,
                "bullet_id": t.bullet_id,
                "original": t.text,
                "rewritten": None if blocked else rewritten,
                "reason": r.reason if r else "No suggestion.",
                "blocked_reason": blocked,
            }
        )
    return {"ai_available": True, "suggestions": suggestions}


@router.post("/apply")
async def apply_optimizations(
    body: ApplyRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Apply accepted improvements to the master profile and save a new optimized resume version."""
    profile = (await db.execute(select(Profile).where(Profile.user_id == user.user_id))).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail={"code": "PROFILE_NOT_FOUND", "message": "Create your profile first."})

    experiences = {
        str(e.id): e
        for e in (await db.execute(select(Experience).where(Experience.user_id == user.user_id))).scalars().all()
    }
    skills = [s.name for s in (await db.execute(select(Skill).where(Skill.user_id == user.user_id))).scalars().all()]
    changes: list[str] = []
    rejected: list[dict[str, str]] = []

    for upd in body.bullet_updates:
        exp = experiences.get(upd.experience_id)
        if not exp:
            continue
        bullets = list(exp.bullets or [])
        for i, b in enumerate(bullets):
            if _bullet_id(exp, i, b) != upd.bullet_id:
                continue
            original = b.get("text", "") if isinstance(b, dict) else str(b)
            reason = verify_rewrite(original, upd.text, skills)
            if reason:
                rejected.append({"bullet_id": upd.bullet_id, "reason": reason})
                break
            new_b = dict(b) if isinstance(b, dict) else {}
            new_b.setdefault("id", upd.bullet_id)
            new_b["text"] = upd.text.strip()
            bullets[i] = new_b
            changes.append(f"Rewrote a bullet at {exp.company}")
            break
        exp.bullets = bullets

    if body.summary is not None and body.summary.strip() and body.summary.strip() != (profile.summary or ""):
        profile.summary = body.summary.strip()
        changes.append("Updated summary")

    existing = {s.lower() for s in skills}
    for name in body.add_skills:
        n = name.strip()
        if n and n.lower() not in existing:
            db.add(
                Skill(
                    id=uuid.uuid4(),
                    user_id=user.user_id,
                    name=n,
                    normalized_name=n.lower(),
                    category="technical",
                    years=1.0,
                    proficiency="intermediate",
                    source="user",
                )
            )
            existing.add(n.lower())
            changes.append(f"Added skill {n}")

    await db.commit()
    version = await create_profile_snapshot_for_user(db, user.user_id)
    snap = version.snapshot_json

    content = {
        "source": "ats_optimizer",
        "summary": snap.get("profile", {}).get("summary") or "",
        "skills_ordered": [s.get("name") for s in snap.get("skills", [])],
        "experiences": [
            {
                "experience_id": e.get("id"),
                "company": e.get("company"),
                "title": e.get("title"),
                "bullets": [
                    {"source_bullet_id": (b.get("id") if isinstance(b, dict) else None) or f"{e.get('id')}:{i}",
                     "text": b.get("text", "") if isinstance(b, dict) else str(b)}
                    for i, b in enumerate(e.get("bullets", []))
                ],
            }
            for e in snap.get("experiences", [])
        ],
        "keywords_used": [],
        "changes_made": changes,
    }
    count = len(
        (
            await db.execute(
                select(ResumeVersion.id).where(ResumeVersion.user_id == user.user_id, ResumeVersion.job_id.is_(None))
            )
        ).all()
    )
    rv = ResumeVersion(
        user_id=user.user_id,
        job_id=None,
        profile_version_id=version.id,
        content_json=content,
        template_id="classic_ats",
        pdf_path=None,
        truth_check_status="passed",
        flagged_claims=[],
        status="approved",
        version_no=count + 1,
    )
    db.add(rv)
    await db.commit()

    report = analyze_resume(profile_snapshot_to_text(snap))
    return {
        "resume_version_id": str(rv.id),
        "version_no": rv.version_no,
        "changes": changes,
        "rejected": rejected,
        "ats": report,
    }
