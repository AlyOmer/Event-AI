"""
Admin Platform Stats API

GET / — returns aggregate platform statistics in a single DB round-trip.
Mounted at /api/v1/admin/stats in main.py.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from src.api.deps import require_admin
from src.config.database import get_session
from src.models.user import User
from src.models.vendor import Vendor, VendorStatus
from src.models.booking import Booking, BookingStatus
from src.schemas.admin import AdminStatsResponse

import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["Admin Stats"])


@router.get("/", response_model=None)
async def get_platform_stats(
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Admin-only: Return platform-wide aggregate counts in a single DB round-trip.

    Uses scalar subqueries to avoid Cartesian product inflation across
    independent tables (User, Vendor, Booking).
    """
    stats = await session.execute(
        select(
            select(func.count())
            .where(User.is_active == True)  # noqa: E712
            .scalar_subquery()
            .label("total_users"),
            select(func.count())
            .where(Vendor.status == VendorStatus.ACTIVE)
            .scalar_subquery()
            .label("active_vendors"),
            select(func.count())
            .where(Vendor.status == VendorStatus.PENDING)
            .scalar_subquery()
            .label("pending_vendors"),
            select(func.count())
            .select_from(Booking)
            .scalar_subquery()
            .label("total_bookings"),
            select(func.count())
            .where(Booking.status == BookingStatus.confirmed)
            .scalar_subquery()
            .label("confirmed_bookings"),
            select(func.count())
            .where(Booking.status == BookingStatus.pending)
            .scalar_subquery()
            .label("pending_bookings"),
            select(func.coalesce(func.sum(Booking.total_price), 0.0))
            .where(
                Booking.status.in_(
                    [BookingStatus.confirmed, BookingStatus.completed]
                )
            )
            .scalar_subquery()
            .label("total_revenue"),
        )
    )
    row = stats.one()

    data = AdminStatsResponse(
        totalUsers=row.total_users,
        activeVendors=row.active_vendors,
        pendingVendors=row.pending_vendors,
        totalBookings=row.total_bookings,
        confirmedBookings=row.confirmed_bookings,
        pendingBookings=row.pending_bookings,
        totalRevenue=float(row.total_revenue),
    )

    logger.info(
        "admin.stats.fetched",
        admin_id=str(current_user.id),
        total_users=data.totalUsers,
        total_bookings=data.totalBookings,
    )

    return {
        "success": True,
        "data": data.model_dump(),
        "meta": {},
    }
