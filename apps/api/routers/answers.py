import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.preferences import AnswerBank

router = APIRouter(prefix="/answers", tags=["Answer Bank"])


class AnswerCreateSchema(BaseModel):
    question_key: str
    question_text: str
    answer_text: str
    answer_type: str = "short"


@router.get("")
async def list_answers(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all stored answers in the user's answer bank."""
    stmt = select(AnswerBank).where(AnswerBank.user_id == current_user.user_id)
    answers = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(a.id),
            "question_key": a.question_key,
            "question_text": a.question_text,
            "answer_text": a.answer_text,
            "answer_type": a.answer_type,
            "source": a.source,
            "times_used": a.times_used,
        }
        for a in answers
    ]


@router.post("")
async def upsert_answer(
    payload: AnswerCreateSchema,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add or update an answer in the user's answer bank."""
    stmt = select(AnswerBank).where(
        AnswerBank.user_id == current_user.user_id,
        AnswerBank.question_key == payload.question_key,
    )
    ans = (await db.execute(stmt)).scalar_one_or_none()

    if not ans:
        ans = AnswerBank(
            id=uuid.uuid4(),
            user_id=current_user.user_id,
            question_key=payload.question_key,
            question_text=payload.question_text,
            answer_text=payload.answer_text,
            answer_type=payload.answer_type,
            source="user_edit",
        )
        db.add(ans)
    else:
        ans.answer_text = payload.answer_text
        ans.source = "user_edit"

    await db.commit()
    return {"id": str(ans.id), "status": "saved"}
