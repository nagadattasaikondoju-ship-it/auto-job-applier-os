"""API router for in-app notifications and read state management."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.services.notifications import NotificationsService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve candidate notifications feed with unread count."""
    items, unread_count = await NotificationsService.list_notifications(
        db=db,
        user_id=user.user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
        "unread_count": unread_count,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark a specific notification as read."""
    notif = await NotificationsService.mark_as_read(
        db=db, user_id=user.user_id, notification_id=notification_id
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"id": str(notif.id), "read_at": notif.read_at.isoformat() if notif.read_at else None}


@router.post("/read-all")
async def mark_all_notifications_read(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark all unread notifications for current user as read."""
    count = await NotificationsService.mark_all_read(db=db, user_id=user.user_id)
    return {"marked_read_count": count}
