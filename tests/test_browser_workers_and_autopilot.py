"""Unit and integration tests for Phase 9: Browser Workers & Autopilot."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.browser.adapters import get_adapter
from apps.browser.executor import BrowserAutomationExecutor
from packages.core.models.applications import Campaign
from packages.core.models.jobs import Job
from packages.core.models.matching import JobMatch
from packages.core.models.platform import Consent
from packages.core.models.profile import Experience, Profile
from packages.core.services.autopilot import AutopilotService


@pytest.mark.asyncio
async def test_blocker_detection_and_section0_compliance():
    """Verify Section 0 rule: Zero bypass of CAPTCHA/anti-bot challenges."""
    adapter = get_adapter("greenhouse")

    html_captcha = (
        "<html><body>Please solve the recaptcha to continue <div class='g-recaptcha'></div></body></html>"
    )
    blocker = adapter.detect_blockers(html_captcha, "https://boards.greenhouse.io/test/jobs/123")
    assert blocker == "captcha_detected"

    html_cloudflare = (
        "<html><title>Just a moment...</title><body><div id='cf-turnstile'></div></body></html>"
    )
    blocker_cf = adapter.detect_blockers(html_cloudflare, "https://boards.greenhouse.io/test/jobs/123")
    assert blocker_cf in ["captcha_detected", "anti_bot_challenge"]

    # Executor should stop and return needs_user_action
    executor = BrowserAutomationExecutor()
    result = await executor.execute_application(
        application_id=uuid.uuid4(),
        application_url="https://boards.greenhouse.io/test/jobs/123",
        ats_type="greenhouse",
        fields=[{"canonical_key": "first_name", "value": "Aarav"}],
        html_content=html_captcha,
    )

    assert result.success is False
    assert result.status == "needs_user_action"
    assert result.blocker_detected == "captcha_detected"


@pytest.mark.asyncio
async def test_browser_executor_success_and_dry_run():
    """Test successful form filling in simulated / headless mode."""
    executor = BrowserAutomationExecutor()
    clean_html = "<html><form><input id='first_name'><button type='submit'>Apply</button></form></html>"

    # Dry run
    res_dry = await executor.execute_application(
        application_id=uuid.uuid4(),
        application_url="https://boards.greenhouse.io/test/jobs/123",
        ats_type="greenhouse",
        fields=[{"canonical_key": "first_name", "value": "Aarav"}],
        dry_run=True,
        html_content=clean_html,
    )
    assert res_dry.success is True
    assert res_dry.status == "ready_for_review"
    assert res_dry.fields_filled == 1

    # Live submit mode
    res_submit = await executor.execute_application(
        application_id=uuid.uuid4(),
        application_url="https://boards.greenhouse.io/test/jobs/123",
        ats_type="greenhouse",
        fields=[{"canonical_key": "first_name", "value": "Aarav"}],
        dry_run=False,
        html_content=clean_html,
    )
    assert res_submit.success is True
    assert res_submit.status == "submitted"


@pytest.mark.asyncio
async def test_can_run_autopilot_guards():
    """Test safety guards: profile completeness, DPDP consent, campaign status, and circuit breaker."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    mock_db = AsyncMock()

    # 1. No profile -> fails
    res_empty = MagicMock()
    res_empty.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = res_empty

    can_run, reason, _ = await AutopilotService.can_run_autopilot(mock_db, user_id)
    assert can_run is False
    assert "Profile does not exist" in reason

    # 2. Incomplete profile (<80 score) -> fails
    incomplete_profile = Profile(
        user_id=user_id,
        full_name="Aarav Sharma",
        email="aarav@example.com",
        phone="+919876543210",
        city="Bengaluru",
        state="Karnataka",
        country="India",
        pincode="560001",
        headline="Software Engineer",
        summary="Backend developer",
    )
    res_prof = MagicMock()
    res_prof.scalar_one_or_none.return_value = incomplete_profile
    res_empty_list = MagicMock()
    res_empty_list.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [res_prof, res_empty_list, res_empty_list, res_empty_list]
    can_run, reason, _ = await AutopilotService.can_run_autopilot(mock_db, user_id)
    assert can_run is False
    assert "Minimum 80 required" in reason

    # 3. Complete profile (80+), but no DPDP consent -> fails
    complete_profile = Profile(
        user_id=user_id,
        full_name="Aarav Sharma",
        email="aarav@example.com",
        phone="+919876543210",
        city="Bengaluru",
        state="Karnataka",
        country="India",
        pincode="560001",
        headline="Senior Backend Engineer",
        summary="Distributed systems and Python expert",
        current_ctc_lpa=25.0,
        expected_ctc_lpa=35.0,
        notice_period_days=30,
        total_experience_months=48,
        work_authorization={"India": True},
    )
    res_prof_full = MagicMock()
    res_prof_full.scalar_one_or_none.return_value = complete_profile

    exp = Experience(
        id=uuid.uuid4(),
        user_id=user_id,
        company="Tech Corp",
        title="Senior Developer",
        location="Bengaluru",
        is_current=True,
        bullets=["Designed scalable distributed services", "Optimized database performance"],
    )
    res_exp = MagicMock()
    res_exp.scalars.return_value.all.return_value = [exp]

    mock_db.add = MagicMock()

    from packages.core.models.profile import Education

    edu = Education(
        id=uuid.uuid4(),
        user_id=user_id,
        institution="IIT Madras",
        degree="B.Tech",
        field="Computer Science",
    )
    res_edu = MagicMock()
    res_edu.scalars.return_value.all.return_value = [edu]

    res_no_consent = MagicMock()
    res_no_consent.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [
        res_prof_full,
        res_exp,
        res_edu,
        res_empty_list,
        res_no_consent,
    ]
    can_run, reason, _ = await AutopilotService.can_run_autopilot(mock_db, user_id)
    assert can_run is False
    assert "consent for auto_submit" in reason

    # 4. Valid consent, active campaign, valid credits -> passes!
    res_consent = MagicMock()
    res_consent.scalar_one_or_none.return_value = Consent(
        user_id=user_id, purpose="auto_submit", version="v1"
    )

    campaign = Campaign(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Backend Campaign",
        status="active",
        preferences_snapshot={"titles": ["Backend Engineer"]},
    )
    res_camp = MagicMock()
    res_camp.scalar_one_or_none.return_value = campaign

    res_no_recent_failures = MagicMock()
    res_no_recent_failures.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        res_prof_full,
        res_exp,
        res_edu,
        res_empty_list,
        res_consent,
        res_camp,
        res_no_recent_failures,
    ]

    with (
        patch("packages.core.services.credits.CreditsService.check_daily_application_cap", new_callable=AsyncMock) as mock_daily,
        patch("packages.core.services.credits.CreditsService.get_available_balance", new_callable=AsyncMock) as mock_bal,
    ):
        mock_daily.return_value = {"allowed": True, "limit": 10, "used_today": 0, "remaining": 10}
        mock_bal.return_value = 25

        can_run, reason, camp = await AutopilotService.can_run_autopilot(mock_db, user_id)
        assert can_run is True
        assert reason is None
        assert camp.id == campaign.id


