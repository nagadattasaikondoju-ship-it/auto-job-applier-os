"""Gemini scoring is capped per user per day; matches beyond the cap still get rule-based scores."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, PropertyMock, patch

from packages.ai.client import GeminiClient
from packages.ai.schemas import MatchScoreOutput
from packages.core.config import settings
from packages.core.database import async_session_maker
from packages.core.models.jobs import Company, Job
from packages.core.models.preferences import JobPreference
from packages.core.models.profile import Profile
from packages.core.services.matching import run_matching_funnel_for_user

ROLE = f"Zyxtronics Analyst {uuid.uuid4().hex[:6]}"  # unique, so other tests' jobs don't match


async def _seed(user_id: str, jobs: int) -> None:
    async with async_session_maker() as db:
        if not await db.get(Profile, user_id):
            db.add(Profile(user_id=user_id, full_name="Ravi Kumar", email="ravi@example.com", total_experience_months=36))
            db.add(JobPreference(user_id=user_id, target_roles=[ROLE], locations=["Bengaluru"],
                                 remote_mode=["onsite", "hybrid", "remote"], seniority="mid", min_exp=3, max_exp=6))
        company = Company(name=f"Co {uuid.uuid4().hex[:6]}", normalized_name=uuid.uuid4().hex)
        db.add(company)
        await db.flush()
        for _ in range(jobs):
            db.add(Job(
                company_id=company.id, title=ROLE, normalized_title=ROLE.lower(), source="greenhouse",
                external_id=uuid.uuid4().hex, application_url=f"https://boards.greenhouse.io/x/jobs/{uuid.uuid4().hex}",
                ats_type="greenhouse", description_text="SQL, Python, Power BI.", content_hash=uuid.uuid4().hex,
                location_raw="Bengaluru, India", locations=["Bengaluru"], remote_mode="hybrid",
                experience_min=2, experience_max=5, required_skills=["SQL", "Python"], posted_at=datetime.now(UTC),
            ))
        await db.commit()


def _fake_score(**kwargs):  # type: ignore[no-untyped-def]
    job_id = kwargs["prompt"].split("job_id ")[1].split(")")[0]
    return MatchScoreOutput(job_id=job_id, match_score=80, decision="apply", fit_reasons=["SQL"], gaps=[],
                            resume_focus=[], risk_flags=[])


async def test_ai_scoring_respects_daily_budget(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    user = f"budget-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(settings, "ai_match_daily_budget", 3)
    await _seed(user, jobs=12)
    with (
        patch.object(GeminiClient, "is_mock", new_callable=PropertyMock, return_value=False),
        patch("packages.core.services.matching.gemini_client.generate_structured", new=AsyncMock(side_effect=_fake_score)) as gen,
    ):
        async with async_session_maker() as db:
            first = await run_matching_funnel_for_user(db, user)
        assert gen.await_count == 3, gen.await_count
        assert len(first) == 12  # every candidate still gets a (rule-based) score

        await _seed(user, jobs=5)  # new jobs later the same day
        async with async_session_maker() as db:
            second = await run_matching_funnel_for_user(db, user)
        assert gen.await_count == 3  # budget used up: no more Gemini calls today
        assert len(second) == 5
