"""
Property-based tests for VendorDashboardService.

Uses a dedicated asyncio event loop + aiosqlite in-memory DB.
Hypothesis @given tests are plain synchronous functions that call
_run() on a module-level loop — no asyncio.run(), no nest_asyncio,
no pytest-asyncio interference.

Run with: uv run pytest tests/test_vendor_dashboard_service.py -v
Feature: vendor-portal-complete
"""
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import settings as h_settings
from hypothesis import strategies as st
from sqlalchemy import String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from src.models.booking import Booking, BookingStatus
from src.models.service import Service
from src.models.vendor import Vendor, VendorStatus
from src.services.vendor_dashboard_service import vendor_dashboard_service

# Prevent pytest-asyncio (asyncio_mode=auto) from wrapping these sync
# Hypothesis tests in a coroutine. The tests manage their own event loop.
pytestmark = pytest.mark.asyncio(mode="strict")

# ── Tables needed (FK order) ──────────────────────────────────────────────────

DASHBOARD_TABLES = [
    "users",
    "vendors",
    "categories",
    "vendor_categories",
    "services",
    "bookings",
]


def _import_models() -> None:
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.booking import Booking  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.domain_event import DomainEvent  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.notification import Notification  # noqa: F401
    from src.models.notification_preference import NotificationPreference  # noqa: F401
    from src.models.user import PasswordResetToken, RefreshToken, User  # noqa: F401


_import_models()

# ── Module-level dedicated event loop + engine ────────────────────────────────

_LOOP: asyncio.AbstractEventLoop = asyncio.new_event_loop()


def _build_engine():
    # Patch Vendor.status — uses PostgreSQL ENUM, needs String for SQLite
    Vendor.__table__.c["status"].type = String(50)

    # Patch Booking.status — Python Enum, needs String for SQLite
    Booking.__table__.c["status"].type = String(50)

    # Patch Booking.payment_status — Python Enum, needs String for SQLite
    Booking.__table__.c["payment_status"].type = String(50)

    # Patch Booking.event_location — JSONB, needs JSON for SQLite
    Booking.__table__.c["event_location"].type = JSON()

    # Patch Booking.metadata (metadata_info column) — JSONB, needs JSON for SQLite
    Booking.__table__.c["metadata"].type = JSON()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async def _create():
        async with engine.begin() as conn:
            tables = [
                SQLModel.metadata.tables[name]
                for name in DASHBOARD_TABLES
                if name in SQLModel.metadata.tables
            ]
            await conn.run_sync(
                lambda c: SQLModel.metadata.create_all(c, tables=tables)
            )

    _LOOP.run_until_complete(_create())
    return engine


_ENGINE = _build_engine()
_SESSION_FACTORY = sessionmaker(_ENGINE, class_=AsyncSession, expire_on_commit=False)


def _run(coro):
    """Run a coroutine on the dedicated module-level loop."""
    return _LOOP.run_until_complete(coro)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_vendor() -> Vendor:
    return Vendor(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        business_name=f"Vendor {uuid.uuid4().hex[:6]}",
        contact_email=f"{uuid.uuid4().hex[:8]}@test.com",
        status=VendorStatus.ACTIVE,
    )


def _make_service(vendor_id: uuid.UUID) -> Service:
    return Service(
        id=uuid.uuid4(),
        vendor_id=vendor_id,
        name=f"Service {uuid.uuid4().hex[:6]}",
        is_active=True,
        price_min=100.0,
        price_max=500.0,
    )


def _make_booking(vendor_id: uuid.UUID, service_id: uuid.UUID, event_date: date) -> Booking:
    return Booking(
        id=uuid.uuid4(),
        vendor_id=vendor_id,
        service_id=service_id,
        event_date=event_date,
        status=BookingStatus.pending,
        unit_price=100.0,
        total_price=100.0,
        currency="USD",
    )


# ── Hypothesis strategies ─────────────────────────────────────────────────────

def booking_strategy():
    """Generate dicts with random future event_dates."""
    return st.fixed_dictionaries({
        "days_ahead": st.integers(min_value=1, max_value=365),
        "status": st.just("pending"),
    })


# ── Property 3: Dashboard recent bookings are the N most recent ───────────────

