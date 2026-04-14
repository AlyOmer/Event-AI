"""
Event Management API — CRUD for events and event types.

All routes require JWT authentication unless noted.
Rate limits: 10/min for create/duplicate, 60/min for reads.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, require_admin
from src.config.database import get_session
from src.models.event import Event, EventType, EventStatus
from src.models.booking import BookingStatus, BookingRead
from src.models.user import User
from src.schemas.event import (
    EventCreate,
    EventUpdate,
    EventCancel,
    EventRead,
    EventStatusUpdate,
    EventTypeCreate,
    EventTypeUpdate,
    EventTypeRead,
)
from src.services.event_service import event_service
from src.middleware.rate_limit import rate_limit_dependency
import structlog

log = structlog.get_logger()
router = APIRouter(tags=["Events"])

# ── Rate limiters ─────────────────────────────────────────────────────────────
create_limiter = rate_limit_dependency(max_attempts=10, window_seconds=60)
read_limiter   = rate_limit_dependency(max_attempts=60, window_seconds=60)


# ── Event Types ───────────────────────────────────────────────────────────────

@router.get("/types")
async def list_event_types(
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(read_limiter),
):
    """List event types. Returns active types only by default."""
    stmt = select(EventType).order_by(EventType.display_order)
    if not include_inactive:
        stmt = stmt.where(EventType.is_active == True)
    result = await session.execute(stmt)
    types = result.scalars().all()
    return {"success": True, "data": [EventTypeRead.model_validate(t) for t in types], "meta": {}}


@router.post("/types", status_code=status.HTTP_201_CREATED)
async def create_event_type(
    et_in: EventTypeCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin: Create a new event type."""
    existing = await session.execute(
        select(EventType).where(EventType.name.ilike(et_in.name))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT_EVENT_TYPE_EXISTS", "message": f"Event type '{et_in.name}' already exists."},
        )
    et = EventType(**et_in.model_dump())
    session.add(et)
    await session.commit()
    await session.refresh(et)
    log.info("event_type.created", id=str(et.id), admin_id=str(current_user.id))
    return {"success": True, "data": EventTypeRead.model_validate(et), "meta": {}}


@router.put("/types/{type_id}")
async def update_event_type(
    type_id: uuid.UUID,
    et_in: EventTypeUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin: Update an event type."""
    et = await session.get(EventType, type_id)
    if not et:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND_EVENT_TYPE", "message": "Event type not found."},
        )
    for field, value in et_in.model_dump(exclude_unset=True).items():
        setattr(et, field, value)
    et.updated_at = datetime.now()
    await session.commit()
    await session.refresh(et)
    log.info("event_type.updated", id=str(et.id), admin_id=str(current_user.id))
    return {"success": True, "data": EventTypeRead.model_validate(et), "meta": {}}


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_event_type(
    type_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin: Deactivate an event type (soft-delete)."""
    et = await session.get(EventType, type_id)
    if not et:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND_EVENT_TYPE", "message": "Event type not found."},
        )
    count_result = await session.execute(
        select(func.count()).select_from(Event).where(
            Event.event_type_id == type_id,
            Event.status.notin_(["completed", "canceled"]),
        )
    )
    if (count_result.scalar() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT_EVENT_TYPE_IN_USE", "message": "Cannot deactivate: active events use this type."},
        )
    et.is_active = False
    await session.commit()
    log.info("event_type.deactivated", id=str(type_id), admin_id=str(current_user.id))


# ── Admin: all events ─────────────────────────────────────────────────────────

@router.get("/admin/all")
async def list_all_events_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[EventStatus] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    city: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(read_limiter),
):
    """Admin: List all events across all users with optional filters."""
    events, total = await event_service.list_all_events_admin(
        session, page=page, limit=limit,
        status=status, user_id=user_id, city=city,
        date_from=date_from, date_to=date_to,
    )
    pages = -(-total // limit) if total else 0
    return {
        "success": True,
        "data": [EventRead.model_validate(e) for e in events],
        "meta": {"total": total, "page": page, "limit": limit, "pages": pages},
    }


# ── Events CRUD ───────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(create_limiter),
):
    """Create a new event for the authenticated user."""
    event = await event_service.create_event(session, event_in, current_user.id)
    return {"success": True, "data": EventRead.model_validate(event), "meta": {}}


@router.get("/")
async def list_my_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[EventStatus] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(read_limiter),
):
    """List the authenticated user's events with pagination and optional status filter."""
    events, total = await event_service.list_events(
        session, current_user.id, page=page, limit=limit, status_filter=status
    )
    pages = -(-total // limit) if total else 0
    return {
        "success": True,
        "data": [EventRead.model_validate(e) for e in events],
        "meta": {"total": total, "page": page, "limit": limit, "pages": pages},
    }


@router.get("/{event_id}")
async def get_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(read_limiter),
):
    """Get a single event by ID."""
    event = await event_service.get_event(session, event_id, current_user.id)
    return {"success": True, "data": EventRead.model_validate(event), "meta": {}}


@router.put("/{event_id}")
async def update_event(
    event_id: uuid.UUID,
    event_in: EventUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update an event's fields."""
    event = await event_service.update_event(session, event_id, event_in, current_user.id)
    return {"success": True, "data": EventRead.model_validate(event), "meta": {}}


@router.patch("/{event_id}/status")
async def update_event_status(
    event_id: uuid.UUID,
    body: EventStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Explicitly transition an event's status via the state machine."""
    event = await event_service.get_event(session, event_id, current_user.id)
    event = await event_service.transition_status(
        session, event, body.status, current_user.id, reason=body.reason
    )
    return {"success": True, "data": EventRead.model_validate(event), "meta": {}}


@router.delete("/{event_id}")
async def cancel_event(
    event_id: uuid.UUID,
    body: EventCancel = EventCancel(),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cancel an event (transitions to CANCELED status)."""
    event = await event_service.cancel_event(
        session, event_id, current_user.id, reason=body.reason
    )
    return {"success": True, "data": EventRead.model_validate(event), "meta": {}}


@router.post("/{event_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(create_limiter),
):
    """Clone an event with status=DRAFT and name='Copy of ...'."""
    event = await event_service.duplicate_event(session, event_id, current_user.id)
    return {"success": True, "data": EventRead.model_validate(event), "meta": {}}


@router.get("/{event_id}/bookings")
async def list_event_bookings(
    event_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[BookingStatus] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(read_limiter),
):
    """List all bookings associated with a specific event."""
    bookings, total = await event_service.list_event_bookings(
        session, event_id, current_user.id, page=page, limit=limit, status_filter=status
    )
    pages = -(-total // limit) if total else 0
    return {
        "success": True,
        "data": [BookingRead.model_validate(b) for b in bookings],
        "meta": {"total": total, "page": page, "limit": limit, "pages": pages},
    }
