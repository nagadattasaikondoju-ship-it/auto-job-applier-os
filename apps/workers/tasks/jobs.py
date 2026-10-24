"""Celery tasks for job board crawling, ingestion, and matching."""

import logging
import uuid
from typing import Any

from apps.workers.celery_app import celery_app
from packages.core.async_utils import run_async
from packages.core.database import async_session_maker
from packages.core.services.jobs import ingest_normalized_job
from packages.core.services.matching import run_matching_funnel_for_user
from packages.jobs_sources.adzuna import AdzunaConnector
from packages.jobs_sources.ashby import AshbyBoardConnector
from packages.jobs_sources.greenhouse import GreenhouseBoardConnector
from packages.jobs_sources.lever import LeverPostingsConnector

logger = logging.getLogger("applyon.workers.jobs")


async def _async_crawl_greenhouse(
    board_token: str, company_name: str | None = None
) -> dict[str, Any]:
    connector = GreenhouseBoardConnector(board_token=board_token, company_name=company_name)
    raw_jobs = await connector.fetch()
    ingested_count = 0
    new_count = 0

    async with async_session_maker() as session:
        for raw in raw_jobs:
            normalized = connector.normalize(raw)
            _, is_new = await ingest_normalized_job(session=session, job_in=normalized)
            ingested_count += 1
            if is_new:
                new_count += 1
        await session.commit()

    return {"board": board_token, "ingested": ingested_count, "new": new_count}


async def _async_crawl_lever(company_id: str, company_name: str | None = None) -> dict[str, Any]:
    connector = LeverPostingsConnector(company_id=company_id, company_name=company_name)
    raw_jobs = await connector.fetch()
    ingested_count = 0
    new_count = 0

    async with async_session_maker() as session:
        for raw in raw_jobs:
            normalized = connector.normalize(raw)
            _, is_new = await ingest_normalized_job(session=session, job_in=normalized)
            ingested_count += 1
            if is_new:
                new_count += 1
        await session.commit()

    return {"company": company_id, "ingested": ingested_count, "new": new_count}


async def _async_crawl_ashby(board_token: str, company_name: str | None = None) -> dict[str, Any]:
    connector = AshbyBoardConnector(board_token=board_token, company_name=company_name)
    raw_jobs = await connector.fetch()
    ingested_count = 0
    new_count = 0

    async with async_session_maker() as session:
        for raw in raw_jobs:
            normalized = connector.normalize(raw)
            _, is_new = await ingest_normalized_job(session=session, job_in=normalized)
            ingested_count += 1
            if is_new:
                new_count += 1
        await session.commit()

    return {"board": board_token, "ingested": ingested_count, "new": new_count}


async def _async_crawl_adzuna(keywords: str, city: str) -> dict[str, Any]:
    connector = AdzunaConnector(keywords=keywords, city=city)
    raw_jobs = await connector.fetch()
    ingested_count = 0
    new_count = 0

    async with async_session_maker() as session:
        for raw in raw_jobs:
            normalized = connector.normalize(raw)
            _, is_new = await ingest_normalized_job(session=session, job_in=normalized)
            ingested_count += 1
            if is_new:
                new_count += 1
        await session.commit()

    return {"keywords": keywords, "city": city, "ingested": ingested_count, "new": new_count}


async def _async_match_user_jobs(user_id_str: str) -> dict[str, Any]:
    user_id = uuid.UUID(user_id_str)
    async with async_session_maker() as session:
        matches = await run_matching_funnel_for_user(session=session, user_id=user_id)
        return {"user_id": user_id_str, "matches_count": len(matches)}


@celery_app.task(name="jobs.crawl_greenhouse", queue="job_ingestion")
def crawl_greenhouse_board(board_token: str, company_name: str | None = None) -> dict[str, Any]:
    return run_async(_async_crawl_greenhouse(board_token=board_token, company_name=company_name))


@celery_app.task(name="jobs.crawl_lever", queue="job_ingestion")
def crawl_lever_company(company_id: str, company_name: str | None = None) -> dict[str, Any]:
    return run_async(_async_crawl_lever(company_id=company_id, company_name=company_name))


@celery_app.task(name="jobs.crawl_ashby", queue="job_ingestion")
def crawl_ashby_board(board_token: str, company_name: str | None = None) -> dict[str, Any]:
    return run_async(_async_crawl_ashby(board_token=board_token, company_name=company_name))


@celery_app.task(name="jobs.crawl_adzuna", queue="job_ingestion")
def crawl_adzuna_feed(keywords: str, city: str) -> dict[str, Any]:
    return run_async(_async_crawl_adzuna(keywords=keywords, city=city))


@celery_app.task(name="jobs.match_user", queue="ai_matching")
def match_user_jobs(user_id: str) -> dict[str, Any]:
    return run_async(_async_match_user_jobs(user_id_str=user_id))
