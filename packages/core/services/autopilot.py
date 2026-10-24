"""Autopilot service managing automated job matching, circuit breaking,
credit reservation, and browser submission pipelines.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.applications import (
    Application,
    ApplicationEvent,
    Campaign,
)
from packages.core.models.jobs import Job
from packages.core.models.matching import JobMatch
from packages.core.models.platform import Consent
from packages.core.models.profile import (
    Education,
    Experience,
    Profile,
    Skill,
)
from packages.core.services.credits import CreditsService
from packages.core.services.profile import compute_profile_completeness

logger = logging.getLogger(__name__)


class AutopilotService:
    """Core orchestration engine for autonomous job application campaigns."""

    @classmethod
    async def can_run_autopilot(
        cls, db: AsyncSession, user_id: str
    ) -> tuple[bool, str | None, Campaign | None]:
        """Verify strict safety requirements before initiating an autonomous run:
        1. Profile completeness score >= 80
        2. DPDP explicit consent granted for auto_submit
        3. Active campaign exists
        4. Daily limit not exceeded
        5. Circuit breaker not tripped (< 3 consecutive failures)
        6. Credit balance >= 1
        """
        # 1. Profile completeness check
        res = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = res.scalar_one_or_none()
        if not profile:
            return False, "Profile does not exist. Complete onboarding first.", None

        exp_res = await db.execute(select(Experience).where(Experience.user_id == user_id))
        edu_res = await db.execute(select(Education).where(Education.user_id == user_id))
        skill_res = await db.execute(select(Skill).where(Skill.user_id == user_id))

        completeness = compute_profile_completeness(
            profile,
            experiences=list(exp_res.scalars().all()),
            educations=list(edu_res.scalars().all()),
            skills=list(skill_res.scalars().all()),
        )
        if completeness["score"] < 80:
            return (
                False,
                f"Profile score is {completeness['score']}/100. Minimum 80 required for Autopilot.",
                None,
            )

        # 2. DPDP consent for auto_submit
        consent_res = await db.execute(
            select(Consent).where(
                Consent.user_id == user_id,
                Consent.purpose == "auto_submit",
                Consent.withdrawn_at.is_(None),
            )
        )
        consent = consent_res.scalar_one_or_none()
        if not consent:
            return False, "Explicit DPDP consent for auto_submit has not been granted.", None

        # 3. Active campaign check
        camp_res = await db.execute(
            select(Campaign).where(Campaign.user_id == user_id, Campaign.status == "active")
        )
        campaign = camp_res.scalar_one_or_none()
        if not campaign:
            return False, "No active autopilot campaign found.", None

        # 4. Daily application limit
        credits_svc = CreditsService(db)
        cap_info = await credits_svc.check_daily_application_cap(user_id)
        if not cap_info.get("allowed", True):
            remaining = cap_info.get("remaining", 0)
            return False, f"Daily limit reached ({remaining} applications remaining today).", campaign

        # 5. Circuit breaker: 3 consecutive failures in last 24h
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        recent_apps_res = await db.execute(
            select(Application)
            .where(Application.user_id == user_id, Application.created_at >= cutoff)
            .order_by(desc(Application.created_at))
            .limit(3)
        )
        recent_apps = recent_apps_res.scalars().all()
        if len(recent_apps) >= 3 and all(a.status == "failed" for a in recent_apps):
            # Trip circuit breaker and pause campaign
            campaign.status = "paused"
            await db.commit()
            return (
                False,
                "Circuit breaker tripped: 3 consecutive application failures. Campaign paused.",
                campaign,
            )

        # 6. Credit balance check
        balance = await credits_svc.get_available_balance(user_id)
        if balance < 1:
            return False, "Insufficient credit balance for autopilot run.", campaign

        return True, None, campaign

    @classmethod
    async def select_next_job_for_autopilot(
        cls, db: AsyncSession, user_id: str, min_match_score: float = 0.60
    ) -> Job | None:
        """Select highest scored matched job that satisfies:
        - Score >= min_match_score
        - Company diversification (<= 2 applications to same company in 7 days)
        - Not already applied by this user
        """
        # Fetch companies applied to in the last 7 days
        seven_days_ago = datetime.now(UTC) - timedelta(days=7)
        apps_res = await db.execute(
            select(Application.job_id).where(
                Application.user_id == user_id, Application.created_at >= seven_days_ago
            )
        )
        applied_job_ids = set(apps_res.scalars().all())

        # Find company application frequency
        applied_company_counts: dict[uuid.UUID, int] = {}
        if applied_job_ids:
            jobs_res = await db.execute(select(Job).where(Job.id.in_(applied_job_ids)))
            for j in jobs_res.scalars().all():
                applied_company_counts[j.company_id] = (
                    applied_company_counts.get(j.company_id, 0) + 1
                )

        # Get matched jobs
        target_score = int(min_match_score * 100 if min_match_score <= 1.0 else min_match_score)
        matches_res = await db.execute(
            select(JobMatch)
            .where(
                JobMatch.user_id == user_id,
                JobMatch.match_score >= target_score,
                JobMatch.status.in_(["matched", "tailored", "new"]),
            )
            .order_by(desc(JobMatch.match_score))
            .limit(50)
        )
        matches = matches_res.scalars().all()

        for m in matches:
            if m.job_id in applied_job_ids:
                continue

            job_res = await db.execute(select(Job).where(Job.id == m.job_id))
            job = job_res.scalar_one_or_none()
            if not job:
                continue

            # Check company diversification
            if applied_company_counts.get(job.company_id, 0) >= 2:
                continue

            return job

        return None

    @classmethod
    async def execute_autopilot_cycle(
        cls,
        db: AsyncSession,
        user_id: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Execute a single autopilot submission cycle:
        - Validates safety preconditions
        - Selects diversified job match
        - Reserves credit hold
        - Creates application record
        - Enqueues browser automation
        """
        can_run, reason, campaign = await cls.can_run_autopilot(db, user_id)
        if not can_run:
            return {"success": False, "reason": reason}

        job = await cls.select_next_job_for_autopilot(db, user_id)
        if not job:
            return {"success": False, "reason": "No qualifying jobs available for autopilot"}

        # Create application entity
        application = Application(
            user_id=user_id,
            job_id=job.id,
            campaign_id=campaign.id if campaign else None,
            status="preparing",
            channel="auto",
            application_url=job.application_url,
        )
        db.add(application)
        await db.flush()

        # Reserve credit hold
        credits_svc = CreditsService(db)
        hold = await credits_svc.reserve_hold(
            user_id=user_id,
            amount=1,
            task_id=str(application.id),
        )

        event = ApplicationEvent(
            application_id=application.id,
            type="autopilot_cycle_started",
            actor="system",
            payload={"job_id": str(job.id), "hold_id": str(hold.id), "dry_run": dry_run},
        )
        db.add(event)
        await db.commit()
        await db.refresh(application)

        # Enqueue browser automation task via Celery
        try:
            from apps.workers.tasks.autopilot import execute_browser_application

            execute_browser_application.delay(str(application.id), dry_run=dry_run)
        except Exception as e:
            logger.info(f"Celery enqueue skipped or running synchronously: {e}")

        return {
            "success": True,
            "application_id": str(application.id),
            "job_id": str(job.id),
            "status": application.status,
            "company_id": str(job.company_id),
            "dry_run": dry_run,
        }
