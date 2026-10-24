import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Global company registry with discovered ATS metadata."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    careers_url: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    ats_type: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    ats_board_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str] = mapped_column(String(64), default="India", nullable=False)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    crawl_interval_minutes: Mapped[int] = mapped_column(Integer, default=360, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Normalized global job repository."""

    __tablename__ = "jobs"

    source: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # greenhouse | lever | adzuna | ...
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    seniority: Mapped[str] = mapped_column(
        String(32), default="fresher", nullable=False
    )  # intern | fresher | junior | mid | senior | lead
    location_raw: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    locations: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )  # Normalized cities
    country: Mapped[str] = mapped_column(String(64), default="India", nullable=False)
    remote_mode: Mapped[str] = mapped_column(
        String(32), default="onsite", nullable=False
    )  # remote | hybrid | onsite
    employment_type: Mapped[str] = mapped_column(String(32), default="full-time", nullable=False)
    description_html: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    salary_min_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    experience_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    experience_max: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    application_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    ats_type: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="jobs")
    embedding: Mapped["JobEmbedding"] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )


class JobEmbedding(Base, TimestampMixin):
    """pgvector semantic vector index column for jobs."""

    __tablename__ = "job_embeddings"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    embedding = mapped_column(Vector(768), nullable=False)

    job: Mapped["Job"] = relationship(back_populates="embedding")


class JobAlias(Base, UUIDPrimaryKeyMixin):
    """Tracks cross-source deduplicated URLs and IDs pointing to canonical job postings."""

    __tablename__ = "job_aliases"

    alias_source: Mapped[str] = mapped_column(String(64), nullable=False)
    alias_external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    canonical_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class PreferenceBucket(Base, UUIDPrimaryKeyMixin):
    """Grouping of active users by target cluster to optimize matching from O(N*M) to O(1) indexed lookup."""

    __tablename__ = "preference_buckets"

    bucket_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


class JobFormSchema(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Extracted questions and field selectors cached once globally per job."""

    __tablename__ = "job_form_schemas"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ats_type: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    extraction_method: Mapped[str] = mapped_column(
        String(32), default="api", nullable=False
    )  # api | dom
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ready", nullable=False)


class AtsFlow(Base, TimestampMixin):
    """Reliability statistics and trust gate for ATS automation."""

    __tablename__ = "ats_flows"

    ats_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    flow_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    success_rate_7d: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
