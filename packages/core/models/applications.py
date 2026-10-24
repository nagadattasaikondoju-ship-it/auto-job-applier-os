import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Campaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Autopilot continuous application campaign configuration."""

    __tablename__ = "campaigns"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), default="Default Autopilot", nullable=False)
    preferences_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    mode: Mapped[str] = mapped_column(
        String(32), default="review", nullable=False
    )  # review | auto_submit
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )  # active | paused | stopped
    daily_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    schedule: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=lambda: {"windows": ["09:00-18:00"]}, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    applications: Mapped[list["Application"]] = relationship(back_populates="campaign")


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core job application entity tracking lifecycle states from review to submission."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job_application"),)

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cover_letters.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="ready_for_review",
        nullable=False,
        index=True,
    )  # draft|preparing|ready_for_review|approved|submitting|submitted|needs_user_action|failed|withdrawn|interview|offer|rejected|ghosted
    channel: Mapped[str] = mapped_column(
        String(32), default="extension", nullable=False
    )  # extension | assisted | auto
    application_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    automation_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign | None"] = relationship(back_populates="applications")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationEvent(Base, UUIDPrimaryKeyMixin):
    """Append-only audit timeline of application lifecycle transitions."""

    __tablename__ = "application_events"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    actor: Mapped[str] = mapped_column(
        String(32), default="system", nullable=False
    )  # user | system | worker
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    application: Mapped["Application"] = relationship(back_populates="events")


class AutomationTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution state of browser automation and external tasks."""

    __tablename__ = "automation_tasks"

    type: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    queue: Mapped[str] = mapped_column(String(64), default="browser_automation", nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False
    )  # queued | running | succeeded | failed | dead
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    artifacts: Mapped[list["AutomationArtifact"]] = relationship(
        back_populates="automation_task", cascade="all, delete-orphan"
    )


class AutomationArtifact(Base, UUIDPrimaryKeyMixin):
    """Proof-of-submission, screenshot audit, and redacted form snapshots."""

    __tablename__ = "automation_artifacts"

    automation_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    html_snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    log: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    automation_task: Mapped["AutomationTask"] = relationship(back_populates="artifacts")
