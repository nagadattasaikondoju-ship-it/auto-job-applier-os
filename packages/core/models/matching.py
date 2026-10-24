import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobMatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Scored match between a specific job posting and a user profile version."""

    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", "profile_version_id", name="uq_user_job_match"),
    )

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profile_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    filter_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vector_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    decision: Mapped[str] = mapped_column(
        String(16), default="skip", nullable=False
    )  # apply | maybe | skip
    fit_reasons: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    gaps: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    resume_focus: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    risk_flags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    model: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    user_feedback: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )  # good | bad | null
    status: Mapped[str] = mapped_column(
        String(32), default="new", nullable=False, index=True
    )  # new | seen | saved | dismissed | queued


class ResumeVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Deterministically generated, truth-checked tailored resume versions."""

    __tablename__ = "resume_versions"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profile_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    template_id: Mapped[str] = mapped_column(String(64), default="classic_ats", nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    truth_check_status: Mapped[str] = mapped_column(
        String(32), default="passed", nullable=False
    )  # passed | flagged | failed
    flagged_claims: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False
    )  # draft | approved
    version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class CoverLetter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Concise (<300 word) company-specific tailored cover letters."""

    __tablename__ = "cover_letters"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profile_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)


class ScreeningAnswer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific questions & resolved answers for an application."""

    __tablename__ = "screening_answers"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(32), default="answer_bank", nullable=False
    )  # answer_bank | ai | user
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
