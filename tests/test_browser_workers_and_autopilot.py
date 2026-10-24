"""Unit and integration tests for Phase 9: Browser Workers & Autopilot."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.browser.adapters import get_adapter
from apps.browser.executor import BrowserAutomationExecutor
from packages.core.models.applications import Campaign
from packages.core.models.jobs import Job
from packages.core.models.matching import JobMatch
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
async def test_readiness_review_vs_hybrid():
    """Review mode needs a profile, preferences and document consent; hybrid also needs
    auto-submit consent and a plan that allows auto-submit."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    mock_db = AsyncMock()
    res_none = MagicMock()
    res_none.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = res_none

    with (
        patch("packages.core.services.autopilot.active_consents", new_callable=AsyncMock) as mock_consents,
        patch("packages.core.services.credits.CreditsService.get_user_plan", new_callable=AsyncMock) as mock_plan,
    ):
        mock_consents.return_value = {}
        mock_plan.return_value = {"plan": "free", "config": {"name": "Free", "daily_application_limit": 5, "auto_submit_allowed": False}}

        review = await AutopilotService.readiness(mock_db, user_id, "review")
        assert review["can_start"] is False
        assert any("Upload your resume" in b for b in review["blockers"])
        assert any("preferences" in b for b in review["blockers"])
        assert any("tailored documents" in b for b in review["blockers"])

        hybrid = await AutopilotService.readiness(mock_db, user_id, "hybrid")
        assert any("auto-submit" in b for b in hybrid["blockers"])
        assert any("Upgrade to Pro" in b for b in hybrid["blockers"])


@pytest.mark.asyncio
async def test_can_run_autopilot_guards():
    """Guards: active campaign, readiness, campaign daily limit, circuit breaker."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    campaign = Campaign(id=uuid.uuid4(), user_id=user_id, status="active", mode="review", daily_limit=5, preferences_snapshot={})

    def first(value):
        r = MagicMock()
        r.scalars.return_value.first.return_value = value
        return r

    # 1. No active campaign
    mock_db = AsyncMock()
    mock_db.execute.return_value = first(None)
    ok, reason, _ = await AutopilotService.can_run_autopilot(mock_db, user_id)
    assert ok is False and "No active autopilot campaign" in reason

    ready = {"can_start": True, "blockers": []}
    with (
        patch.object(AutopilotService, "readiness", new_callable=AsyncMock) as mock_ready,
        patch.object(AutopilotService, "prepared_today", new_callable=AsyncMock) as mock_today,
        patch("packages.core.services.credits.CreditsService.check_daily_application_cap", new_callable=AsyncMock) as mock_cap,
    ):
        mock_cap.return_value = {"can_apply": True, "daily_limit": 5}

        # 2. Readiness blocker is surfaced
        mock_ready.return_value = {"can_start": False, "blockers": ["Set your job preferences (at least one target role)."]}
        mock_db.execute.return_value = first(campaign)
        ok, reason, _ = await AutopilotService.can_run_autopilot(mock_db, user_id)
        assert ok is False and "preferences" in reason

        # 3. Campaign daily limit reached
        mock_ready.return_value = ready
        mock_today.return_value = 5
        ok, reason, _ = await AutopilotService.can_run_autopilot(mock_db, user_id)
        assert ok is False and "Daily limit of 5" in reason

        # 4. Circuit breaker: 3 recent failures pause the campaign
        mock_today.return_value = 0
        failed = MagicMock()
        failed.status = "failed"
        recent = MagicMock()
        recent.scalars.return_value.all.return_value = [failed, failed, failed]
        mock_db.execute.side_effect = [first(campaign), recent]
        ok, reason, _ = await AutopilotService.can_run_autopilot(mock_db, user_id)
        assert ok is False and "Paused after 3 failed" in reason
        assert campaign.status == "paused"

        # 5. All clear
        campaign.status = "active"
        ok_recent = MagicMock()
        ok_recent.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [first(campaign), ok_recent]
        ok, reason, _ = await AutopilotService.can_run_autopilot(mock_db, user_id)
        assert ok is True and reason is None


@pytest.mark.asyncio
async def test_company_diversification_and_cycle_execution():
    """Diversification skips over-applied companies and excluded ones; review mode never submits,
    hybrid submits only very high-fit jobs with no open questions."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    comp_a_id, comp_b_id, comp_c_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    def job(company_id, title):
        return Job(id=uuid.uuid4(), company_id=company_id, title=title, locations=["Bengaluru"],
                   application_url=f"https://example.com/{title}", ats_type="greenhouse",
                   source="greenhouse", content_hash=uuid.uuid4().hex)

    job_a, job_c, job_b = job(comp_a_id, "a"), job(comp_c_id, "c"), job(comp_b_id, "b")
    match_a = JobMatch(user_id=user_id, job_id=job_a.id, match_score=95, status="new")
    match_c = JobMatch(user_id=user_id, job_id=job_c.id, match_score=92, status="new")
    match_b = JobMatch(user_id=user_id, job_id=job_b.id, match_score=85, status="new")

    applied = MagicMock()
    applied.scalars.return_value.all.return_value = []
    company_counts = MagicMock()
    company_counts.all.return_value = [(comp_a_id, 2)]  # already 2 applications to A this week
    pref = MagicMock()
    pref.scalar_one_or_none.return_value = MagicMock(excluded_companies=["Excluded Co"])
    rows = MagicMock()
    rows.all.return_value = [(match_a, job_a, "A Corp"), (match_c, job_c, "Excluded Co"), (match_b, job_b, "B Corp")]

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [applied, company_counts, pref, rows]
    picked = await AutopilotService.select_next_match(mock_db, user_id, 70)
    assert picked is not None and picked[0].id == job_b.id

    # Cycle behaviour per mode
    plan = MagicMock(unresolved_count=0)
    for mode, score, expect_status, expect_submit in [
        ("review", 99, "ready_for_review", False),
        ("hybrid", 95, "approved", True),
        ("hybrid", 85, "ready_for_review", False),
    ]:
        campaign = Campaign(id=uuid.uuid4(), user_id=user_id, status="active", mode=mode,
                            daily_limit=10, schedule={"min_match_score": 70, "hybrid_threshold": 90},
                            preferences_snapshot={})
        match = JobMatch(user_id=user_id, job_id=job_b.id, match_score=score, status="new")
        app_obj = MagicMock(id=uuid.uuid4(), status="ready_for_review")
        db = AsyncMock()
        db.add = MagicMock()
        pref_res = MagicMock()
        pref_res.scalar_one_or_none.return_value = None
        db.execute.return_value = pref_res
        with (
            patch.object(AutopilotService, "can_run_autopilot", new_callable=AsyncMock) as mock_can,
            patch.object(AutopilotService, "select_next_match", new_callable=AsyncMock) as mock_sel,
            patch("packages.core.services.applications.ApplicationsService.create_or_get_application", new_callable=AsyncMock) as mock_create,
            patch("packages.core.services.credits.CreditsService.reserve_hold", new_callable=AsyncMock) as mock_hold,
            patch("apps.workers.dispatch.enqueue_browser_submission") as mock_enqueue,
        ):
            mock_can.return_value = (True, None, campaign)
            mock_sel.return_value = (job_b, match)
            mock_create.return_value = (app_obj, plan)
            mock_hold.return_value = MagicMock(id=uuid.uuid4())
            res = await AutopilotService.execute_autopilot_cycle(db, user_id)
        assert res["success"] is True
        assert app_obj.status == expect_status, mode
        assert res["auto_submitted"] is expect_submit
        assert mock_enqueue.called is expect_submit
        assert match.status == "queued"
