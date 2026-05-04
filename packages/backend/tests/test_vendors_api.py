"""
Property-based HTTP integration tests for vendor API endpoints.

Uses a dedicated asyncio event loop + aiosqlite in-memory DB, with the
FastAPI app's get_session and get_current_user dependencies overridden.
Hypothesis @given tests are plain synchronous functions that call _run()
on a module-level loop — no asyncio.run(), no nest_asyncio, no
pytest-asyncio interference.

Run with: uv run pytest tests/test_vendors_api.py -v
Feature: vendor-portal-complete
"""
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
from hypothesis import given
from hypothesis import settings as h_settings
from hypothesis import strategies as st
from httpx import AsyncClient, ASGITransport
from sqlalchemy import String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from src.main import app
from src.api.deps import get_current_user
from src.config.database import get_session
from src.models.booking import Booking, BookingStatus
from src.models.service import Service
from src.models.user import User
from src.models.vendor import Vendor, VendorStatus

# Prevent pytest-asyncio (asyncio_mode=auto) from wrapping these sync
# Hypothesis tests in a coroutine. The tests manage their own event loop.
pytestmark = pytest.mark.asyncio(mode="strict")

# ── Tables needed (FK order) ──────────────────────────────────────────────────

API_TABLES = [
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
                for name in API_TABLES
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

def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:8]}@test.com",
        password_hash="x",
        first_name="T",
        last_name="U",
        role="vendor",
        is_active=True,
        email_verified=True,
    )


def _make_vendor(user_id: uuid.UUID) -> Vendor:
    return Vendor(
        id=uuid.uuid4(),
        user_id=user_id,
        business_name=f"Vendor {uuid.uuid4().hex[:6]}",
        contact_email=f"{uuid.uuid4().hex[:8]}@vendor.com",
        status=VendorStatus.ACTIVE,
    )


def _make_service(vendor_id: uuid.UUID, index: int = 0) -> Service:
    return Service(
        id=uuid.uuid4(),
        vendor_id=vendor_id,
        name=f"Service {index} {uuid.uuid4().hex[:6]}",
        is_active=True,
        price_min=100.0,
        price_max=500.0,
    )


def _make_booking(
    vendor_id: uuid.UUID,
    service_id: uuid.UUID,
    event_date: date,
    status: BookingStatus = BookingStatus.pending,
) -> Booking:
    return Booking(
        id=uuid.uuid4(),
        vendor_id=vendor_id,
        service_id=service_id,
        event_date=event_date,
        status=status,
        unit_price=100.0,
        total_price=100.0,
        currency="USD",
    )


# ── Property 5: Service pagination invariants ─────────────────────────────────

class TestServicePaginationInvariants:
    """
    Property 5: Service pagination invariants.

    For a vendor with exactly N=7 active services, any (page, limit) combination
    must satisfy:
      - meta.total == N
      - len(data) <= limit
      - len(data) == min(limit, max(0, N - (page-1)*limit))

    Feature: vendor-portal-complete, Property 5: Service pagination invariants
    Validates: Requirements 3.1
    """

    @given(
        page=st.integers(min_value=1, max_value=5),
        limit=st.integers(min_value=1, max_value=10),
    )
    @h_settings(max_examples=10, deadline=None)
    def test_pagination_invariants(self, page: int, limit: int):
        """
        meta.total always equals N; len(data) matches the expected slice size.
        Validates: Requirements 3.1
        """
        _run(self._run_pagination(page, limit))

    async def _run_pagination(self, page: int, limit: int):
        N = 7  # fixed seed count for determinism

        async with _SESSION_FACTORY() as session:
            user = _make_user()
            vendor = _make_vendor(user.id)
            session.add(user)
            session.add(vendor)
            await session.flush()

            vendor_id = vendor.id

            for i in range(N):
                session.add(_make_service(vendor_id, index=i))

            await session.commit()

            async def override_session() -> AsyncGenerator[AsyncSession, None]:
                yield session

            async def override_user() -> User:
                return user

            app.dependency_overrides[get_session] = override_session
            app.dependency_overrides[get_current_user] = override_user

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    resp = await ac.get(
                        "/api/v1/vendors/me/services",
                        params={"page": page, "limit": limit},
                    )
                body = resp.json()
            finally:
                app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {body}"
        assert body["success"] is True

        meta = body["meta"]
        data = body["data"]

        expected_count = min(limit, max(0, N - (page - 1) * limit))

        assert meta["total"] == N, (
            f"meta.total={meta['total']} != N={N} for page={page}, limit={limit}"
        )
        assert len(data) <= limit, (
            f"len(data)={len(data)} > limit={limit} for page={page}, limit={limit}"
        )
        assert len(data) == expected_count, (
            f"len(data)={len(data)} != expected={expected_count} "
            f"for page={page}, limit={limit}, N={N}"
        )


# ── Property 7: Booking list is sorted by event_date descending ───────────────

