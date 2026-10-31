"""Closing jobs that employers removed, so nobody prepares or submits an application to a dead posting.

- Company boards (Greenhouse, Lever, Ashby): after a fetch that returned jobs, postings from that board
  missing from the response are closed (mark and sweep). Skipped when the response looks truncated.
- Anything not seen for a while is closed by a daily sweep: 14 days for boards (covers boards that
  started failing or emptied out), 21 days for aggregator results (JSearch, Indeed, LinkedIn, ...).
- Applications still waiting on such a job move to needs_user_action with a plain reason.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.applications import Application, ApplicationEvent
from packages.core.models.jobs import Job

logger = logging.getLogger("applyon.job_lifecycle")

BOARD_SOURCES = ("greenhouse", "lever", "ashby")
BOARD_STALE_AFTER = timedelta(days=14)
AGGREGATOR_STALE_AFTER = timedelta(days=21)
# A response with fewer than this share of the board's open jobs is treated as partial, not as closures
MIN_COMPLETE_SHARE = 0.5

# Applications not yet submitted that a closed job should pull back
_WAITING = ("draft", "preparing", "ready_for_review", "approved", "needs_user_action")
CLOSED_REASON = "This job was closed or removed by the employer, so it can't be applied to any more. Nothing was submitted."


async def close_jobs(session: AsyncSession, job_ids: list[uuid.UUID]) -> int:
    """Close the given jobs and pull back applications still waiting on them. Returns jobs closed."""
    if not job_ids:
        return 0
    result = await session.execute(
        update(Job).where(Job.id.in_(job_ids), Job.is_active.is_(True)).values(is_active=False).returning(Job.id)
    )
    closed = [row[0] for row in result.all()]
    if not closed:
        return 0
    apps = (
        await session.execute(select(Application).where(Application.job_id.in_(closed), Application.status.in_(_WAITING)))
    ).scalars().all()
    now = datetime.now(UTC)
    for app in apps:
        old = app.status
        app.status = "needs_user_action"
        app.failure_reason = CLOSED_REASON
        session.add(
            ApplicationEvent(
                id=uuid.uuid4(),
                application_id=app.id,
                type="job_closed",
                payload={"from_status": old, "reason": CLOSED_REASON},
                actor="system",
                created_at=now,
            )
        )
    logger.info("Closed %d jobs; %d waiting applications flagged", len(closed), len(apps))
    return len(closed)


async def sweep_board(
    session: AsyncSession, company_id: uuid.UUID, source: str, seen_job_ids: set[uuid.UUID]
) -> int:
    """After a board fetch that returned jobs, close that board's open postings missing from it."""
    if not seen_job_ids:
        return 0  # connectors return [] on errors too: never read an empty response as "all closed"
    open_ids = set(
        (
            await session.execute(
                select(Job.id).where(Job.company_id == company_id, Job.source == source, Job.is_active.is_(True))
            )
        ).scalars()
    )
    if len(open_ids) > 10 and len(seen_job_ids & open_ids) < MIN_COMPLETE_SHARE * len(open_ids):
        logger.warning(
            "Skipping sweep for company %s (%s): saw %d of %d open jobs, response looks partial",
            company_id, source, len(seen_job_ids & open_ids), len(open_ids),
        )
        return 0
    return await close_jobs(session, list(open_ids - seen_job_ids))


async def expire_stale_jobs(session: AsyncSession, now: datetime | None = None) -> dict[str, int]:
    """Daily: close postings we haven't seen again for a while."""
    now = now or datetime.now(UTC)
    board_ids = (
        await session.execute(
            select(Job.id).where(
                and_(Job.is_active.is_(True), Job.source.in_(BOARD_SOURCES), Job.last_seen_at < now - BOARD_STALE_AFTER)
            )
        )
    ).scalars().all()
    aggregator_ids = (
        await session.execute(
            select(Job.id).where(
                and_(
                    Job.is_active.is_(True),
                    Job.source.not_in(BOARD_SOURCES),
                    Job.last_seen_at < now - AGGREGATOR_STALE_AFTER,
                )
            )
        )
    ).scalars().all()
    return {
        "board_jobs_closed": await close_jobs(session, list(board_ids)),
        "aggregator_jobs_closed": await close_jobs(session, list(aggregator_ids)),
    }
