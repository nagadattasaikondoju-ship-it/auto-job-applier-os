"""API router for candidate analytics, velocity overview, and conversion funnel."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_analytics_overview(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve comprehensive application status breakdown, credit stats, and AI spend."""
    return await AnalyticsService.get_user_overview(db=db, user_id=user.user_id)


@router.get("/funnel")
async def get_conversion_funnel(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve end-to-end job application conversion rates from discovery to offers."""
    return await AnalyticsService.get_conversion_funnel(db=db, user_id=user.user_id)
