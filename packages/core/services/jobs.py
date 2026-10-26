"""Job management service: ingestion, deduplication, preference buckets, and feed querying."""

from datetime import datetime
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai.client import gemini_client
from packages.core.models.jobs import Company, Job, JobEmbedding, PreferenceBucket
from packages.core.models.matching import JobMatch
from packages.jobs_sources.base import JobIn


def compute_preference_bucket_keys(
    role: str,
    seniority: str,
    locations: list[str],
    is_remote: bool = False,
) -> list[str]:
    """Generate set of bucket keys for indexed fast candidate discovery."""
    role_token = role.lower().replace(" ", "_").strip()
    seniority_token = seniority.lower().strip()
    keys: list[str] = []

    if is_remote:
        keys.append(f"{role_token}:{seniority_token}:remote")

    for loc in locations:
        loc_token = loc.lower().replace(" ", "_").strip()
        keys.append(f"{role_token}:{seniority_token}:{loc_token}")

    if not keys:
        keys.append(f"{role_token}:{seniority_token}:all")

    return keys


async def get_or_create_company(
    session: AsyncSession,
    name: str,
    ats_type: str = "unknown",
    board_token: str | None = None,
) -> Company:
    """Find existing company by normalized name or create a new record."""
    norm_name = name.lower().strip()
    stmt = select(Company).where(Company.normalized_name == norm_name)
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        if ats_type != "unknown" and existing.ats_type == "unknown":
            existing.ats_type = ats_type
        if board_token and not existing.ats_board_token:
            existing.ats_board_token = board_token
        return existing

    company = Company(
        name=name,
        normalized_name=norm_name,
        domain=f"{norm_name.replace(' ', '')}.com",
        ats_type=ats_type,
        ats_board_token=board_token,
    )
    session.add(company)
    await session.flush()
    return company


async def ingest_normalized_job(
    session: AsyncSession,
    job_in: JobIn,
) -> tuple[Job, bool]:
    """Ingest, deduplicate, embed, and index a single normalized job.

    Returns (job, is_new).
    """
    now = datetime.utcnow()

    # Check for existing job by content hash
    stmt = select(Job).where(Job.content_hash == job_in.content_hash)
    res = await session.execute(stmt)
    existing_job = res.scalar_one_or_none()

    if existing_job:
        existing_job.last_seen_at = now
        existing_job.is_active = True
        # Pick up cleaner text from parser fixes and edits the employer made to the posting
        if job_in.description_text and job_in.description_text != existing_job.description_text:
            existing_job.description_text = job_in.description_text
        return existing_job, False

    # Lookup or create company
    company = await get_or_create_company(
        session=session,
        name=job_in.company_name,
        ats_type=job_in.ats_type,
        board_token=job_in.ats_board_token,
    )

    new_job = Job(
        source=job_in.source,
        external_id=job_in.external_id,
        company_id=company.id,
        title=job_in.title,
        normalized_title=job_in.normalized_title,
        seniority=job_in.seniority,
        location_raw=job_in.location_raw,
        locations=job_in.locations,
        country=job_in.country,
        remote_mode=job_in.remote_mode,
        employment_type=job_in.employment_type,
        description_html=job_in.description_html,
        description_text=job_in.description_text,
        salary_min_lpa=job_in.salary_min_lpa,
        salary_max_lpa=job_in.salary_max_lpa,
        salary_currency=job_in.salary_currency,
        experience_min=job_in.experience_min,
        experience_max=job_in.experience_max,
        required_skills=job_in.required_skills,
        application_url=job_in.application_url,
        ats_type=job_in.ats_type,
        posted_at=job_in.posted_at or now,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
        content_hash=job_in.content_hash,
        quality_score=job_in.quality_score,
        is_suspicious=job_in.is_suspicious,
    )
    session.add(new_job)
    await session.flush()

    # Generate 768-dim embedding
    embed_text = f"{new_job.title} at {job_in.company_name}. {new_job.description_text[:600]}"
    vector = await gemini_client.get_embedding(embed_text)

    embedding_record = JobEmbedding(
        job_id=new_job.id,
        embedding=vector,
    )
    session.add(embedding_record)

    return new_job, True


async def assign_user_to_preference_buckets(
    session: AsyncSession,
    user_id: str,
    roles: list[str],
    seniority: str,
    locations: list[str],
    allows_remote: bool,
) -> None:
    """Register user in targeted preference buckets for high-speed matching."""
    # Clear old buckets
    del_stmt = select(PreferenceBucket).where(PreferenceBucket.user_id == user_id)
    old_buckets = (await session.execute(del_stmt)).scalars().all()
    for b in old_buckets:
        await session.delete(b)

    for role in roles:
        bucket_keys = compute_preference_bucket_keys(
            role=role,
            seniority=seniority,
            locations=locations,
            is_remote=allows_remote,
        )
        for key in bucket_keys:
            session.add(PreferenceBucket(bucket_key=key, user_id=user_id))

    await session.flush()


async def get_jobs_feed(
    session: AsyncSession,
    user_id: str,
    cursor: datetime | None = None,
    limit: int = 20,
    min_match_score: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve keyset-paginated jobs feed for user with match scores."""
    stmt = (
        select(Job, JobMatch, Company.name.label("company_name"))
        .join(Company, Job.company_id == Company.id)
        .outerjoin(
            JobMatch,
            (JobMatch.job_id == Job.id) & (JobMatch.user_id == user_id),
        )
        .where(
            Job.is_active.is_(True),
            Job.is_suspicious.is_(False),
        )
    )

    if cursor:
        stmt = stmt.where(Job.posted_at < cursor)

    if min_match_score is not None:
        stmt = stmt.where(
            or_(
                JobMatch.match_score >= min_match_score,
                JobMatch.match_score.is_(None),
            )
        )

    stmt = stmt.order_by(desc(Job.posted_at), desc(Job.id)).limit(limit)
    res = await session.execute(stmt)

    feed = []
    for job, match, company_name in res.all():
        feed.append(
            {
                "id": str(job.id),
                "title": job.title,
                "company": company_name,
                "location": job.location_raw
                or (", ".join(job.locations) if job.locations else "India"),
                "locations": job.locations,
                "remote_mode": job.remote_mode,
                "employment_type": job.employment_type,
                "experience_range": f"{job.experience_min}-{job.experience_max} yrs",
                "salary_min_lpa": job.salary_min_lpa,
                "salary_max_lpa": job.salary_max_lpa,
                "required_skills": job.required_skills,
                "application_url": job.application_url,
                "ats_type": job.ats_type,
                "posted_at": job.posted_at.isoformat() if job.posted_at else None,
                "match": (
                    {
                        "score": match.match_score,
                        "decision": match.decision,
                        "fit_reasons": match.fit_reasons,
                        "gaps": match.gaps,
                        "status": match.status,
                        "user_feedback": match.user_feedback,
                    }
                    if match
                    else None
                ),
            }
        )

    return feed