@pytest.mark.asyncio
async def test_company_diversification_and_cycle_execution():
    """Verify company diversification limits and full autopilot cycle execution."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    comp_a_id = uuid.uuid4()
    comp_b_id = uuid.uuid4()

    job_a1 = Job(
        id=uuid.uuid4(),
        company_id=comp_a_id,
        title="Frontend Dev 1",
        locations=["Bengaluru"],
        application_url="https://swiggy.careers/1",
        ats_type="greenhouse",
        source="greenhouse",
        content_hash=uuid.uuid4().hex,
    )
    job_a2 = Job(
        id=uuid.uuid4(),
        company_id=comp_a_id,
        title="Frontend Dev 2",
        locations=["Bengaluru"],
        application_url="https://swiggy.careers/2",
        ats_type="greenhouse",
        source="greenhouse",
        content_hash=uuid.uuid4().hex,
    )
    job_b = Job(
        id=uuid.uuid4(),
        company_id=comp_b_id,
        title="Frontend Dev B",
        locations=["Gurugram"],
        application_url="https://zomato.careers/1",
        ats_type="lever",
        source="lever",
        content_hash=uuid.uuid4().hex,
    )

    pv_id = uuid.uuid4()
    match_a1 = JobMatch(
        user_id=user_id,
        job_id=job_a1.id,
        profile_version_id=pv_id,
        match_score=90,
        status="matched",
    )
    match_b = JobMatch(
        user_id=user_id,
        job_id=job_b.id,
        profile_version_id=pv_id,
        match_score=80,
        status="matched",
    )

    mock_db = AsyncMock()

    # Simulate user already has 2 applications to company A in past 7 days
    res_past_apps = MagicMock()
    res_past_apps.scalars.return_value.all.return_value = [job_a1.id, job_a2.id]

    res_past_jobs = MagicMock()
    res_past_jobs.scalars.return_value.all.return_value = [job_a1, job_a2]

    res_matches = MagicMock()
    res_matches.scalars.return_value.all.return_value = [match_a1, match_b]

    res_job_b = MagicMock()
    res_job_b.scalar_one_or_none.return_value = job_b

    # select_next_job_for_autopilot queries:
    # 1. applied_job_ids (res_past_apps)
    # 2. jobs for applied_company_counts (res_past_jobs)
    # 3. matches (res_matches)
    # 4. job_b lookup
    mock_db.execute.side_effect = [res_past_apps, res_past_jobs, res_matches, res_job_b]

    selected_job = await AutopilotService.select_next_job_for_autopilot(mock_db, user_id=user_id)
    assert selected_job is not None
    assert selected_job.id == job_b.id
    assert selected_job.company_id == comp_b_id

    # Test full execute_autopilot_cycle with mocks
    campaign = Campaign(id=uuid.uuid4(), user_id=user_id, status="active", preferences_snapshot={})
    with (
        patch("packages.core.services.autopilot.AutopilotService.can_run_autopilot", new_callable=AsyncMock) as mock_can,
        patch("packages.core.services.autopilot.AutopilotService.select_next_job_for_autopilot", new_callable=AsyncMock) as mock_sel,
        patch("packages.core.services.credits.CreditsService.reserve_hold", new_callable=AsyncMock) as mock_hold,
        patch("apps.workers.tasks.autopilot.execute_browser_application.delay") as mock_delay,
    ):
        mock_can.return_value = (True, None, campaign)
        mock_sel.return_value = job_b
        mock_hold_obj = MagicMock()
        mock_hold_obj.id = uuid.uuid4()
        mock_hold.return_value = mock_hold_obj
        mock_delay.return_value = MagicMock()

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        cycle_res = await AutopilotService.execute_autopilot_cycle(mock_db, user_id=user_id, dry_run=True)
        assert cycle_res["success"] is True
        assert cycle_res["job_id"] == str(job_b.id)
        assert cycle_res["company_id"] == str(comp_b_id)
