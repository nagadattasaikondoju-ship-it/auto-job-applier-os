"""Funnel Matching Engine: Hard Filters -> pgvector Ranking -> Batched Gemini Evaluation."""

import json
import logging
from typing import Literal

from sqlalchemy import and_, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai.client import gemini_client
from packages.ai.schemas import MatchScoreOutput
from packages.core.config import settings
from packages.core.models.jobs import Company, Job, JobEmbedding
from packages.core.models.matching import JobMatch
from packages.core.models.preferences import JobPreference
from packages.core.models.profile import Profile, ProfileEmbedding, ProfileVersion
from packages.core.redis import get_async_redis

logger = logging.getLogger("applyon.matching")


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

    # User experience in years
    user_exp_years = (profile.total_experience_months or 0) / 12.0

    # 2. Stage 1: SQL Hard Filters
    # Existing match job IDs to exclude
    existing_stmt = select(JobMatch.job_id).where(JobMatch.user_id == user_id)
    existing_matches = (await session.execute(existing_stmt)).scalars().all()
    excluded_job_ids = set(existing_matches)

    filter_conditions = [
        Job.is_active.is_(True),
        Job.is_suspicious.is_(False),
        # Experience tolerance: within ±1.5 years
        Job.experience_min <= int(user_exp_years + 1.5),
        Job.experience_max >= max(0, int(user_exp_years - 1.5)),
    ]

    if excluded_job_ids:
        filter_conditions.append(not_(Job.id.in_(excluded_job_ids)))

    if preferences.excluded_companies:
        filter_conditions.append(not_(Company.name.in_(preferences.excluded_companies)))

    if preferences.min_salary_lpa:
        # If job specifies a maximum salary, it should meet user's minimum
        filter_conditions.append(
            and_(
                or_(
                    Job.salary_max_lpa.is_(None),
                    Job.salary_max_lpa >= preferences.min_salary_lpa,
                )
            )
        )

    base_query = (
        select(Job, JobEmbedding.embedding)
        .join(Company, Job.company_id == Company.id)
        .outerjoin(JobEmbedding, Job.id == JobEmbedding.job_id)
        .where(*filter_conditions)
    )

    candidates_res = await session.execute(base_query.limit(200))
    candidates = candidates_res.all()

    if not candidates:
        logger.info("No candidates passed Stage 1 hard filters for user %s", user_id)
        return []

    # 3. Stage 2: Vector distance ranking
    scored_candidates = []
    for job, job_vec in candidates:
        vector_score = 0.5  # default if embedding not present
        if user_embedding and job_vec is not None:
            # Cosine similarity approximation
            try:
                # dot product of normalized vectors
                u_vec = user_embedding.embedding
                dot = sum(a * b for a, b in zip(u_vec, job_vec, strict=False))
                vector_score = max(0.0, min(1.0, (dot + 1.0) / 2.0))
            except Exception:
                vector_score = 0.5
        scored_candidates.append((job, vector_score))

    # Sort descending by vector_score and take top_k
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = scored_candidates[:top_k]

    # 4. Stage 3: Batched Gemini Scoring
    redis = await get_async_redis()
    results: list[JobMatch] = []

    # Process in batches of 5
    batch_size = 5
    for i in range(0, len(top_candidates), batch_size):
        batch = top_candidates[i : i + batch_size]
        for job, v_score in batch:
            cache_key = f"match:{user_id}:{job.id}:{profile_version_id or 'none'}"
            cached_data = await redis.get(cache_key)

            if cached_data:
                score_data = json.loads(cached_data)
                match_out = MatchScoreOutput.model_validate(score_data)
            else:
                prompt = f"""Evaluate candidate-job fit.
Candidate Profile:
- Title: {profile.current_title or "Fresher"}
- Experience: {user_exp_years:.1f} years
- Summary: {profile.summary or "Motivated professional"}

Job Posting:
- Title: {job.title}
- Required Experience: {job.experience_min}-{job.experience_max} years
- Description: {job.description_text[:1200]}

Rate match 0-100, provide decision ('apply', 'maybe', 'skip'), fit reasons, gaps, and resume focus.
"""
                try:
                    match_out = await gemini_client.generate_structured(
                        model_name=settings.gemini_model_fast,
                        system_instruction="You are an expert recruitment and candidate matching system.",
                        prompt=prompt,
                        response_model=MatchScoreOutput,
                        cache_ttl_seconds=86400 * 30,  # 30 days
                    )
                    # Cache in redis
                    await redis.set(
                        cache_key,
                        match_out.model_dump_json(),
                        ex=86400 * 30,
                    )
                except Exception as e:
                    logger.warning("Gemini scoring failed for job %s: %s", job.id, e)
                    # Graceful deterministic fallback
                    score = int(v_score * 100)
                    decision: Literal["apply", "maybe", "skip"] = (
                        "apply" if score >= preferences.min_match_score else "maybe"
                    )
                    match_out = MatchScoreOutput(
                        job_id=str(job.id),
                        match_score=score,
                        decision=decision,
                        fit_reasons=["Relevant experience", "Core skill alignment"],
                        gaps=[],
                        resume_focus=["Recent impact metrics"],
                        risk_flags=[],
                    )

            # Persist JobMatch
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
