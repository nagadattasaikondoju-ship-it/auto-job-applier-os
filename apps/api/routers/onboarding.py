from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.preferences import JobPreference, QuestionnaireSession
from packages.core.models.profile import Profile
from packages.core.services.onboarding import (
    get_next_question_from_state,
    save_onboarding_answer,
)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


class OnboardingAnswerPayload(BaseModel):
    question_id: str
    answer: Any


@router.get("/status")
async def get_onboarding_status(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get current onboarding progression, active step, and answers collected."""
    stmt = select(QuestionnaireSession).where(QuestionnaireSession.user_id == current_user.user_id)
    session = (await db.execute(stmt)).scalar_one_or_none()

    if not session:
        return {
            "status": "pending",
            "current_step": "career_goal",
            "progress_percent": 0,
            "answers": {},
        }

    p_stmt = select(Profile).where(Profile.user_id == current_user.user_id)
    profile = (await db.execute(p_stmt)).scalar_one_or_none()

    pref_stmt = select(JobPreference).where(JobPreference.user_id == current_user.user_id)
    pref = (await db.execute(pref_stmt)).scalar_one_or_none()

    next_q = get_next_question_from_state(session.answers, profile, pref)

    return {
        "status": session.status,
        "current_step": session.current_step,
        "progress_percent": next_q["progress_percent"],
        "completed": next_q["completed"],
        "answers": session.answers,
    }


@router.get("/next-question")
async def get_next_question(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve the next unanswered question based on resume and profile state."""
    stmt = select(QuestionnaireSession).where(QuestionnaireSession.user_id == current_user.user_id)
    session = (await db.execute(stmt)).scalar_one_or_none()
    stored_answers = session.answers if session else {}

    p_stmt = select(Profile).where(Profile.user_id == current_user.user_id)
    profile = (await db.execute(p_stmt)).scalar_one_or_none()

    pref_stmt = select(JobPreference).where(JobPreference.user_id == current_user.user_id)
    pref = (await db.execute(pref_stmt)).scalar_one_or_none()

    return get_next_question_from_state(stored_answers, profile, pref)


@router.post("/answer")
async def submit_question_answer(
    payload: OnboardingAnswerPayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Submit an answer to an onboarding question and route to target fields."""
    answers = await save_onboarding_answer(
        session=db,
        user_id=current_user.user_id,
        question_id=payload.question_id,
        answer_value=payload.answer,
    )
    return {"status": "ok", "answers_recorded": len(answers)}
