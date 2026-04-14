"""
Notifications API — JWT-required, user-scoped (010).

Routes (ordered to avoid path param collision):
  GET    /notifications/preferences              — list preferences
  PUT    /notifications/preferences/{type}       — upsert preference
  GET    /notifications/unread-count             — unread count
  PATCH  /notifications/read-all                 — mark all read
  DELETE /notifications/read                     — delete all read
  GET    /notifications/                         — paginated list
  PATCH  /notifications/{id}/read                — mark single read
  DELETE /notifications/{id}                     — delete single
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import Notification, NotificationRead, NotificationType
from src.models.user import User
from src.services.notification_service import notification_service
from src.config.database import get_session
from src.api.deps import get_current_user
from src.middleware.rate_limit import rate_limit_dependency

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# Rate limiters
_read_limiter  = rate_limit_dependency(max_attempts=60, window_seconds=60)
_write_limiter = rate_limit_dependency(max_attempts=10, window_seconds=60)


# ── Preferences (must be before /{id} routes) ─────────────────────────────────

@router.get("/preferences")
async def get_preferences(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(_read_limiter),
):
    """List all notification preferences for the authenticated user."""
    from src.services.preference_service import preference_service
    prefs = await preference_service.get_preferences(session, current_user.id)
    return {"success": True, "data": prefs, "meta": {}}


@router.put("/preferences/{notification_type}")
async def upsert_preference(
    notification_type: NotificationType,
    body: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(_write_limiter),
):
    """Upsert a notification preference. Body: {"enabled": bool}"""
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "Body must contain 'enabled' (bool)."},
        )
    from src.services.preference_service import preference_service
    pref = await preference_service.upsert_preference(
        session, current_user.id, notification_type, enabled
    )
    return {"success": True, "data": pref, "meta": {}}


# ── Unread count (before /{id}) ───────────────────────────────────────────────

@router.get("/unread-count")
async def unread_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(_read_limiter),
):
    count = await notification_service.unread_count(session, current_user.id)
    return {"success": True, "data": {"count": count}, "meta": {}}


# ── Bulk operations (before /{id}) ────────────────────────────────────────────

@router.patch("/read-all")
async def mark_all_read(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(_write_limiter),
):
    updated = await notification_service.mark_all_read(session, current_user.id)
    return {"success": True, "data": {"updated": updated}, "meta": {}}


@router.delete("/read")
async def delete_read_notifications(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(_write_limiter),
):
    """Delete all read notifications for the authenticated user."""
    result = await session.execute(
        delete(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == True,  # noqa: E712
        )
    )
    await session.commit()
    return {"success": True, "data": {"deleted": result.rowcount}, "meta": {}}


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(_read_limiter),
):
    items, total = await notification_service.list_notifications(
        session, current_user.id, page=page, limit=limit, unread_only=unread_only
    )
    return {
        "success": True,
        "data": [NotificationRead.model_validate(n) for n in items],
        "meta": {"total": total, "page": page, "limit": limit, "pages": -(-total // limit) if total else 0},
    }


# ── Single notification operations ────────────────────────────────────────────

@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(_write_limiter),
):
    """Mark a single notification as read. Returns standard envelope."""
    notif = await notification_service.mark_read(session, notification_id, current_user.id)
    return {"success": True, "data": NotificationRead.model_validate(notif), "meta": {}}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(_write_limiter),
):
    """Delete a single notification."""
    notif = await session.get(Notification, notification_id)
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND_NOTIFICATION", "message": "Notification not found."},
        )
    if notif.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "Not your notification."},
        )
    await session.delete(notif)
    await session.commit()
    return {"success": True, "data": None, "meta": {}}
