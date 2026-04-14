"""
Booking System API — all endpoints require JWT authentication.
"""
import uuid
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.booking import (
    BookingRead, BookingCreate, BookingStatus,
    BookingMessageRead, BookingMessageCreate,
)
from src.models.user import User
from src.services.booking_service import booking_service
from src.config.database import get_session
from src.api.deps import get_current_user

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ── Request bodies ────────────────────────────────────────────────────────────

class StatusUpdateBody(BaseModel):
    status: BookingStatus
    reason: Optional[str] = None


class CancelBody(BaseModel):
    reason: Optional[str] = None


# ── Availability ──────────────────────────────────────────────────────────────

@router.get("/availability")
async def check_availability(
    vendor_id: uuid.UUID = Query(...),
    service_id: uuid.UUID = Query(...),
    date: date = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Check if a vendor's service is available on a specific date."""
    result = await booking_service.check_availability(session, vendor_id, service_id, date)
    return {"success": True, "data": result, "meta": {}}


# ── Booking CRUD ──────────────────────────────────────────────────────────────

@router.post("/", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_in: BookingCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new booking for the authenticated user."""
    return await booking_service.create_booking(session, booking_in, current_user.id)


@router.get("/")
async def list_my_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[BookingStatus] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List the authenticated user's bookings with pagination and optional status filter."""
    bookings, total = await booking_service.list_bookings(
        session, current_user.id, page=page, limit=limit, status_filter=status
    )
    return {
        "success": True,
        "data": [BookingRead.model_validate(b) for b in bookings],
        "meta": {"total": total, "page": page, "limit": limit, "pages": -(-total // limit) if total else 0},
    }


@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get booking details by ID."""
    booking = await booking_service.get_by_id(session, booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND_BOOKING", "message": "Booking not found."},
        )
    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "Not authorized to access this booking."},
        )
    return booking


@router.patch("/{booking_id}/status", response_model=BookingRead)
async def update_booking_status(
    booking_id: uuid.UUID,
    body: StatusUpdateBody,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update booking status (state machine validated). Accepts JSON body."""
    return await booking_service.update_status(
        session, booking_id, body.status, current_user.id, reason=body.reason
    )


@router.patch("/{booking_id}/cancel", response_model=BookingRead)
async def cancel_booking(
    booking_id: uuid.UUID,
    body: CancelBody,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending or confirmed booking and release the availability slot."""
    return await booking_service.cancel_booking(
        session, booking_id, current_user.id, reason=body.reason
    )


# ── Messages ──────────────────────────────────────────────────────────────────

@router.post("/{booking_id}/messages", response_model=BookingMessageRead, status_code=status.HTTP_201_CREATED)
async def add_message(
    booking_id: uuid.UUID,
    message_in: BookingMessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Send a message on a booking (client or vendor only)."""
    msg = await booking_service.add_message(session, booking_id, message_in, current_user.id)
    return msg


@router.get("/{booking_id}/messages")
async def list_messages(
    booking_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List messages for a booking in reverse chronological order."""
    messages, total = await booking_service.list_messages(
        session, booking_id, current_user.id, page=page, limit=limit
    )
    return {
        "success": True,
        "data": [BookingMessageRead.model_validate(m) for m in messages],
        "meta": {"total": total, "page": page, "limit": limit, "pages": -(-total // limit) if total else 0},
    }