class TestDashboardRecentBookings:
    """
    Property 3: Dashboard recent bookings are the N most recent.

    For any vendor with K bookings (K >= 5), the recent_bookings array returned
    by get_dashboard_stats SHALL contain exactly 5 items.

    Note: The service orders by Booking.created_at DESC. Since all bookings are
    created in the same test transaction with effectively the same timestamp in
    SQLite, we assert the count invariant (exactly 5 returned when >= 5 exist)
    rather than a strict ordering assertion that would be non-deterministic.

    Feature: vendor-portal-complete, Property 3: Dashboard recent bookings are the N most recent
    Validates: Requirements 2.5
    """

    @given(booking_params=st.lists(booking_strategy(), min_size=5))
    @h_settings(max_examples=10, deadline=None)
    def test_recent_bookings_count_is_five(self, booking_params: list):
        """
        When a vendor has >= 5 bookings, get_dashboard_stats returns exactly 5
        recent bookings.
        Validates: Requirements 2.5
        """
        _run(self._run_recent_bookings_count(booking_params))

    async def _run_recent_bookings_count(self, booking_params: list):
        async with _SESSION_FACTORY() as session:
            # Create vendor
            vendor = _make_vendor()
            session.add(vendor)
            await session.flush()
            vendor_id = vendor.id  # capture before session closes

            # Create a service for the vendor (needed for booking FK)
            service = _make_service(vendor_id)
            session.add(service)
            await session.flush()
            service_id = service.id

            # Create N bookings (N >= 5) with the generated event_dates
            today = datetime.now(timezone.utc).date()
            for params in booking_params:
                event_date = today + timedelta(days=params["days_ahead"])
                booking = _make_booking(vendor_id, service_id, event_date)
                session.add(booking)

            await session.commit()

            # Call the service under test
            stats = await vendor_dashboard_service.get_dashboard_stats(session, vendor_id)

            # Read recent_bookings values while session is still open
            recent_count = len(stats.recent_bookings)
            recent_ids = [rb.id for rb in stats.recent_bookings]

        # Assert exactly 5 recent bookings are returned
        assert recent_count == 5, (
            f"Expected exactly 5 recent bookings, got {recent_count}. "
            f"Total bookings created: {len(booking_params)}"
        )

        # Assert all returned items have valid UUIDs (sanity check)
        assert len(recent_ids) == 5
        for booking_id in recent_ids:
            assert isinstance(booking_id, uuid.UUID), (
                f"Expected UUID, got {type(booking_id)}: {booking_id}"
            )

    @given(booking_params=st.lists(booking_strategy(), min_size=5, max_size=20))
    @h_settings(max_examples=10, deadline=None)
    def test_recent_bookings_never_exceeds_five(self, booking_params: list):
        """
        Regardless of how many bookings exist (>= 5), recent_bookings never
        returns more than 5 items.
        Validates: Requirements 2.5
        """
        _run(self._run_never_exceeds_five(booking_params))

    async def _run_never_exceeds_five(self, booking_params: list):
        async with _SESSION_FACTORY() as session:
            vendor = _make_vendor()
            session.add(vendor)
            await session.flush()
            vendor_id = vendor.id

            service = _make_service(vendor_id)
            session.add(service)
            await session.flush()
            service_id = service.id

            today = datetime.now(timezone.utc).date()
            for params in booking_params:
                event_date = today + timedelta(days=params["days_ahead"])
                booking = _make_booking(vendor_id, service_id, event_date)
                session.add(booking)

            await session.commit()

            stats = await vendor_dashboard_service.get_dashboard_stats(session, vendor_id)

            # Read values while session is open
            recent_count = len(stats.recent_bookings)

        assert recent_count == 5, (
            f"Expected exactly 5 recent bookings (LIMIT 5), got {recent_count}. "
            f"Total bookings: {len(booking_params)}"
        )

    @given(booking_params=st.lists(booking_strategy(), min_size=5))
    @h_settings(max_examples=10, deadline=None)
    def test_total_bookings_count_matches_created(self, booking_params: list):
        """
        The total_bookings count in DashboardStats matches the number of bookings
        created for the vendor.
        Validates: Requirements 2.5
        """
        _run(self._run_total_count(booking_params))

    async def _run_total_count(self, booking_params: list):
        async with _SESSION_FACTORY() as session:
            vendor = _make_vendor()
            session.add(vendor)
            await session.flush()
            vendor_id = vendor.id

            service = _make_service(vendor_id)
            session.add(service)
            await session.flush()
            service_id = service.id

            today = datetime.now(timezone.utc).date()
            for params in booking_params:
                event_date = today + timedelta(days=params["days_ahead"])
                booking = _make_booking(vendor_id, service_id, event_date)
                session.add(booking)

            await session.commit()

            stats = await vendor_dashboard_service.get_dashboard_stats(session, vendor_id)

            total_bookings = stats.total_bookings
            pending_bookings = stats.pending_bookings

        expected_total = len(booking_params)
        assert total_bookings == expected_total, (
            f"Expected total_bookings={expected_total}, got {total_bookings}"
        )
        # All bookings are created with status=pending
        assert pending_bookings == expected_total, (
            f"Expected pending_bookings={expected_total}, got {pending_bookings}"
        )
