from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User in-app notifications and multi-channel delivery status."""

    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # review_ready | needs_action | digest | ...
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    channels: Mapped[list[str]] = mapped_column(
        JSONB, default=lambda: ["in_app"], nullable=False
    )  # in_app | email


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Immutable audit trail for DPDP compliance and security operations."""

    __tablename__ = "audit_log"

    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )


class AIUsage(Base, UUIDPrimaryKeyMixin):
    """Fine-grained token counting, latency telemetry, and cost attribution per user."""

    __tablename__ = "ai_usage"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # parse_resume | tailor_resume | match_score | ...
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )


class Consent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit, granular DPDP compliance consent records."""

    __tablename__ = "consents"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # profile_matching | document_generation | auto_submit
    version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
