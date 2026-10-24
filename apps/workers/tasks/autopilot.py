"""Celery tasks for Autopilot scheduler and browser automation workers."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from apps.browser.executor import BrowserAutomationExecutor
from apps.workers.celery_app import celery_app
from packages.core.async_utils import run_async
from packages.core.database import async_session_maker
from packages.core.models.applications import Application, ApplicationEvent, Campaign
from packages.core.models.jobs import Job
from packages.core.models.platform import Notification
from packages.core.models.profile import Profile
from packages.core.services.answer_resolver import AnswerResolutionService
from packages.core.services.autopilot import AutopilotService
from packages.core.services.credits import CreditsService
from packages.core.services.form_schema import FormSchemaService

logger = logging.getLogger("applyon.workers.autopilot")


async def _async_execute_browser_application(
    application_id_str: str, dry_run: bool = False
) -> dict[str, Any]:
    app_uuid = uuid.UUID(application_id_str)

    async with async_session_maker() as session:
        res = await session.execute(select(Application).where(Application.id == app_uuid))
        application = res.scalar_one_or_none()
        if not application:
            return {"error": "Application not found", "application_id": application_id_str}

        # Fetch job and profile
        job_res = await session.execute(select(Job).where(Job.id == application.job_id))
        job = job_res.scalar_one_or_none()
        if not job:
            return {"error": "Job not found", "application_id": application_id_str}

        prof_res = await session.execute(
            select(Profile).where(Profile.user_id == application.user_id)
        )
        profile = prof_res.scalar_one_or_none()
        if not profile:
            return {"error": "Profile not found", "application_id": application_id_str}

        # Extract schema and resolve answers
        form_schema = await FormSchemaService.extract_form_schema(
            session=session,
            url=job.application_url,
            ats_type=job.ats_type or "generic",
        )
        resolved_fields = await AnswerResolutionService.resolve_all_fields(
            session=session,
            user_id=application.user_id,
            fields=form_schema.get("fields", []),
            job_description=job.description_text or "",
            profile=profile,
        )

        executor = BrowserAutomationExecutor()
        auto_result = await executor.execute_application(
            application_id=application.id,
            application_url=job.application_url,
            ats_type=job.ats_type or "generic",
            fields=resolved_fields,
            dry_run=dry_run,
        )

        # Handle outcomes adhering to Section 0 & financial ledger safety
        credits_svc = CreditsService(session)
        from packages.core.models.identity import CreditHold
        hold_stmt = select(CreditHold).where(
            CreditHold.user_id == application.user_id,
            CreditHold.task_id == str(application.id),
            CreditHold.status == "held",
        )
        active_hold = (await session.execute(hold_stmt)).scalars().first()

        if auto_result.blocker_detected or auto_result.status == "needs_user_action":
            # Safety stop: human intervention needed, release credit hold
            if active_hold:
                await credits_svc.release_hold(active_hold.id, reason="blocker_detected")
            application.status = "needs_user_action"
            application.failure_reason = f"Blocker detected: {auto_result.blocker_detected}"

            # Create notification
            notif = Notification(
                user_id=application.user_id,
                type="needs_action",
                title="Action Required on Application",
                body=f"Application for {job.title} requires verification ({auto_result.blocker_detected}).",
                data={"application_id": str(application.id), "url": job.application_url},
            )
            session.add(notif)
            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    type="blocker_detected",
                    actor="worker",
                    payload={"blocker": auto_result.blocker_detected},
                )
            )

        elif auto_result.status == "submitted":
            # Capture credit hold atomically
            if active_hold:
                await credits_svc.capture_hold(
                    active_hold.id,
                    reason="autopilot_application_submitted",
                    ref_id=str(application.id),
                )
            application.status = "submitted"
            application.submitted_at = datetime.now(UTC)
            application.follow_up_at = datetime.now(UTC) + timedelta(days=6)
            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    type="submitted",
                    actor="worker",
                    payload={"proof_screenshot": auto_result.proof_screenshot_path},
                )
            )

        elif auto_result.status == "ready_for_review":
            application.status = "ready_for_review"
            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    type="prepared_for_review",
                    actor="worker",
                    payload={"fields_count": auto_result.fields_filled},
                )
            )

        else:  # failed
            if active_hold:
                await credits_svc.release_hold(active_hold.id, reason="execution_failed")
            application.status = "failed"
            application.failure_reason = auto_result.error_message
            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    type="failed",
                    actor="worker",
                    payload={"error": auto_result.error_message},
                )
            )

        await session.commit()
        return {
            "application_id": str(application.id),
            "status": application.status,
            "fields_filled": auto_result.fields_filled,
        }


async def _async_autopilot_tick() -> dict[str, Any]:
    """Prepare a few applications per active campaign (each user in their own session)."""
    async with async_session_maker() as session:
        user_ids = list(
            (await session.execute(select(Campaign.user_id).where(Campaign.status == "active"))).scalars().all()
        )
    executed = 0
    for uid in user_ids:
        try:
            async with async_session_maker() as session:
                res = await AutopilotService.run_batch(db=session, user_id=uid, max_items=3)
                executed += res["prepared"]
        except Exception as e:  # one user's failure must not stop the others
            logger.warning("Autopilot tick failed for %s: %s", uid, e)
    active_campaigns = user_ids

    return {"active_campaigns": len(active_campaigns), "executed_cycles": executed}


@celery_app.task(name="autopilot.execute_browser_application", queue="browser_automation")
def execute_browser_application(application_id: str, dry_run: bool = False) -> dict[str, Any]:
    return run_async(
        _async_execute_browser_application(application_id_str=application_id, dry_run=dry_run)
    )


@celery_app.task(name="autopilot.tick", queue="autopilot")
def autopilot_tick() -> dict[str, Any]:
    return run_async(_async_autopilot_tick())
