import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class QuestionnaireSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks state and progress across the multi-step adaptive onboarding wizard."""

    __tablename__ = "questionnaire_sessions"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default="in_progress", nullable=False
    )  # in_progress | completed
    current_step: Mapped[str] = mapped_column(String(64), default="career_goal", nullable=False)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobPreference(Base, TimestampMixin):
    """Target job criteria and matching constraints for a user."""

    __tablename__ = "job_preferences"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    target_roles: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    role_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    seniority: Mapped[str] = mapped_column(
        String(32), default="fresher", nullable=False
    )  # intern | fresher | junior | mid | senior | lead
    min_exp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_exp: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    locations: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )  # Normalized cities
    remote_mode: Mapped[list[str]] = mapped_column(
        JSONB, default=lambda: ["remote", "hybrid", "onsite"], nullable=False
    )
    min_salary_lpa: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    company_size: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    industries: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    excluded_companies: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    excluded_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    employment_types: Mapped[list[str]] = mapped_column(
        JSONB, default=lambda: ["full-time"], nullable=False
    )
    visa_sponsorship_needed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_application_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    auto_submit_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_match_score: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    learned_weights: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class AnswerBank(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reusable, canonical screening form answers to achieve zero-AI autofill."""

    __tablename__ = "answer_bank"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_type: Mapped[str] = mapped_column(
        String(32), default="short", nullable=False
    )  # short | long | choice | number | boolean | date
    source: Mapped[str] = mapped_column(
        String(32), default="questionnaire", nullable=False
    )  # questionnaire | user_edit | ai_approved
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding = mapped_column(Vector(768), nullable=True)


class AnswerEdit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Historical user edits of AI-generated answers for personalized style learning."""

    __tablename__ = "answer_edits"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    original_answer: Mapped[str] = mapped_column(Text, nullable=False)
    edited_answer: Mapped[str] = mapped_column(Text, nullable=False)
    used_for_personalization: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
