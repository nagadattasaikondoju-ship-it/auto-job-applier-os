import uuid
from datetime import date
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Profile(Base, TimestampMixin):
    """Master user profile containing verified career and logistics attributes."""

    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    state: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(64), default="India", nullable=False)
    pincode: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    headline: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    total_experience_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_title: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    current_company: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    current_ctc_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_ctc_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    currently_serving_notice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Rich jsonb attributes
    work_authorization: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=lambda: {"India": True}, nullable=False
    )
    links: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    educations: Mapped[list["Education"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Experience(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Work experience with verifiable atomic bullet points."""

    __tablename__ = "experiences"

    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    employment_type: Mapped[str] = mapped_column(
        String(32), default="full-time", nullable=False
    )  # full-time | internship | contract
    location: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    start_date: Mapped[str] = mapped_column(String(32), nullable=False)
    end_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Bullets format: list of dicts: {"id": "b1", "text": "...", "skills": [], "metrics": []}
    bullets: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)

    profile: Mapped["Profile"] = relationship(back_populates="experiences")


class Education(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Educational qualifications."""

    __tablename__ = "educations"

    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(128), nullable=False)
    field: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    start_date: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    end_date: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    grade: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # CGPA or percentage
    board: Mapped[str | None] = mapped_column(String(64), nullable=True)  # CBSE / ICSE / State

    profile: Mapped["Profile"] = relationship(back_populates="educations")


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Portfolio projects and open-source contributions."""

    __tablename__ = "projects"

    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    role: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(32), nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="projects")


class Certification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Professional certifications."""

    __tablename__ = "certifications"

    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(128), nullable=False)
    issue_date: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    expiry_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    credential_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    credential_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="certifications")


class Skill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Categorized and verified skills."""

    __tablename__ = "skills"

    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(64), default="technical", nullable=False
    )  # technical | soft | domain | tool
    years: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    proficiency: Mapped[str] = mapped_column(
        String(32), default="intermediate", nullable=False
    )  # beginner | intermediate | advanced | expert
    source: Mapped[str] = mapped_column(
        String(32), default="user", nullable=False
    )  # resume | user | inferred_confirmed

    profile: Mapped["Profile"] = relationship(back_populates="skills")


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Raw uploaded resumes and parser outputs."""

    __tablename__ = "resumes"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(64), default="application/pdf", nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parsed_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    parse_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )  # pending | processing | succeeded | failed
    is_master: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProfileVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable snapshot of the master profile used for reproducible document tailoring."""

    __tablename__ = "profile_versions"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class ProfileEmbedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Semantic pgvector embeddings of user profile facets."""

    __tablename__ = "profile_embeddings"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # full | skills | summary
    embedding = mapped_column(Vector(768), nullable=False)
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profile_versions.id", ondelete="CASCADE"), nullable=False
    )
