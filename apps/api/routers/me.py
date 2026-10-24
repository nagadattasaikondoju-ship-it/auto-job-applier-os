from typing import Any

from fastapi import APIRouter, Depends

from apps.api.deps.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/me", tags=["User"])


@router.get("")
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the profile and session metadata for the currently authenticated user."""
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "claims": current_user.claims,
    }