class TestBookingListSortOrder:
    """
    Property 7: Booking list is sorted by event_date descending.

    For any set of bookings with distinct event_dates, the GET
    /api/v1/vendors/me/bookings response must return them ordered
    event_date DESC — i.e. for any adjacent pair (i, i+1):
    data[i].event_date >= data[i+1].event_date.

    Feature: vendor-portal-complete, Property 7: Booking list is sorted by event_date descending
    Validates: Requirements 4.1
    """

    @given(
        days_ahead_list=st.lists(
            st.integers(min_value=1, max_value=365),
            min_size=2,
            max_size=8,
        )
    )
    @h_settings(max_examples=10, deadline=None)
    def test_bookings_sorted_by_event_date_desc(self, days_ahead_list: list):
        """
        Bookings returned by GET /api/v1/vendors/me/bookings are sorted
        event_date descending for any set of event_dates.
        Validates: Requirements 4.1
        """
        _run(self._run_sort_order(days_ahead_list))

    async def _run_sort_order(self, days_ahead_list: list):
        today = datetime.now(timezone.utc).date()

        async with _SESSION_FACTORY() as session:
            user = _make_user()
            vendor = _make_vendor(user.id)
            session.add(user)
            session.add(vendor)
            await session.flush()

            vendor_id = vendor.id

            service = _make_service(vendor_id)
            session.add(service)
            await session.flush()
            service_id = service.id

            for days in days_ahead_list:
                event_date = today + timedelta(days=days)
                session.add(_make_booking(vendor_id, service_id, event_date))

            await session.commit()

            async def override_session() -> AsyncGenerator[AsyncSession, None]:
                yield session

            async def override_user() -> User:
                return user

            app.dependency_overrides[get_session] = override_session
            app.dependency_overrides[get_current_user] = override_user

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    resp = await ac.get("/api/v1/vendors/me/bookings")
                body = resp.json()
            finally:
                app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {body}"
        assert body["success"] is True

        data = body["data"]
        assert len(data) == len(days_ahead_list), (
            f"Expected {len(days_ahead_list)} bookings, got {len(data)}"
        )

        # Assert adjacent pairs are sorted descending
        dates = [item["event_date"] for item in data]
        for i in range(len(dates) - 1):
            assert dates[i] >= dates[i + 1], (
                f"Sort order violated at index {i}: "
                f"dates[{i}]={dates[i]} < dates[{i+1}]={dates[i+1]}"
            )


# ── Property 8: Status filter returns only matching bookings ──────────────────

class TestBookingStatusFilter:
    """
    Property 8: Status filter returns only matching bookings.

    When GET /api/v1/vendors/me/bookings?status=S is called, every item
    in the response data must have status == S, regardless of what other
    statuses exist in the database for that vendor.

    Feature: vendor-portal-complete, Property 8: Status filter returns only matching bookings
    Validates: Requirements 4.2
    """

    @given(
        filter_status=st.sampled_from(["pending", "confirmed", "cancelled"])
    )
    @h_settings(max_examples=10, deadline=None)
    def test_status_filter_returns_only_matching(self, filter_status: str):
        """
        Every booking returned when filtering by status S has status == S.
        Validates: Requirements 4.2
        """
        _run(self._run_status_filter(filter_status))

    async def _run_status_filter(self, filter_status: str):
        today = datetime.now(timezone.utc).date()

        # Seed one booking for each of the three statuses so the filter
        # always has something to exclude.
        all_statuses = [
            BookingStatus.pending,
            BookingStatus.confirmed,
            BookingStatus.cancelled,
        ]

        async with _SESSION_FACTORY() as session:
            user = _make_user()
            vendor = _make_vendor(user.id)
            session.add(user)
            session.add(vendor)
            await session.flush()

            vendor_id = vendor.id

            service = _make_service(vendor_id)
            session.add(service)
            await session.flush()
            service_id = service.id

            for i, bstatus in enumerate(all_statuses):
                event_date = today + timedelta(days=i + 1)
                session.add(_make_booking(vendor_id, service_id, event_date, status=bstatus))

            await session.commit()

            async def override_session() -> AsyncGenerator[AsyncSession, None]:
                yield session

            async def override_user() -> User:
                return user

            app.dependency_overrides[get_session] = override_session
            app.dependency_overrides[get_current_user] = override_user

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    resp = await ac.get(
                        "/api/v1/vendors/me/bookings",
                        params={"status": filter_status},
                    )
                body = resp.json()
            finally:
                app.dependency_overrides.clear()

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {body}"
        assert body["success"] is True

        data = body["data"]

        # Every returned booking must match the requested status
        for item in data:
            assert item["status"] == filter_status, (
                f"Expected status={filter_status!r}, got {item['status']!r} "
                f"for booking id={item.get('id')}"
            )

        # Sanity: exactly one booking with this status was seeded
        assert len(data) == 1, (
            f"Expected exactly 1 booking with status={filter_status!r}, got {len(data)}"
        )
