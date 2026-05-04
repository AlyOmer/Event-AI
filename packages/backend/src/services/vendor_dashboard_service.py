"""
VendorDashboardService — aggregates booking and service stats for the vendor dashboard.
"""
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import structlog

from ..models.booking import Booking, BookingStatus
from ..models.service import Service
from ..schemas.vendor_dashboard import DashboardStats, RecentBookingItem

logger = structlog.get_logger()


class VendorDashboardService:

    async def get_dashboard_stats(
        self, session: AsyncSession, vendor_id: uuid.UUID
    ) -> DashboardStats:
        """
        Return aggregated dashboard stats for a vendor in a minimal number of DB round-trips.
        """
        # --- Booking counts ---
        total_bookings: int = (
            await session.execute(
                select(func.count()).select_from(Booking).where(Booking.vendor_id == vendor_id)
            )
        ).scalar() or 0

        pending_bookings: int = (
            await session.execute(
                select(func.count())
                .select_from(Booking)
                .where(Booking.vendor_id == vendor_id, Booking.status == BookingStatus.pending)
            )
        ).scalar() or 0

        confirmed_bookings: int = (
            await session.execute(
                select(func.count())
                .select_from(Booking)
                .where(Booking.vendor_id == vendor_id, Booking.status == BookingStatus.confirmed)
            )
        ).scalar() or 0

        # --- Service counts ---
        active_services: int = (
            await session.execute(
                select(func.count())
                .select_from(Service)
                .where(Service.vendor_id == vendor_id, Service.is_active == True)  # noqa: E712
            )
        ).scalar() or 0

        total_services: int = (
            await session.execute(
                select(func.count())
                .select_from(Service)
                .where(Service.vendor_id == vendor_id)
            )
        ).scalar() or 0

        # --- 5 most recent bookings (with service name via join) ---
        recent_rows = (
            await session.execute(
                select(Booking, Service.name.label("service_name"))
                .outerjoin(Service, Booking.service_id == Service.id)
                .where(Booking.vendor_id == vendor_id)
                .order_by(Booking.created_at.desc())
                .limit(5)
            )
        ).all()

        recent_bookings = [
            RecentBookingItem(
                id=row.Booking.id,
                service_name=row.service_name,
                event_date=row.Booking.event_date,
                status=row.Booking.status,
                total_price=row.Booking.total_price,
                currency=row.Booking.currency,
                client_name=row.Booking.client_name,
            )
            for row in recent_rows
        ]

        logger.info(
            "vendor.dashboard.stats_fetched",
            vendor_id=str(vendor_id),
            total_bookings=total_bookings,
        )

        return DashboardStats(
            total_bookings=total_bookings,
            pending_bookings=pending_bookings,
            confirmed_bookings=confirmed_bookings,
            active_services=active_services,
            total_services=total_services,
            recent_bookings=recent_bookings,
        )


vendor_dashboard_service = VendorDashboardService()
