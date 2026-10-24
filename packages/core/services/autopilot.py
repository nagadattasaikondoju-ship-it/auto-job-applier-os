"""Autopilot: continuously prepares applications for the best matches.

Modes (launch scope):
- review: every application is prepared (answers resolved) and waits for the user's approval.
- hybrid: same, except very high-fit jobs with no open questions are submitted automatically,
  only with explicit auto_submit consent and a plan that allows auto-submit.
Full-auto is intentionally not offered yet.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.applications import Application, ApplicationEvent, Campaign
from packages.core.models.jobs import Company, Job
from packages.core.models.matching import JobMatch
from packages.core.models.platform import Consent, Notification
from packages.core.models.preferences import JobPreference
from packages.core.models.profile import Education, Experience, Profile, Skill
from packages.core.services.credits import CreditsService
from packages.core.services.profile import compute_profile_completeness

logger = logging.getLogger(__name__)

MODES = ("review", "hybrid")
DEFAULT_HYBRID_THRESHOLD = 90
MIN_SCORE_REVIEW = 50
MIN_SCORE_HYBRID = 80


def today_start() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


async def active_consents(db: AsyncSession, user_id: str) -> dict[str, bool]:
    """Latest grant/withdraw state per purpose."""
    rows = (
        await db.execute(select(Consent).where(Consent.user_id == user_id).order_by(Consent.granted_at.asc()))
    ).scalars().all()
    state: dict[str, bool] = {}
    for c in rows:
        state[c.purpose] = c.withdrawn_at is None
    return state


class AutopilotService:
    """Core orchestration engine for job application campaigns."""

    @classmethod
    async def readiness(cls, db: AsyncSession, user_id: str, mode: str = "review") -> dict[str, Any]:
        """Everything needed to start (or keep running) a campaign in the given mode."""
        blockers: list[str] = []
        profile = (await db.execute(select(Profile).where(Profile.user_id == user_id))).scalar_one_or_none()
        score = 0
        if profile:
            completeness = compute_profile_completeness(
                profile,
                experiences=list((await db.execute(select(Experience).where(Experience.user_id == user_id))).scalars().all()),
                educations=list((await db.execute(select(Education).where(Education.user_id == user_id))).scalars().all()),
                skills=list((await db.execute(select(Skill).where(Skill.user_id == user_id))).scalars().all()),
            )
            score = int(completeness["score"])
        else:
            blockers.append("Upload your resume to create your profile.")

        min_score = MIN_SCORE_HYBRID if mode == "hybrid" else MIN_SCORE_REVIEW
        if profile and score < min_score:
            blockers.append(f"Profile is {score}% complete; {min_score}% is needed for {mode} mode.")

        pref = (await db.execute(select(JobPreference).where(JobPreference.user_id == user_id))).scalar_one_or_none()
        if not pref or not pref.target_roles:
            blockers.append("Set your job preferences (at least one target role).")

        consents = await active_consents(db, user_id)
        if not consents.get("document_generation"):
            blockers.append("Allow tailored documents in Settings → Data permissions.")

        plan_info = await CreditsService(db).get_user_plan(user_id)
        if mode == "hybrid":
            if not consents.get("auto_submit"):
                blockers.append("Hybrid mode needs your permission to auto-submit (Settings → Data permissions).")
            if not plan_info["config"].get("auto_submit_allowed"):
                blockers.append(f"Your {plan_info['config']['name']} plan doesn't include auto-submit. Upgrade to Pro.")

        return {
            "mode": mode,
            "can_start": not blockers,
            "blockers": blockers,
            "profile_score": score,
            "has_preferences": bool(pref and pref.target_roles),
            "consents": consents,
            "plan": plan_info["plan"],
            "plan_daily_limit": int(plan_info["config"]["daily_application_limit"]),
            "auto_submit_allowed": bool(plan_info["config"].get("auto_submit_allowed")),
        }

    @classmethod
    async def get_active_campaign(cls, db: AsyncSession, user_id: str) -> Campaign | None:
        return (
            await db.execute(
                select(Campaign)
                .where(Campaign.user_id == user_id, Campaign.status.in_(["active", "paused"]))
                .order_by(desc(Campaign.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    @classmethod
    async def prepared_today(cls, db: AsyncSession, campaign: Campaign) -> int:
        return int(
            (
                await db.execute(
                    select(func.count(Application.id)).where(
                        Application.campaign_id == campaign.id, Application.created_at >= today_start()
                    )
                )
            ).scalar()
            or 0
        )

    @classmethod
    async def can_run_autopilot(
        cls, db: AsyncSession, user_id: str
    ) -> tuple[bool, str | None, Campaign | None]:
        """Safety checks before a cycle: readiness, active campaign, daily caps, circuit breaker."""
        camp_res = await db.execute(
            select(Campaign).where(Campaign.user_id == user_id, Campaign.status == "active")
        )
        campaign = camp_res.scalars().first()
        if not campaign:
            return False, "No active autopilot campaign found.", None

        ready = await cls.readiness(db, user_id, campaign.mode)
        if not ready["can_start"]:
            return False, ready["blockers"][0], campaign

        if await cls.prepared_today(db, campaign) >= campaign.daily_limit:
            return False, f"Daily limit of {campaign.daily_limit} applications reached.", campaign

        cap_info = await CreditsService(db).check_daily_application_cap(user_id)
        if not cap_info.get("can_apply", True):
            return False, f"Plan limit of {cap_info.get('daily_limit')} submissions today reached.", campaign

        # Circuit breaker: 3 consecutive failures in the last 24h pauses the campaign
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        recent = (
            await db.execute(
                select(Application)
                .where(Application.user_id == user_id, Application.created_at >= cutoff)
                .order_by(desc(Application.created_at))
                .limit(3)
            )
        ).scalars().all()
        if len(recent) >= 3 and all(a.status == "failed" for a in recent):
            campaign.status = "paused"
            campaign.stats = {**(campaign.stats or {}), "paused_reason": "3 failed applications in a row"}
            await db.commit()
            return False, "Paused after 3 failed applications in a row.", campaign

        return True, None, campaign

    @classmethod
    async def select_next_match(
        cls, db: AsyncSession, user_id: str, min_match_score: int
    ) -> tuple[Job, JobMatch] | None:
        """Best unapplied match above the threshold, with company diversification
        (max 2 applications per company per 7 days) and excluded companies honoured."""
        applied_job_ids = set(
            (await db.execute(select(Application.job_id).where(Application.user_id == user_id))).scalars().all()
        )
        week_ago = datetime.now(UTC) - timedelta(days=7)
        recent_company_counts: dict[uuid.UUID, int] = {}
        for company_id, count in (
            await db.execute(
                select(Job.company_id, func.count(Application.id))
                .join(Job, Application.job_id == Job.id)
                .where(Application.user_id == user_id, Application.created_at >= week_ago)
                .group_by(Job.company_id)
            )
        ).all():
            recent_company_counts[company_id] = int(count)

        pref = (await db.execute(select(JobPreference).where(JobPreference.user_id == user_id))).scalar_one_or_none()
        excluded = {c.strip().lower() for c in (pref.excluded_companies if pref else []) if c.strip()}

        rows = (
            await db.execute(
                select(JobMatch, Job, Company.name)
                .join(Job, JobMatch.job_id == Job.id)
                .join(Company, Job.company_id == Company.id)
                .where(
                    JobMatch.user_id == user_id,
                    JobMatch.match_score >= min_match_score,
                    JobMatch.decision != "skip",
                    JobMatch.status.in_(["new", "seen", "saved", "matched", "tailored"]),
                    Job.is_active.is_(True),
                    Job.is_suspicious.is_(False),
                )
                .order_by(desc(JobMatch.match_score))
                .limit(100)
            )
        ).all()
        for match, job, company_name in rows:
            if job.id in applied_job_ids:
                continue
            if (company_name or "").strip().lower() in excluded:
                continue
            if recent_company_counts.get(job.company_id, 0) >= 2:
                continue
            return job, match
        return None

    @classmethod
    async def execute_autopilot_cycle(
        cls,
        db: AsyncSession,
        user_id: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Prepare one application. Review mode waits for approval; hybrid may submit high-fit jobs."""
        can_run, reason, campaign = await cls.can_run_autopilot(db, user_id)
        if not can_run or campaign is None:
            return {"success": False, "reason": reason}

        pref = (await db.execute(select(JobPreference).where(JobPreference.user_id == user_id))).scalar_one_or_none()
        min_score = int((campaign.schedule or {}).get("min_match_score") or (pref.min_match_score if pref else 70))
        picked = await cls.select_next_match(db, user_id, min_score)
        if not picked:
            return {"success": False, "reason": "No new jobs above your minimum match score right now."}
        job, match = picked

        from packages.core.services.applications import ApplicationsService

        app_obj, plan = await ApplicationsService(db).create_or_get_application(
            user_id=user_id, job_id=job.id, channel="auto", campaign_id=campaign.id
        )
        match.status = "queued"

        threshold = int((campaign.schedule or {}).get("hybrid_threshold") or DEFAULT_HYBRID_THRESHOLD)
        auto_submit = (
            campaign.mode == "hybrid"
            and match.match_score >= threshold
            and plan.unresolved_count == 0
            and not dry_run
        )

        if auto_submit:
            app_obj.status = "approved"
            hold = await CreditsService(db).reserve_hold(user_id=user_id, amount=1, task_id=str(app_obj.id))
            db.add(
                ApplicationEvent(
                    application_id=app_obj.id,
                    type="auto_approved",
                    actor="system",
                    payload={"match_score": match.match_score, "threshold": threshold, "hold_id": str(hold.id)},
                )
            )
        else:
            app_obj.status = "ready_for_review"
            db.add(
                Notification(
                    user_id=user_id,
                    type="review_ready",
                    title=f"Ready for review: {job.title}",
                    body=f"Match {match.match_score}/100. Check the answers and approve when you're happy.",
                    data={"application_id": str(app_obj.id), "job_id": str(job.id)},
                )
            )
        await db.commit()

        if auto_submit:
            from apps.workers.dispatch import enqueue_browser_submission

            enqueue_browser_submission(str(app_obj.id))

        return {
            "success": True,
            "application_id": str(app_obj.id),
            "job_id": str(job.id),
            "status": app_obj.status,
            "auto_submitted": auto_submit,
            "match_score": match.match_score,
        }

    @classmethod
    async def run_batch(cls, db: AsyncSession, user_id: str, max_items: int = 5) -> dict[str, Any]:
        """Prepare up to max_items applications now (used by 'Run now' and the scheduler)."""
        results = []
        reason = None
        for _ in range(max_items):
            r = await cls.execute_autopilot_cycle(db, user_id)
            if not r.get("success"):
                reason = r.get("reason")
                break
            results.append(r)
        return {"prepared": len(results), "items": results, "stopped_reason": reason}
