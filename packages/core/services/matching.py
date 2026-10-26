"""Funnel Matching Engine: Hard Filters -> pgvector Ranking -> Batched Gemini Evaluation."""

import json
import logging

from sqlalchemy import ColumnElement, and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai.client import gemini_client
from packages.ai.schemas import MatchScoreOutput
from packages.core.config import settings
from packages.core.models.jobs import Company, Job, JobEmbedding
from packages.core.models.matching import JobMatch
from packages.core.models.preferences import JobPreference
from packages.core.models.profile import (
    Experience,
    Profile,
    ProfileEmbedding,
    ProfileVersion,
    Skill,
)
from packages.core.redis import get_async_redis
from packages.core.services.match_rules import (
    FOREIGN_LOCATION_REGEX,
    estimate_experience_years,
    location_patterns,
    role_title_patterns,
    rule_based_score,
    title_allowed,
)

logger = logging.getLogger("applyon.matching")

# Gemini scores only the best few candidates per run; the rest use rule-based scores.
AI_SCORED_PER_RUN = 8


async def run_matching_funnel_for_user(
    session: AsyncSession,
    user_id: str,
    top_k: int = 30,
) -> list[JobMatch]:
    """Execute the multi-stage matching funnel for a user."""
    # 1. Fetch user preferences and active profile
    pref_stmt = select(JobPreference).where(JobPreference.user_id == user_id)
    pref_res = await session.execute(pref_stmt)
    preferences = pref_res.scalar_one_or_none()

    prof_stmt = select(Profile).where(Profile.user_id == user_id)
    prof_res = await session.execute(prof_stmt)
    profile = prof_res.scalar_one_or_none()

    if not profile or not preferences:
        logger.info("Matching aborted for user %s: missing profile or preferences", user_id)
        return []

    # Get active profile version
    ver_stmt = (
        select(ProfileVersion)
        .where(ProfileVersion.user_id == user_id)
        .order_by(ProfileVersion.version_no.desc())
        .limit(1)
    )
    ver_res = await session.execute(ver_stmt)
    profile_version = ver_res.scalar_one_or_none()
    profile_version_id = profile_version.id if profile_version else None

    # Get user profile embedding
    emb_stmt = select(ProfileEmbedding).where(
        ProfileEmbedding.user_id == user_id,
        ProfileEmbedding.kind == "full",
    )
    emb_res = await session.execute(emb_stmt)
    user_embedding = emb_res.scalar_one_or_none()

    experiences = list((await session.execute(select(Experience).where(Experience.user_id == user_id))).scalars().all())
    skills = [
        sk.name for sk in (await session.execute(select(Skill).where(Skill.user_id == user_id))).scalars().all() if sk.name
    ]

    # Effective experience: parsed total, else estimated from dates, never below the chosen band
    user_exp_years = (profile.total_experience_months or 0) / 12.0 or estimate_experience_years(experiences)
    user_exp_years = max(user_exp_years, float(preferences.min_exp or 0))

    # 2. Stage 1: SQL hard filters (roles, locations, experience, exclusions)
    existing_matches = (await session.execute(select(JobMatch.job_id).where(JobMatch.user_id == user_id))).scalars().all()
    filter_conditions: list[ColumnElement[bool]] = [
        Job.is_active.is_(True),
        Job.is_suspicious.is_(False),
        Job.experience_min <= int(user_exp_years + 1.5),
        Job.experience_max >= max(0, int(user_exp_years - 1.5)),
    ]
    if existing_matches:
        filter_conditions.append(not_(Job.id.in_(set(existing_matches))))

    title_patterns = role_title_patterns(preferences.target_roles or [], preferences.role_keywords or [])
    if title_patterns:
        filter_conditions.append(or_(*[Job.title.ilike(p) for p in title_patterns]))

    allows_remote = "remote" in (preferences.remote_mode or []) or any(
        c.lower() == "remote" for c in (preferences.locations or [])
    )
    city_patterns = location_patterns(preferences.locations or [])
    # Remote, but not restricted to another country ("Remote - United States")
    remote_in_reach = and_(
        Job.remote_mode == "remote",
        or_(
            Job.location_raw.is_(None),
            Job.location_raw.ilike("%india%"),
            not_(Job.location_raw.op("~*")(FOREIGN_LOCATION_REGEX)),
        ),
    )
    if city_patterns:
        loc_clauses: list[ColumnElement[bool]] = [Job.location_raw.ilike(p) for p in city_patterns]
        if allows_remote:
            loc_clauses.append(remote_in_reach)
        filter_conditions.append(or_(*loc_clauses))
    elif allows_remote:
        filter_conditions.append(remote_in_reach)
    elif preferences.remote_mode:
        filter_conditions.append(Job.remote_mode.in_(preferences.remote_mode))

    if preferences.excluded_companies:
        filter_conditions.append(
            not_(func.lower(Company.name).in_([c.lower() for c in preferences.excluded_companies]))
        )
    for kw in preferences.excluded_keywords or []:
        filter_conditions.append(not_(Job.title.ilike(f"%{kw}%")))

    if preferences.min_salary_lpa:
        filter_conditions.append(
            or_(Job.salary_max_lpa.is_(None), Job.salary_max_lpa >= preferences.min_salary_lpa)
        )

    base_query = (
        select(Job, JobEmbedding.embedding)
        .join(Company, Job.company_id == Company.id)
        .outerjoin(JobEmbedding, Job.id == JobEmbedding.job_id)
        .where(*filter_conditions)
        .order_by(Job.posted_at.desc().nulls_last())
    )
    candidates = [
        (job, vec)
        for job, vec in (await session.execute(base_query.limit(400))).all()
        if title_allowed(job.title, preferences.seniority)
    ]

    if not candidates:
        logger.info("No candidates passed Stage 1 hard filters for user %s", user_id)
        return []

    # 3. Stage 2: rank by skill overlap and title fit, blended with vector similarity when available
    scored_candidates = []
    for job, job_vec in candidates:
        rules = rule_based_score(skills, preferences.target_roles or [], job, preferences.min_match_score)
        rank = rules["match_score"] / 100.0
        vector_score = None
        if user_embedding is not None and job_vec is not None:
            try:
                dot = sum(a * b for a, b in zip(user_embedding.embedding, job_vec, strict=False))
                vector_score = max(0.0, min(1.0, (dot + 1.0) / 2.0))
                rank = 0.7 * rank + 0.3 * vector_score
            except Exception:
                vector_score = None
        scored_candidates.append((job, rank, vector_score, rules))

    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = scored_candidates[:top_k]

    # 4. Stage 3: AI scoring for the very top (saves quota); rules score the rest
    redis = await get_async_redis()
    results: list[JobMatch] = []
    ai_budget = 0 if gemini_client.is_mock else min(AI_SCORED_PER_RUN, len(top_candidates))
    profile_brief = _profile_brief(profile, experiences, skills, user_exp_years)

    for idx, (job, _rank, v_score, rules) in enumerate(top_candidates):
        match_out: MatchScoreOutput | None = None
        if idx < ai_budget:
            cache_key = f"match:{user_id}:{job.id}:{profile_version_id or 'none'}"
            cached_data = await redis.get(cache_key)
            if cached_data:
                match_out = MatchScoreOutput.model_validate(json.loads(cached_data))
            else:
                try:
                    match_out = await gemini_client.generate_structured(
                        model_name=settings.gemini_model_fast,
                        system_instruction=(
                            "You are an expert recruiter for Indian tech hiring. Score how well the candidate "
                            "fits the job from 0-100, honestly. Only cite facts present in the candidate profile."
                        ),
                        prompt=(
                            f"Candidate:\n{profile_brief}\n\nJob (job_id {job.id}):\nTitle: {job.title}\n"
                            f"Location: {job.location_raw}\nExperience: {job.experience_min}-{job.experience_max} years\n"
                            f"Required skills: {', '.join(job.required_skills or [])}\n"
                            f"Description: {(job.description_text or '')[:1500]}\n\n"
                            "Return match_score, decision (apply >= 70, maybe 50-69, skip < 50), fit_reasons, "
                            "gaps, resume_focus (which of the candidate's real experience to emphasise) and risk_flags."
                        ),
                        response_model=MatchScoreOutput,
                        cache_ttl_seconds=86400 * 30,
                    )
                    await redis.set(cache_key, match_out.model_dump_json(), ex=86400 * 30)
                except Exception as e:
                    logger.warning("Gemini scoring failed for job %s: %s", job.id, e)
                    ai_budget = idx  # stop calling AI this run (quota/outage); rules take over
                    match_out = None
        if match_out is None:
            match_out = MatchScoreOutput(job_id=str(job.id), **rules)

        job_match = JobMatch(
            user_id=user_id,
            job_id=job.id,
            profile_version_id=profile_version_id,
            filter_passed=True,
            vector_score=v_score,
            match_score=match_out.match_score,
            decision=match_out.decision,
            fit_reasons=match_out.fit_reasons,
            gaps=match_out.gaps,
            resume_focus=match_out.resume_focus,
            risk_flags=match_out.risk_flags,
            status="new",
        )
        session.add(job_match)
        results.append(job_match)

    await session.commit()
    return results


def _profile_brief(profile: Profile, experiences: list[Experience], skills: list[str], years: float) -> str:
    lines = [
        f"Headline: {profile.headline or profile.current_title or 'Not stated'}",
        f"Experience: about {years:.1f} years",
        f"Skills: {', '.join(skills[:30]) or 'Not listed'}",
        f"Summary: {(profile.summary or '')[:400]}",
    ]
    for e in experiences[:4]:
        bullets = [b.get("text", "") if isinstance(b, dict) else str(b) for b in (e.bullets or [])][:3]
        lines.append(f"- {e.title} at {e.company}: " + " | ".join(bullets))
    return "\n".join(lines)
