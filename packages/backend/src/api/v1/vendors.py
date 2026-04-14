"""
Vendor self-service endpoints.
All routes require JWT authentication.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_current_user
from ...config.database import get_session
from ...models.user import User
from ...models.vendor import Vendor, VendorStatus
from ...schemas.vendor import VendorCreate, VendorUpdate, VendorRead
from ...services.vendor_service import vendor_service
from sqlalchemy import select as sa_select
import structlog

from src.models.booking import Booking, BookingRead, BookingStatus

log = structlog.get_logger()
router = APIRouter(tags=["Vendors"])


@router.post(
    "/register",
    response_model=VendorRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_vendor(
    vendor_in: VendorCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Register the current authenticated user as a marketplace vendor."""
    try:
        vendor = await vendor_service.create_vendor(session, current_user, vendor_in)
        return vendor
    except ValueError as e:
        msg = str(e)
        if msg == "CONFLICT_VENDOR_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "CONFLICT_VENDOR_EXISTS", "message": "A vendor profile already exists for this account."},
            )
        if msg == "CONFLICT_DUPLICATE_VENDOR":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "CONFLICT_DUPLICATE_VENDOR", "message": "A vendor with this business name already exists in this location."},
            )
        if "Invalid category IDs" in msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "VALIDATION_INVALID_CATEGORY", "message": "One or more category IDs are invalid."},
            )
        log.error("vendor.register.failed", error=msg, user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."},
        )


@router.get("/profile/me", response_model=VendorRead)
async def get_my_vendor_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get the current authenticated user's vendor profile."""
    vendor = await vendor_service.get_by_user_id(session, current_user.id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND_VENDOR_PROFILE", "message": "Vendor profile not found."},
        )
    return vendor


@router.put("/profile/me", response_model=VendorRead)
async def update_vendor_profile(
    vendor_in: VendorUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update own vendor profile."""
    from sqlalchemy import select as sa_select

    result = await session.execute(
        sa_select(Vendor).where(Vendor.user_id == current_user.id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND_VENDOR_PROFILE", "message": "Vendor profile not found."},
        )

    try:
        return await vendor_service.update_vendor(session, vendor, vendor_in)
    except ValueError as e:
        msg = str(e)
        if "Invalid category IDs" in msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "VALIDATION_INVALID_CATEGORY", "message": "One or more category IDs are invalid."},
            )
        log.error("vendor.update.failed", error=msg, user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."},
        )


@router.delete("/profile/me")
async def delete_my_vendor_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete (suspend) the current vendor's profile."""
    from sqlalchemy import select as sa_select

    result = await session.execute(
        sa_select(Vendor).where(Vendor.user_id == current_user.id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND_VENDOR_PROFILE", "message": "Vendor profile not found."},
        )

    vendor.status = VendorStatus.SUSPENDED
    await session.commit()

    log.info("vendor.deactivated", vendor_id=str(vendor.id), user_id=str(current_user.id))
    return {"success": True, "data": {"message": "Vendor profile deactivated."}, "meta": {}}


@router.get("/me/bookings")
async def list_vendor_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    booking_status: Optional[BookingStatus] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List bookings for the authenticated vendor."""
    from sqlalchemy import func
    from src.models.vendor import Vendor
    vendor = (await session.execute(sa_select(Vendor).where(Vendor.user_id == current_user.id))).scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND_VENDOR", "message": "Vendor profile not found."})
    base = sa_select(Booking).where(Booking.vendor_id == vendor.id)
    count_q = sa_select(func.count()).select_from(Booking).where(Booking.vendor_id == vendor.id)
    if booking_status:
        base = base.where(Booking.status == booking_status)
        count_q = count_q.where(Booking.status == booking_status)
    total = (await session.execute(count_q)).scalar() or 0
    offset = (page - 1) * limit
    rows = (await session.execute(base.order_by(Booking.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return {
        "success": True,
        "data": [BookingRead.model_validate(b) for b in rows],
        "meta": {"total": total, "page": page, "limit": limit, "pages": -(-total // limit) if total else 0},
    }


class VendorBookingStatusBody(BaseModel):
    status: BookingStatus
    reason: Optional[str] = None

@router.patch("/me/bookings/{booking_id}/status")
async def vendor_update_booking_status(
    booking_id: uuid.UUID,
    body: VendorBookingStatusBody,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Vendor confirms or rejects a booking."""
    from src.models.vendor import Vendor
    from src.services.booking_service import booking_service
    vendor = (await session.execute(sa_select(Vendor).where(Vendor.user_id == current_user.id))).scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND_VENDOR", "message": "Vendor profile not found."})
    booking = await session.get(Booking, booking_id)
    if not booking or booking.vendor_id != vendor.id:
        raise HTTPException(status_code=403, detail={"code": "AUTH_FORBIDDEN", "message": "Not your booking."})
    updated = await booking_service.update_status(session, booking_id, body.status, current_user.id, reason=body.reason)
    return {"success": True, "data": BookingRead.model_validate(updated), "meta": {}}