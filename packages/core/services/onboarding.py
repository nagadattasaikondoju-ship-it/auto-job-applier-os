import json
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.preferences import (
    AnswerBank,
    JobPreference,
    QuestionnaireSession,
)
from packages.core.models.profile import Profile

# Load versioned questionnaire definitions
_QUESTIONNAIRE_PATH = Path(__file__).parent.parent / "questionnaire" / "v1.json"


def load_questionnaire_definition() -> dict[str, Any]:
    with open(_QUESTIONNAIRE_PATH, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def get_next_question_from_state(
    stored_answers: dict[str, Any],
    profile: Profile | None = None,
    preferences: JobPreference | None = None,
) -> dict[str, Any]:
    """Find the next unanswered question from the adaptive questionnaire engine."""
    q_data = load_questionnaire_definition()
    all_questions = []
    for section in q_data.get("sections", []):
        all_questions.extend(section.get("questions", []))

    total = len(all_questions)
    answered_count = 0

    for question in all_questions:
        q_id = question["id"]
        canonical_key = question["canonical_key"]

        # Check if already answered in this session
        if q_id in stored_answers:
            answered_count += 1
            continue

        # Check if already populated from uploaded resume into profile
        if profile and hasattr(profile, canonical_key):
            val = getattr(profile, canonical_key)
            if val is not None and val != "":
                answered_count += 1
                continue

        # Check if already populated in preferences
        if preferences and hasattr(preferences, canonical_key):
            val = getattr(preferences, canonical_key)
            if val is not None and val != []:
                answered_count += 1
                continue

        # Found next question!
        progress = int((answered_count / total) * 100) if total > 0 else 0
        return {
            "completed": False,
            "progress_percent": progress,
            "question": question,
        }

    return {
        "completed": True,
        "progress_percent": 100,
        "question": None,
    }


async def save_onboarding_answer(
    session: AsyncSession,
    user_id: str,
    question_id: str,
    answer_value: Any,
) -> dict[str, Any]:
    """Persist an onboarding answer and route to profile/preferences/answer_bank."""
    # 1. Update session
    stmt = select(QuestionnaireSession).where(QuestionnaireSession.user_id == user_id)
    res = await session.execute(stmt)
    q_session = res.scalar_one_or_none()

    if not q_session:
        q_session = QuestionnaireSession(
            user_id=user_id,
            status="in_progress",
            current_step=question_id,
            answers={question_id: answer_value},
        )
        session.add(q_session)
    else:
        current_answers = dict(q_session.answers)
        current_answers[question_id] = answer_value
        q_session.answers = current_answers
        q_session.current_step = question_id

    # 2. Look up question spec for target table routing
    q_data = load_questionnaire_definition()
    target_q = None
    for section in q_data.get("sections", []):
        for q in section.get("questions", []):
            if q["id"] == question_id:
                target_q = q
                break

    if target_q:
        table = target_q.get("target_table")
        _field = target_q.get("target_field")

        if table == "answer_bank":
            # Upsert into answer_bank
            ans_stmt = select(AnswerBank).where(
                AnswerBank.user_id == user_id,
                AnswerBank.question_key == target_q["canonical_key"],
            )
            ans_res = await session.execute(ans_stmt)
            existing_ans = ans_res.scalar_one_or_none()

            ans_text = str(answer_value)
            if not existing_ans:
                new_ans = AnswerBank(
                    user_id=user_id,
                    question_key=target_q["canonical_key"],
                    question_text=target_q["text"],
                    answer_text=ans_text,
                    answer_type="short" if target_q["type"] != "long_text" else "long",
                    source="questionnaire",
                )
                session.add(new_ans)
            else:
                existing_ans.answer_text = ans_text

    await session.commit()
    return q_session.answers
