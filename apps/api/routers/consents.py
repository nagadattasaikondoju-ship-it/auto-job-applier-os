import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.platform import Consent

router = APIRouter(prefix="/consents", tags=["Consents"])


class ConsentPayload(BaseModel):
    purpose: str  # profile_matching | document_generation | auto_submit
    version: str = "v1"
    granted: bool = True


@router.get("")
async def get_consents(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Current state of each DPDP consent purpose."""
    from packages.core.services.autopilot import active_consents

    state = await active_consents(db, current_user.user_id)
    purposes = ["profile_matching", "document_generation", "auto_submit"]
    return {"consents": {p: state.get(p, False) for p in purposes}}


@router.post("")
async def grant_consent(
    payload: ConsentPayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Grant or withdraw DPDP explicit data processing consent."""
    consent = Consent(
        id=uuid.uuid4(),
        user_id=current_user.user_id,
        purpose=payload.purpose,
        version=payload.version,
        granted_at=datetime.utcnow(),
        withdrawn_at=None if payload.granted else datetime.utcnow(),
    )
    db.add(consent)
    await db.commit()
    return {
        "status": "recorded",
        "purpose": payload.purpose,
        "granted": payload.granted,
        "consent_id": str(consent.id),
    }
