"""Close jobs whose apply link points to a private or internal address.

Before job import refused such links (SSRF fix), a security audit imported two probe URLs
(127.0.0.1 and the 169.254.169.254 metadata address). Deactivate any job like that so it never
appears in feeds or gets applied to.

Revision ID: 002_close_internal_url_jobs
Revises: 001_initial_schema
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_close_internal_url_jobs"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INTERNAL_URL = (
    r"^[a-z]+://(localhost|127\.|10\.|0\.|169\.254\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|\[)"
)


def upgrade() -> None:
    op.execute(
        f"UPDATE jobs SET is_active = false WHERE is_active AND application_url ~* '{INTERNAL_URL}'"
    )


def downgrade() -> None:
    pass  # data cleanup; nothing to restore
