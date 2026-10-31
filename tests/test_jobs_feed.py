"""Jobs feed: "Matched for you" lists only this user's matches; saving or rating an unmatched job works."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from packages.core.database import async_session_maker
from packages.core.models.jobs import Company, Job
from packages.core.models.matching import JobMatch
from packages.core.services.profile import current_profile_version


async def _setup(uid: str) -> dict[str, uuid.UUID]:
    now = datetime.now(UTC)
    async with async_session_maker() as db:
        name = f"Feed Co {uuid.uuid4().hex[:6]}"
        company = Company(name=name, normalized_name=name.lower(), ats_type="greenhouse")
        db.add(company)
        await db.flush()
        ids: dict[str, uuid.UUID] = {}
        for i, key in enumerate(["matched", "filtered_out", "dismissed", "unscored"]):
            job = Job(company_id=company.id, title=f"Backend {key}", normalized_title="backend", source="greenhouse",
                      external_id=uuid.uuid4().hex, application_url=f"https://boards.greenhouse.io/x/jobs/{uuid.uuid4().hex}",
                      ats_type="greenhouse", content_hash=uuid.uuid4().hex,
                      posted_at=datetime(2100, 1, 1, tzinfo=UTC) + timedelta(seconds=now.timestamp() + i), first_seen_at=now, last_seen_at=now)
            db.add(job)
            await db.flush()
            ids[key] = job.id
        version = await current_profile_version(db, uid)
        for key, passed, status in [("matched", True, "new"), ("filtered_out", False, "new"), ("dismissed", True, "dismissed")]:
            db.add(JobMatch(user_id=uid, job_id=ids[key], profile_version_id=version.id, filter_passed=passed,
                            match_score=80, decision="apply", status=status))
        await db.commit()
    return ids


async def test_matched_only_feed_lists_only_this_users_matches(client: AsyncClient) -> None:
    uid = f"feed-{uuid.uuid4().hex[:8]}"
    ids = await _setup(uid)
    h = {"X-Dev-User-Id": uid}

    matched = (await client.get("/v1/jobs", params={"matched_only": True, "limit": 100}, headers=h)).json()["items"]
    titles = {j["title"] for j in matched}
    assert "Backend matched" in titles
    assert not titles & {"Backend filtered_out", "Backend dismissed", "Backend unscored"}

    everything = (await client.get("/v1/jobs", params={"limit": 100}, headers=h)).json()["items"]
    assert str(ids["unscored"]) in {j["id"] for j in everything}


async def test_save_and_feedback_on_unmatched_job(client: AsyncClient) -> None:
    uid = f"feed-{uuid.uuid4().hex[:8]}"
    ids = await _setup(uid)
    h = {"X-Dev-User-Id": uid}

    r = await client.post(f"/v1/jobs/{ids['unscored']}/save", headers=h)
    assert r.status_code == 200, r.text
    other = f"feed-{uuid.uuid4().hex[:8]}"
    r = await client.post(f"/v1/jobs/{ids['unscored']}/feedback", json={"feedback": "dismissed"}, headers={"X-Dev-User-Id": other})
    assert r.status_code == 200, r.text
    async with async_session_maker() as db:
        rows = (await db.execute(select(JobMatch.user_id, JobMatch.status).where(JobMatch.job_id == ids["unscored"]))).all()
    assert sorted(rows) == sorted([(uid, "saved"), (other, "dismissed")])
