"""Analytics and reporting engine computing application funnel metrics,
response rates, and AI token costs.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.applications import Application
from packages.core.models.matching import JobMatch
from packages.core.models.platform import AIUsage
from packages.core.models.profile import Education, Experience, Profile, Skill
from packages.core.services.credits import CreditsService
from packages.core.services.profile import compute_profile_completeness


class AnalyticsService:
    """Computes candidate pipeline metrics, application velocity, and telemetry."""

    @classmethod
    async def get_user_overview(cls, db: AsyncSession, user_id: str) -> dict[str, Any]:
        """Aggregate total applications, status distribution, credits, and AI usage."""
        # Status distribution
        status_stmt = (
            select(Application.status, func.count(Application.id))
            .where(Application.user_id == user_id)
            .group_by(Application.status)
        )
        status_res = await db.execute(status_stmt)
        status_counts = {row[0]: row[1] for row in status_res.all()}

        total_applications = sum(status_counts.values())
        total_submitted = (
            status_counts.get("submitted", 0)
            + status_counts.get("interview", 0)
            + status_counts.get("offer", 0)
        )
        total_interviews = status_counts.get("interview", 0)
        total_offers = status_counts.get("offer", 0)

        # Credits & cap
        credits_svc = CreditsService(db)
        balance = await credits_svc.get_available_balance(user_id)
        cap_info = await credits_svc.check_daily_application_cap(user_id)

        # AI Usage
        ai_stmt = (
            select(
                func.coalesce(func.sum(AIUsage.tokens_in), 0),
                func.coalesce(func.sum(AIUsage.tokens_out), 0),
                func.coalesce(func.sum(AIUsage.cost_estimate_usd), 0.0),
            )
            .where(AIUsage.user_id == user_id)
        )
        ai_res = await db.execute(ai_stmt)
        ai_in, ai_out, ai_cost = ai_res.first() or (0, 0, 0.0)

        # Profile completeness
        prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = prof_res.scalar_one_or_none()
        exp_res = await db.execute(select(Experience).where(Experience.user_id == user_id))
        edu_res = await db.execute(select(Education).where(Education.user_id == user_id))
        skill_res = await db.execute(select(Skill).where(Skill.user_id == user_id))

        comp = compute_profile_completeness(
            profile,
            experiences=list(exp_res.scalars().all()),
            educations=list(edu_res.scalars().all()),
            skills=list(skill_res.scalars().all()),
        )

        return {
            "total_applications": total_applications,
            "total_submitted": total_submitted,
            "total_interviews": total_interviews,
            "total_offers": total_offers,
            "status_distribution": status_counts,
            "credits": {
                "available_balance": balance,
                "daily_remaining": cap_info.get("remaining", 0),
                "daily_limit": cap_info.get("limit", 10),
            },
            "ai_usage": {
                "tokens_in": int(ai_in),
                "tokens_out": int(ai_out),
                "total_tokens": int(ai_in + ai_out),
                "estimated_cost_usd": float(round(ai_cost, 4)),
            },
            "profile_completeness_score": comp["score"],
            "can_start_autopilot": comp["can_start_autopilot"],
        }

    @classmethod
    async def get_conversion_funnel(cls, db: AsyncSession, user_id: str) -> dict[str, Any]:
        """Compute end-to-end conversion rates across matching and submission funnel stages."""
        # 1. Total matches
        matches_stmt = select(func.count(JobMatch.id)).where(JobMatch.user_id == user_id)
        matches_count = (await db.execute(matches_stmt)).scalar() or 0

        # 2. Total created/reviewed
        apps_stmt = select(Application.status).where(Application.user_id == user_id)
        apps_res = await db.execute(apps_stmt)
        statuses = [s for (s,) in apps_res.all()]

        ready_for_review_count = len(statuses)
        submitted_count = sum(1 for s in statuses if s in ["submitted", "interview", "offer"])
        interview_count = sum(1 for s in statuses if s in ["interview", "offer"])
        offer_count = sum(1 for s in statuses if s == "offer")

        def _pct(num: int, denom: int) -> float:
            return round((num / denom) * 100, 1) if denom > 0 else 0.0

        return {
            "stages": [
                {"stage": "matched", "count": matches_count, "conversion_pct": 100.0},
                {
                    "stage": "reviewed",
                    "count": ready_for_review_count,
                    "conversion_pct": _pct(ready_for_review_count, matches_count),
                },
                {
                    "stage": "submitted",
                    "count": submitted_count,
                    "conversion_pct": _pct(submitted_count, ready_for_review_count),
                },
                {
                    "stage": "interview",
                    "count": interview_count,
                    "conversion_pct": _pct(interview_count, submitted_count),
                },
                {
                    "stage": "offer",
                    "count": offer_count,
                    "conversion_pct": _pct(offer_count, interview_count),
                },
            ],
            "overall_conversion_pct": _pct(offer_count, submitted_count),
        }
