from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserMeta(Base, TimestampMixin):
    """User metadata, DPDP consent tracking, and onboarding state."""

    __tablename__ = "users_meta"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    onboarding_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )  # pending | in_progress | completed
    consent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_opt_in: Mapped[bool] = mapped_column(default=False, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Subscription(Base, TimestampMixin):
    """Active billing subscription status."""

    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CreditsLedger(Base, UUIDPrimaryKeyMixin):
    """Append-only credit transactions for AI and application actions."""

    __tablename__ = "credits_ledger"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    credit_type: Mapped[str] = mapped_column(String(16), nullable=False)  # ai | apply
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # + or -
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class CreditHold(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Temporary credit reserves held prior to async worker pipeline execution."""

    __tablename__ = "credit_holds"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    credit_type: Mapped[str] = mapped_column(String(16), default="apply", nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default="held", nullable=False
    )  # held | captured | released
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
