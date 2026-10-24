"""initial schema with pgvector, indexes, and rls

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-24 12:40:00.000000

"""

from collections.abc import Sequence

import pgvector
import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable required PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Identity & Billing
    op.create_table(
        "users_meta",
        sa.Column("user_id", sa.String(128), primary_key=True),
        sa.Column("plan", sa.String(32), server_default="free", nullable=False),
        sa.Column("onboarding_status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("consent_version", sa.String(32), nullable=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "marketing_opt_in", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("timezone", sa.String(64), server_default="Asia/Kolkata", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "subscriptions",
        sa.Column("user_id", sa.String(128), primary_key=True),
        sa.Column("plan", sa.String(32), server_default="free", nullable=False),
        sa.Column("razorpay_subscription_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "credits_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("credit_type", sa.String(16), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(128), nullable=False),
        sa.Column("ref_type", sa.String(64), nullable=True),
        sa.Column("ref_id", sa.String(128), nullable=True),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "credit_holds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("credit_type", sa.String(16), server_default="apply", nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(128), nullable=False, index=True),
        sa.Column("status", sa.String(32), server_default="held", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 3. Profile & Resumes
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.String(128), primary_key=True),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), server_default="", nullable=False),
        sa.Column("city", sa.String(128), server_default="", nullable=False),
        sa.Column("state", sa.String(128), server_default="", nullable=False),
        sa.Column("country", sa.String(64), server_default="India", nullable=False),
        sa.Column("pincode", sa.String(16), server_default="", nullable=False),
        sa.Column("headline", sa.String(255), server_default="", nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("total_experience_months", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_title", sa.String(128), server_default="", nullable=False),
        sa.Column("current_company", sa.String(128), server_default="", nullable=False),
        sa.Column("current_ctc_lpa", sa.Float(), nullable=True),
        sa.Column("expected_ctc_lpa", sa.Float(), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column(
            "currently_serving_notice",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "willing_to_relocate", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("gender", sa.String(32), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column(
            "work_authorization",
            postgresql.JSONB(),
            server_default='{"India": true}',
            nullable=False,
        ),
        sa.Column("links", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("languages", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "experiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(128),
            sa.ForeignKey("profiles.user_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("company", sa.String(128), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("employment_type", sa.String(32), server_default="full-time", nullable=False),
        sa.Column("location", sa.String(128), server_default="", nullable=False),
        sa.Column("start_date", sa.String(32), nullable=False),
        sa.Column("end_date", sa.String(32), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("bullets", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "educations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(128),
            sa.ForeignKey("profiles.user_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("institution", sa.String(255), nullable=False),
        sa.Column("degree", sa.String(128), nullable=False),
        sa.Column("field", sa.String(128), server_default="", nullable=False),
        sa.Column("start_date", sa.String(32), server_default="", nullable=False),
        sa.Column("end_date", sa.String(32), server_default="", nullable=False),
        sa.Column("grade", sa.String(32), server_default="", nullable=False),
        sa.Column("board", sa.String(64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(128),
            sa.ForeignKey("profiles.user_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("role", sa.String(128), server_default="", nullable=False),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("skills", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("start_date", sa.String(32), nullable=True),
        sa.Column("end_date", sa.String(32), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(128),
            sa.ForeignKey("profiles.user_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(128), nullable=False),
        sa.Column("issue_date", sa.String(32), server_default="", nullable=False),
        sa.Column("expiry_date", sa.String(32), nullable=True),
        sa.Column("credential_id", sa.String(128), nullable=True),
        sa.Column("credential_url", sa.String(512), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(128),
            sa.ForeignKey("profiles.user_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("normalized_name", sa.String(64), nullable=False, index=True),
        sa.Column("category", sa.String(64), server_default="technical", nullable=False),
        sa.Column("years", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("proficiency", sa.String(32), server_default="intermediate", nullable=False),
        sa.Column("source", sa.String(32), server_default="user", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(64), server_default="application/pdf", nullable=False),
        sa.Column("raw_text", sa.Text(), server_default="", nullable=False),
        sa.Column("parsed_json", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("parse_status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("is_master", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "profile_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "profile_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(768), nullable=False),
        sa.Column(
            "profile_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 4. Questionnaire & Answer Bank
    op.create_table(
        "questionnaire_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("status", sa.String(32), server_default="in_progress", nullable=False),
        sa.Column("current_step", sa.String(64), server_default="career_goal", nullable=False),
        sa.Column("answers", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "job_preferences",
        sa.Column("user_id", sa.String(128), primary_key=True),
        sa.Column("target_roles", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("role_keywords", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("seniority", sa.String(32), server_default="fresher", nullable=False),
        sa.Column("min_exp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_exp", sa.Integer(), server_default="2", nullable=False),
        sa.Column("locations", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "remote_mode",
            postgresql.JSONB(),
            server_default='["remote", "hybrid", "onsite"]',
            nullable=False,
        ),
        sa.Column("min_salary_lpa", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("company_size", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("industries", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("excluded_companies", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("excluded_keywords", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "employment_types", postgresql.JSONB(), server_default='["full-time"]', nullable=False
        ),
        sa.Column(
            "visa_sponsorship_needed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("daily_application_limit", sa.Integer(), server_default="10", nullable=False),
        sa.Column(
            "auto_submit_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("min_match_score", sa.Integer(), server_default="70", nullable=False),
        sa.Column("learned_weights", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "answer_bank",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("question_key", sa.String(128), nullable=False, index=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("answer_type", sa.String(32), server_default="short", nullable=False),
        sa.Column("source", sa.String(32), server_default="questionnaire", nullable=False),
        sa.Column("times_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(768), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "answer_edits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("original_answer", sa.Text(), nullable=False),
        sa.Column("edited_answer", sa.Text(), nullable=False),
        sa.Column(
            "used_for_personalization", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 5. Companies, Jobs & Preferences Buckets
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False, index=True),
        sa.Column("domain", sa.String(255), server_default="", nullable=False, index=True),
        sa.Column("careers_url", sa.String(512), server_default="", nullable=False),
        sa.Column("ats_type", sa.String(64), server_default="unknown", nullable=False),
        sa.Column("ats_board_token", sa.String(128), nullable=True),
        sa.Column("country", sa.String(64), server_default="India", nullable=False),
        sa.Column("size", sa.String(64), nullable=True),
        sa.Column("industry", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("crawl_interval_minutes", sa.Integer(), server_default="360", nullable=False),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("normalized_title", sa.String(255), nullable=False, index=True),
        sa.Column("seniority", sa.String(32), server_default="fresher", nullable=False),
        sa.Column("location_raw", sa.String(255), server_default="", nullable=False),
        sa.Column("locations", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("country", sa.String(64), server_default="India", nullable=False),
        sa.Column("remote_mode", sa.String(32), server_default="onsite", nullable=False),
        sa.Column("employment_type", sa.String(32), server_default="full-time", nullable=False),
        sa.Column("description_html", sa.Text(), server_default="", nullable=False),
        sa.Column("description_text", sa.Text(), server_default="", nullable=False),
        sa.Column("salary_min_lpa", sa.Float(), nullable=True),
        sa.Column("salary_max_lpa", sa.Float(), nullable=True),
        sa.Column("salary_currency", sa.String(8), server_default="INR", nullable=False),
        sa.Column("experience_min", sa.Integer(), server_default="0", nullable=False),
        sa.Column("experience_max", sa.Integer(), server_default="30", nullable=False),
        sa.Column("required_skills", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("application_url", sa.String(1024), nullable=False),
        sa.Column("ats_type", sa.String(64), server_default="unknown", nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False, index=True
        ),
        sa.Column("content_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("quality_score", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_suspicious", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "job_embeddings",
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(768), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "job_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alias_source", sa.String(64), nullable=False),
        sa.Column("alias_external_id", sa.String(255), nullable=False),
        sa.Column("alias_url", sa.String(1024), nullable=False),
        sa.Column(
            "canonical_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "preference_buckets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bucket_key", sa.String(128), nullable=False, index=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "job_form_schemas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ats_type", sa.String(64), nullable=False),
        sa.Column("schema_json", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("extraction_method", sa.String(32), server_default="api", nullable=False),
        sa.Column(
            "extracted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(32), server_default="ready", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "ats_flows",
        sa.Column("ats_type", sa.String(64), primary_key=True),
        sa.Column("flow_version", sa.String(32), server_default="v1", nullable=False),
        sa.Column("trusted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("success_rate_7d", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 6. Matching & Documents
    op.create_table(
        "job_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "profile_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filter_passed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("vector_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("match_score", sa.Integer(), server_default="0", nullable=False, index=True),
        sa.Column("decision", sa.String(16), server_default="skip", nullable=False),
        sa.Column("fit_reasons", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("gaps", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("resume_focus", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("risk_flags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("model", sa.String(64), server_default="", nullable=False),
        sa.Column("prompt_version", sa.String(32), server_default="v1", nullable=False),
        sa.Column("user_feedback", sa.String(16), nullable=True),
        sa.Column("status", sa.String(32), server_default="new", nullable=False, index=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "job_id", "profile_version_id", name="uq_user_job_match"),
    )

    op.create_table(
        "resume_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "profile_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_json", postgresql.JSONB(), nullable=False),
        sa.Column("template_id", sa.String(64), server_default="classic_ats", nullable=False),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.Column("truth_check_status", sa.String(32), server_default="passed", nullable=False),
        sa.Column("flagged_claims", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("version_no", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "cover_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "screening_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("field_key", sa.String(128), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("source", sa.String(32), server_default="answer_bank", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 7. Campaigns, Applications & Automation
    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("name", sa.String(128), server_default="Default Autopilot", nullable=False),
        sa.Column("preferences_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("mode", sa.String(32), server_default="review", nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("daily_limit", sa.Integer(), server_default="10", nullable=False),
        sa.Column(
            "schedule",
            postgresql.JSONB(),
            server_default='{"windows": ["09:00-18:00"]}',
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("stats", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "resume_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resume_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cover_letter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cover_letters.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status", sa.String(32), server_default="ready_for_review", nullable=False, index=True
        ),
        sa.Column("channel", sa.String(32), server_default="extension", nullable=False),
        sa.Column("application_url", sa.String(1024), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("automation_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "job_id", name="uq_user_job_application"),
    )

    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("actor", sa.String(32), server_default="system", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )

    op.create_table(
        "automation_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("queue", sa.String(64), server_default="browser_automation", nullable=False),
        sa.Column("celery_task_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "automation_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "automation_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automation_tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("screenshot_path", sa.String(512), nullable=True),
        sa.Column("html_snapshot_path", sa.String(512), nullable=True),
        sa.Column("log", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 8. Platform Observability & Notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("channels", postgresql.JSONB(), server_default='["in_app"]', nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )

    op.create_table(
        "ai_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("feature", sa.String(64), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("tokens_in", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_out", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_estimate_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cached", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )

    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False, index=True),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), server_default="v1", nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(64), nullable=False, index=True),
        sa.Column("user_id", sa.String(128), nullable=True, index=True),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False, index=True),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("result_ref", postgresql.JSONB(), nullable=True),
        sa.Column("error", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("rules", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 9. High-Performance Indexes (Section 4 & Section 23 of ARCHITECTURE.md)
    # HNSW Index on job_embeddings
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_embeddings_hnsw "
        "ON job_embeddings USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )

    # Trigram index on jobs.normalized_title
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_normalized_title_trgm "
        "ON jobs USING gin (normalized_title gin_trgm_ops);"
    )

    # Partial index on active applications awaiting review
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_applications_review_queue "
        "ON applications (status, updated_at DESC) "
        "WHERE status IN ('ready_for_review', 'needs_user_action');"
    )

    # 10. Enable Row Level Security (Defense-in-depth as per spec)
    user_owned_tables = [
        "users_meta",
        "subscriptions",
        "credits_ledger",
        "credit_holds",
        "profiles",
        "experiences",
        "educations",
        "projects",
        "certifications",
        "skills",
        "resumes",
        "profile_versions",
        "profile_embeddings",
        "questionnaire_sessions",
        "job_preferences",
        "answer_bank",
        "answer_edits",
        "job_matches",
        "resume_versions",
        "cover_letters",
        "screening_answers",
        "campaigns",
        "applications",
        "application_events",
        "notifications",
        "ai_usage",
        "consents",
        "tasks",
    ]
    for tbl in user_owned_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    pass
