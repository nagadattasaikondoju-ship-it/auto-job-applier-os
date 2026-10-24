"""Transactional email delivery via Resend and in-app notifications engine."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config import Settings
from packages.core.models.platform import Notification
from packages.core.models.profile import Profile

logger = logging.getLogger(__name__)
settings = Settings()


class NotificationsService:
    """Multi-channel notification service for transactional email and in-app alerts."""

    @classmethod
    async def send_email(
        cls,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: str | None = None,
        simulate: bool = False,
    ) -> dict[str, Any]:
        """Send transactional email using Resend API."""
        api_key = settings.resend_api_key
        sender = from_email or (
            "onboarding@resend.dev"
            if settings.app_env != "production" and "@applyon.in" in settings.email_from
            else settings.email_from
        )

        if simulate or not api_key or settings.app_env == "test":
            logger.info(f"Simulating email to {to_email} with subject: {subject}")
            return {"id": f"sim_{uuid.uuid4().hex[:12]}", "simulated": True, "to": to_email}

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    logger.error(f"Resend email error {resp.status_code}: {resp.text}")
                    return {"success": False, "status_code": resp.status_code, "error": resp.text}
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to deliver email to {to_email}: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def create_notification(
        cls,
        db: AsyncSession,
        user_id: str,
        notif_type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        channels: list[str] | None = None,
    ) -> Notification:
        """Create in-app notification and optionally trigger email dispatch."""
        chan = channels or ["in_app"]
        notif = Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            body=body,
            data=data or {},
            channels=chan,
        )
        db.add(notif)
        await db.flush()

        if "email" in chan:
            # Query user email
            prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
            profile = prof_res.scalar_one_or_none()
            if profile and profile.email:
                html_body = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #1e1b4b;">{title}</h2>
                    <p style="color: #334155; font-size: 16px; line-height: 1.5;">{body}</p>
                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
                    <p style="color: #94a3b8; font-size: 12px;">Applyon - AI Job Application Copilot</p>
                </div>
                """
                await cls.send_email(to_email=profile.email, subject=title, html_body=html_body)

        return notif

    @classmethod
    async def notify_review_ready(
        cls,
        db: AsyncSession,
        user_id: str,
        job_title: str,
        company_name: str,
        application_id: uuid.UUID | str,
    ) -> Notification:
        title = f"Application Ready for Review: {job_title} at {company_name}"
        body = (
            f"Your tailored application for {job_title} at {company_name} is prepared. "
            "Review your answers and submit with 1 click."
        )
        return await cls.create_notification(
            db,
            user_id=user_id,
            notif_type="review_ready",
            title=title,
            body=body,
            data={"application_id": str(application_id)},
            channels=["in_app", "email"],
        )

    @classmethod
    async def notify_needs_action(
        cls,
        db: AsyncSession,
        user_id: str,
        job_title: str,
        reason: str,
        application_url: str,
    ) -> Notification:
        title = f"Action Required: Application for {job_title}"
        body = f"Human action required to complete application ({reason}). Please click to finish."
        return await cls.create_notification(
            db,
            user_id=user_id,
            notif_type="needs_action",
            title=title,
            body=body,
            data={"url": application_url, "reason": reason},
            channels=["in_app", "email"],
        )

    @classmethod
    async def notify_daily_digest(
        cls,
        db: AsyncSession,
        user_id: str,
        matches_count: int,
        applied_count: int,
    ) -> Notification:
        title = "Applyon Daily Digest"
        body = f"Today's summary: {matches_count} new job matches discovered, {applied_count} applications submitted."
        return await cls.create_notification(
            db,
            user_id=user_id,
            notif_type="digest",
            title=title,
            body=body,
            data={"matches_count": matches_count, "applied_count": applied_count},
            channels=["in_app", "email"],
        )

    @classmethod
    async def list_notifications(
        cls,
        db: AsyncSession,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        """List user notifications with pagination and unread counts."""
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.read_at.is_(None))

        query = query.order_by(desc(Notification.created_at)).limit(limit).offset(offset)
        res = await db.execute(query)
        items = list(res.scalars().all())

        # Count unread
        unread_stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        unread_res = await db.execute(unread_stmt)
        unread_count = unread_res.scalar() or 0

        return items, unread_count

    @classmethod
    async def mark_as_read(
        cls, db: AsyncSession, user_id: str, notification_id: uuid.UUID
    ) -> Notification | None:
        """Mark specific notification as read."""
        stmt = select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
        res = await db.execute(stmt)
        notif = res.scalar_one_or_none()
        if notif:
            notif.read_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(notif)
        return notif

    @classmethod
    async def mark_all_read(cls, db: AsyncSession, user_id: str) -> int:
        """Mark all unread notifications for user as read."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount or 0
