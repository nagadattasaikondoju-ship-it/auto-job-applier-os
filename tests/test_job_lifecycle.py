"""Closed jobs: board mark-and-sweep, stale expiry, and pulling back applications waiting on them."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from packages.core.database import async_session_maker
from packages.core.models.applications import Application, ApplicationEvent
from packages.core.models.jobs import Company, Job
from packages.core.services import discovery
from packages.core.services.job_lifecycle import CLOSED_REASON, expire_stale_jobs, sweep_board
from packages.jobs_sources.base import RawJob
from packages.jobs_sources.greenhouse import GreenhouseBoardConnector


async def _company() -> Company:
    async with async_session_maker() as db:
        name = f"Lifecycle {uuid.uuid4().hex[:6]}"
        c = Company(name=name, normalized_name=name.lower(),
                    ats_type="greenhouse", ats_board_token="lc")
        db.add(c)
        await db.commit()
        return c


async def _jobs(company: Company, n: int, source: str = "greenhouse", seen_days_ago: float = 0) -> list[uuid.UUID]:
    seen = datetime.now(UTC) - timedelta(days=seen_days_ago)
    async with async_session_maker() as db:
        jobs = [
            Job(company_id=company.id, title=f"Analyst {i}", normalized_title="analyst", source=source,
                external_id=uuid.uuid4().hex, application_url=f"https://boards.greenhouse.io/lc/jobs/{uuid.uuid4().hex}",
                ats_type="greenhouse", content_hash=uuid.uuid4().hex, last_seen_at=seen, first_seen_at=seen)
            for i in range(n)
        ]
        db.add_all(jobs)
        await db.commit()
        return [j.id for j in jobs]


async def _application(job_id: uuid.UUID, status: str = "ready_for_review") -> uuid.UUID:
    async with async_session_maker() as db:
        a = Application(user_id=f"lc-{uuid.uuid4().hex[:6]}", job_id=job_id, status=status, channel="assisted",
                        application_url="https://example.com", notes=json.dumps({"fields": []}))
        db.add(a)
        await db.commit()
        return a.id


async def _active(job_ids: list[uuid.UUID]) -> list[bool]:
    async with async_session_maker() as db:
        rows = dict((await db.execute(select(Job.id, Job.is_active).where(Job.id.in_(job_ids)))).all())
        return [rows[j] for j in job_ids]


async def test_sweep_closes_missing_postings_and_flags_applications() -> None:
    company = await _company()
    ids = await _jobs(company, 4)
    waiting = await _application(ids[3])
    sent = await _application(ids[3], status="submitted")
    async with async_session_maker() as db:
        closed = await sweep_board(db, company.id, "greenhouse", set(ids[:3]))
        await db.commit()
    assert closed == 1 and await _active(ids) == [True, True, True, False]
    async with async_session_maker() as db:
        a = await db.get(Application, waiting)
        assert a is not None and a.status == "needs_user_action" and a.failure_reason == CLOSED_REASON
        ev = (await db.execute(select(ApplicationEvent).where(ApplicationEvent.application_id == waiting))).scalars().all()
        assert [e.type for e in ev] == ["job_closed"]
        done = await db.get(Application, sent)
        assert done is not None and done.status == "submitted"  # already sent: untouched


async def test_sweep_ignores_empty_and_partial_responses() -> None:
    company = await _company()
    ids = await _jobs(company, 12)
    async with async_session_maker() as db:
        assert await sweep_board(db, company.id, "greenhouse", set()) == 0          # fetch error looks empty
        assert await sweep_board(db, company.id, "greenhouse", set(ids[:2])) == 0   # 2 of 12: truncated
        await db.commit()
    assert all(await _active(ids))


async def test_stale_expiry_by_source() -> None:
    company = await _company()
    board_stale = await _jobs(company, 1, "greenhouse", seen_days_ago=15)
    agg_recent = await _jobs(company, 1, "jsearch", seen_days_ago=10)
    agg_stale = await _jobs(company, 1, "linkedin", seen_days_ago=22)
    async with async_session_maker() as db:
        await expire_stale_jobs(db)
        await db.commit()
    assert await _active(board_stale + agg_recent + agg_stale) == [False, True, False]


async def test_board_ingest_closes_removed_posting(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    company = await _company()
    connector = GreenhouseBoardConnector(board_token="lc", company_name=company.name)

    def raw(i: int) -> RawJob:
        return RawJob(source="greenhouse", external_id=f"lc-{i}-{company.id}", company_name=company.name,
                      title=f"Data Analyst {i}", location_raw="Bengaluru", application_url=f"https://boards.greenhouse.io/lc/jobs/{i}{company.id.hex[:6]}",
                      description_raw="<p>SQL</p>")

    async def fetch_three(*_: Any, **__: Any) -> list[RawJob]:
        return [raw(1), raw(2), raw(3)]

    async def fetch_two(*_: Any, **__: Any) -> list[RawJob]:
        return [raw(1), raw(2)]

    monkeypatch.setattr(connector, "fetch", fetch_three)
    await discovery._ingest(connector, board_company=company)
    monkeypatch.setattr(connector, "fetch", fetch_two)
    await discovery._ingest(connector, board_company=company)
    async with async_session_maker() as db:
        rows = (await db.execute(select(Job.title, Job.is_active).where(Job.company_id == company.id))).all()
    assert sorted(rows) == [("Data Analyst 1", True), ("Data Analyst 2", True), ("Data Analyst 3", False)]


async def test_board_ingest_keeps_only_postings_open_to_india(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    company = await _company()
    connector = GreenhouseBoardConnector(board_token="lc", company_name=company.name)
    places = ["Bengaluru, India", "Remote - India", "Remote", "San Francisco, California", "Remote - USA", "Bangkok"]

    async def fetch(*_: Any, **__: Any) -> list[RawJob]:
        return [
            RawJob(source="greenhouse", external_id=f"in-{i}-{company.id}", company_name=company.name,
                   title=f"Engineer {i}", location_raw=loc,
                   application_url=f"https://boards.greenhouse.io/lc/jobs/9{i}{company.id.hex[:6]}", description_raw="<p>Go</p>")
            for i, loc in enumerate(places)
        ]

    monkeypatch.setattr(connector, "fetch", fetch)
    await discovery._ingest(connector, board_company=company)
    async with async_session_maker() as db:
        stored = sorted((await db.execute(select(Job.location_raw).where(Job.company_id == company.id))).scalars())
    assert stored == ["Bengaluru, India", "Remote", "Remote - India"]


def test_india_relevance_on_real_board_locations() -> None:
    from packages.core.services.match_rules import is_india_relevant

    for loc in ["Bengaluru, India", "Noida, Uttar Pradesh", "IN-Pune", "Gurugram", "India (Remote)", "APAC", "Remote"]:
        assert is_india_relevant(loc, "onsite" if "Remote" not in loc and loc != "APAC" else "remote"), loc
    for loc in ["United States", "Remote - USA", "London, United Kingdom", "Tokyo, Japan", "Bangkok", "Singapore", "N/A"]:
        assert not is_india_relevant(loc, "remote" if "Remote" in loc else "onsite"), loc
