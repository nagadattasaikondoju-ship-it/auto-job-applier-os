"""Job discovery orchestration: crawl due company boards and Adzuna, then re-run matching.

Used by the Celery beat schedule (all users) and by "Find jobs now" (one user).
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select

from packages.core.database import async_session_maker
from packages.core.models.jobs import Company
from packages.core.models.preferences import JobPreference
from packages.core.services.jobs import ingest_normalized_job
from packages.core.services.matching import run_matching_funnel_for_user
from packages.jobs_sources.adzuna import AdzunaConnector
from packages.jobs_sources.ashby import AshbyBoardConnector
from packages.jobs_sources.greenhouse import GreenhouseBoardConnector
from packages.jobs_sources.lever import LeverPostingsConnector

logger = logging.getLogger("applyon.discovery")

_BOARD_CONNECTORS = {"greenhouse", "lever", "ashby"}


def _connector_for(company: Company) -> Any:
    token = company.ats_board_token or ""
    if company.ats_type == "greenhouse":
        return GreenhouseBoardConnector(board_token=token, company_name=company.name)
    if company.ats_type == "lever":
        return LeverPostingsConnector(company_id=token, company_name=company.name)
    return AshbyBoardConnector(board_token=token, company_name=company.name)


async def _ingest(connector: Any) -> int:
    raw_jobs = await connector.fetch()
    new = 0
    async with async_session_maker() as session:
        for raw in raw_jobs:
            _, is_new = await ingest_normalized_job(session=session, job_in=connector.normalize(raw))
            new += int(is_new)
        await session.commit()
    return new


async def crawl_due_companies(limit: int = 25) -> dict[str, int]:
    """Crawl public ATS boards whose crawl interval has elapsed."""
    now = datetime.now(UTC)
    async with async_session_maker() as session:
        companies = (
            await session.execute(
                select(Company)
                .where(
                    Company.is_active.is_(True),
                    Company.ats_type.in_(_BOARD_CONNECTORS),
                    Company.ats_board_token.is_not(None),
                    or_(
                        Company.last_crawled_at.is_(None),
                        Company.last_crawled_at < now - timedelta(minutes=30),
                    ),
                )
                .order_by(Company.last_crawled_at.asc().nulls_first())
                .limit(limit)
            )
        ).scalars().all()

        crawled = new_jobs = 0
        for company in companies:
            if company.last_crawled_at and company.last_crawled_at > now - timedelta(
                minutes=company.crawl_interval_minutes
            ):
                continue
            try:
                new_jobs += await _ingest(_connector_for(company))
                company.failure_count = 0
            except Exception as e:  # one bad board must not stop the rest
                logger.warning("Crawl failed for %s: %s", company.name, e)
                company.failure_count += 1
                if company.failure_count >= 5:
                    company.is_active = False
            company.last_crawled_at = now
            crawled += 1
        await session.commit()
    return {"companies_crawled": crawled, "new_jobs": new_jobs}


async def crawl_adzuna_for_preferences(user_ids: list[str] | None = None, max_pairs: int = 20) -> dict[str, int]:
    """Search Adzuna for each distinct (target role, city) pair across users' preferences."""
    async with async_session_maker() as session:
        stmt = select(JobPreference)
        if user_ids:
            stmt = stmt.where(JobPreference.user_id.in_(user_ids))
        prefs = (await session.execute(stmt)).scalars().all()

    pairs: list[tuple[str, str]] = []
    for p in prefs:
        cities = [c for c in (p.locations or []) if c.lower() != "remote"] or ["India"]
        for role in p.target_roles or []:
            for city in cities[:3]:
                if (role, city) not in pairs:
                    pairs.append((role, city))

    new_jobs = 0
    for role, city in pairs[:max_pairs]:
        try:
            new_jobs += await _ingest(AdzunaConnector(keywords=role, city=city))
        except Exception as e:
            logger.warning("Adzuna search failed for %s / %s: %s", role, city, e)
    return {"searches": min(len(pairs), max_pairs), "new_jobs": new_jobs}


async def match_users(user_ids: list[str] | None = None) -> dict[str, int]:
    async with async_session_maker() as session:
        stmt = select(JobPreference.user_id)
        if user_ids:
            stmt = stmt.where(JobPreference.user_id.in_(user_ids))
        ids = list((await session.execute(stmt)).scalars().all())
    total = 0
    for uid in ids:
        try:
            async with async_session_maker() as session:
                total += len(await run_matching_funnel_for_user(session=session, user_id=uid))
        except Exception as e:
            logger.warning("Matching failed for %s: %s", uid, e)
    return {"users": len(ids), "new_matches": total}


async def discover_for_user(user_id: str) -> dict[str, Any]:
    """'Find jobs now': search this user's roles/cities, crawl due boards, then match."""
    adzuna = await crawl_adzuna_for_preferences([user_id], max_pairs=6)
    boards = await crawl_due_companies(limit=10)
    matched = await match_users([user_id])
    return {**adzuna, **boards, **matched}
