"""Salary, notice and relocation answers given before the user has a profile.

They live on the Profile, but people who set preferences before uploading a resume have none yet.
Until then the answers wait in the questionnaire session and are copied over when the profile is created.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.preferences import QuestionnaireSession
from packages.core.models.profile import Profile

LOGISTICS_FIELDS = (
    "notice_period_days",
    "current_ctc_lpa",
    "expected_ctc_lpa",
    "willing_to_relocate",
)
_KEY = "pending_logistics"


async def _session(db: AsyncSession, user_id: str) -> QuestionnaireSession | None:
    stmt = (
        select(QuestionnaireSession)
        .where(QuestionnaireSession.user_id == user_id)
        .order_by(QuestionnaireSession.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def pending_logistics(db: AsyncSession, user_id: str) -> dict[str, Any]:
    session = await _session(db, user_id)
    return dict((session.answers or {}).get(_KEY) or {}) if session else {}


async def stash_logistics(db: AsyncSession, user_id: str, values: dict[str, Any]) -> None:
    session = await _session(db, user_id)
    if session is None:
        session = QuestionnaireSession(user_id=user_id, answers={})
        db.add(session)
    merged = {
        **((session.answers or {}).get(_KEY) or {}),
        **{k: v for k, v in values.items() if v is not None},
    }
    session.answers = {
        **(session.answers or {}),
        _KEY: merged,
    }  # reassign so the JSONB change is saved


async def apply_pending_logistics(db: AsyncSession, profile: Profile) -> None:
    """Copy answers given before the profile existed onto it (values already on the profile win)."""
    pending = await pending_logistics(db, profile.user_id)
    for field in LOGISTICS_FIELDS:
        if (
            field in pending
            and pending[field] is not None
            and getattr(profile, field, None) in (None, 30, True)
        ):
            # 30 days / willing=True are column defaults, so a stated answer replaces them
            setattr(profile, field, pending[field])
