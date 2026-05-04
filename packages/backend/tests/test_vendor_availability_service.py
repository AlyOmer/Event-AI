"""
Property-based tests for VendorAvailabilityService.

Uses a dedicated asyncio event loop + aiosqlite in-memory DB.
Hypothesis @given tests are plain synchronous functions that call
_run() on a module-level loop — no asyncio.run(), no nest_asyncio,
no pytest-asyncio interference.

The service no longer uses pg_insert (fixed to SELECT+INSERT/UPDATE),
so no dialect patching is needed.

Run with: uv run pytest tests/test_vendor_availability_service.py -v
Feature: vendor-portal-complete
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import settings as h_settings
from hypothesis import strategies as st
from sqlalchemy import String, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from src.models.availability import VendorAvailability
from src.models.vendor import Vendor, VendorStatus
from src.schemas.vendor_availability import AvailabilityUpsert
from src.services.vendor_availability_service import VendorAvailabilityService

# Prevent pytest-asyncio (asyncio_mode=auto) from wrapping these sync
# Hypothesis tests in a coroutine. The tests manage their own event loop.
pytestmark = pytest.mark.asyncio(mode="strict")

# ── Tables needed (FK order) ──────────────────────────────────────────────────

AVAIL_TABLES = [
    "users",
    "vendors",
    "categories",
    "vendor_categories",
    "services",
    "bookings",
    "vendor_availability",
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
# A dedicated loop avoids any conflict with pytest-asyncio's per-test loop.
# _LOOP.run_until_complete() is safe here because this loop is never running
# when the sync Hypothesis test body calls _run().

_LOOP: asyncio.AbstractEventLoop = asyncio.new_event_loop()


def _build_engine():
    Vendor.__table__.c["status"].type = String(50)

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
                for name in AVAIL_TABLES
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


def _future_date(days_ahead: int = 30):
    return (datetime.now(timezone.utc) + timedelta(days=days_ahead)).date()


# ── Hypothesis strategies ─────────────────────────────────────────────────────

def availability_entry_strategy():
    return st.fixed_dictionaries({
        "days_ahead": st.integers(min_value=1, max_value=365),
        "status": st.sampled_from(["available", "blocked", "tentative"]),
    })


# ── Property 10: Availability upsert is idempotent ───────────────────────────

class TestUpsertIdempotency:
    """
    Property 10: Availability upsert is idempotent.

    Calling upsert_availability twice with the same payload SHALL result in
    exactly one DB record with the latest status; the second call SHALL NOT
    raise a conflict error.

    Feature: vendor-portal-complete, Property 10: Availability upsert is idempotent
    Validates: Requirements 5.2
    """

    @given(entry_params=availability_entry_strategy())
    @h_settings(max_examples=10, deadline=None)
    def test_upsert_idempotency(self, entry_params: dict):
        """
        Two identical upserts → exactly one DB row, correct status, no exception.
        Validates: Requirements 5.2
        """
        _run(self._run_idempotency(entry_params))

    async def _run_idempotency(self, entry_params: dict):
        async with _SESSION_FACTORY() as session:
            vendor = _make_vendor()
            session.add(vendor)
            await session.commit()
            await session.refresh(vendor)
            vendor_id = vendor.id  # capture UUID before session closes

            target_date = _future_date(entry_params["days_ahead"])
            entry = AvailabilityUpsert(
                date=target_date,
                status=entry_params["status"],
                service_id=None,
                notes=None,
            )
            svc = VendorAvailabilityService()

            result1 = await svc.upsert_availability(session, vendor_id, entry)
            result2 = await svc.upsert_availability(session, vendor_id, entry)

            # Read all values while session is still open
            r1_vendor_id = result1.vendor_id
            r2_status = result2.status

            stmt = sa_select(VendorAvailability).where(
                VendorAvailability.vendor_id == vendor_id,
                VendorAvailability.date == target_date,
                VendorAvailability.service_id.is_(None),
            )
            rows = (await session.execute(stmt)).scalars().all()
            row_count = len(rows)
            row_status = rows[0].status if rows else None
            await session.rollback()

        assert row_count == 1, (
            f"Expected 1 row after two upserts, got {row_count}. "
            f"date={target_date}, status={entry_params['status']}"
        )
        assert row_status == entry_params["status"]
        assert result1 is not None and result2 is not None
        assert r1_vendor_id == vendor_id
        assert r2_status == entry_params["status"]

    @given(
        status1=st.sampled_from(["available", "blocked", "tentative"]),
        status2=st.sampled_from(["available", "blocked", "tentative"]),
    )
    @h_settings(max_examples=10, deadline=None)
    def test_upsert_updates_status_on_second_call(self, status1: str, status2: str):
        """
        Second upsert with a different status → DB row reflects the new status.
        Validates: Requirements 5.2
        """
        _run(self._run_status_update(status1, status2))

    async def _run_status_update(self, status1: str, status2: str):
        async with _SESSION_FACTORY() as session:
            vendor = _make_vendor()
            session.add(vendor)
            await session.commit()
            await session.refresh(vendor)
            vendor_id = vendor.id  # capture UUID before session closes

            target_date = _future_date(60)
            e1 = AvailabilityUpsert(date=target_date, status=status1, service_id=None)
            e2 = AvailabilityUpsert(date=target_date, status=status2, service_id=None)
            svc = VendorAvailabilityService()

            await svc.upsert_availability(session, vendor_id, e1)
            result2 = await svc.upsert_availability(session, vendor_id, e2)

            result2_status = result2.status  # read while session open

            stmt = sa_select(VendorAvailability).where(
                VendorAvailability.vendor_id == vendor_id,
                VendorAvailability.date == target_date,
            )
            rows = (await session.execute(stmt)).scalars().all()
            # Read scalar values while session is still open
            row_count = len(rows)
            row_status = rows[0].status if rows else None
            result2_status = result2.status
            await session.rollback()

        assert row_count == 1, f"Expected 1 row, got {row_count}"
        assert row_status == status2, f"Expected {status2!r}, got {row_status!r}"
        assert result2_status == status2


# ── Property 9: Availability date-range filter is inclusive ──────────────────

def date_range_strategy():
    """
    Generate (start_days_ahead, end_days_ahead) pairs where start <= end,
    both representing future dates relative to today.
    """
    return st.integers(min_value=1, max_value=180).flatmap(
        lambda start: st.integers(min_value=start, max_value=180).map(
            lambda end: (start, end)
        )
    )


class TestDateRangeFilterInclusivity:
    """
    Property 9: Availability date-range filter is inclusive.

    list_availability(session, vendor_id, start_date, end_date) SHALL return
    only records where start_date <= record.date <= end_date (inclusive on
    both ends). Records outside the range SHALL NOT appear in the result.

    Feature: vendor-portal-complete, Property 9: Availability date-range filter is inclusive
    Validates: Requirements 5.1
    """

    @given(date_range=date_range_strategy())
    @h_settings(max_examples=10, deadline=None)
    def test_date_range_filter_is_inclusive(self, date_range: tuple):
        """
        Seed records inside and outside the range; assert every returned record
        satisfies start_date <= r.date <= end_date.
        Validates: Requirements 5.1
        """
        _run(self._run_date_range_filter(date_range))

    async def _run_date_range_filter(self, date_range: tuple):
        start_days, end_days = date_range
        start_date = _future_date(start_days)
        end_date = _future_date(end_days)

        async with _SESSION_FACTORY() as session:
            vendor = _make_vendor()
            session.add(vendor)
            await session.commit()
            await session.refresh(vendor)
            vendor_id = vendor.id

            svc = VendorAvailabilityService()

            # ── Seed records INSIDE the range ────────────────────────────────
            # Always include the boundary dates (start_date and end_date) to
            # verify inclusive semantics, plus a mid-range date when the range
            # spans at least 2 days.
            inside_dates = {start_date, end_date}
            if end_days > start_days:
                mid_days = start_days + (end_days - start_days) // 2
                inside_dates.add(_future_date(mid_days))

            for d in inside_dates:
                entry = AvailabilityUpsert(
                    date=d,
                    status="available",
                    service_id=None,
                    notes=None,
                )
                await svc.upsert_availability(session, vendor_id, entry)

            # ── Seed records OUTSIDE the range ───────────────────────────────
            # One day before start (if start_days > 1) and one day after end
            # (if end_days < 180).
            outside_dates = set()
            if start_days > 1:
                outside_dates.add(_future_date(start_days - 1))
            if end_days < 180:
                outside_dates.add(_future_date(end_days + 1))

            for d in outside_dates:
                entry = AvailabilityUpsert(
                    date=d,
                    status="blocked",
                    service_id=None,
                    notes=None,
                )
                await svc.upsert_availability(session, vendor_id, entry)

            # ── Call the service under test ───────────────────────────────────
            results = await svc.list_availability(
                session, vendor_id, start_date, end_date
            )

            # Read all attribute values while the session is still open to
            # avoid DetachedInstanceError after the context manager exits.
            result_dates = [r.date for r in results]
            result_count = len(results)

            await session.rollback()

        # ── Assertions ────────────────────────────────────────────────────────
        # Every returned record must be within [start_date, end_date].
        for d in result_dates:
            assert start_date <= d <= end_date, (
                f"Returned date {d} is outside the requested range "
                f"[{start_date}, {end_date}]"
            )

        # The boundary dates we seeded must appear in the results.
        assert start_date in result_dates, (
            f"start_date {start_date} was seeded inside the range but not returned. "
            f"Returned dates: {result_dates}"
        )
        assert end_date in result_dates, (
            f"end_date {end_date} was seeded inside the range but not returned. "
            f"Returned dates: {result_dates}"
        )

        # Records outside the range must NOT appear.
        for d in outside_dates:
            assert d not in result_dates, (
                f"Date {d} is outside [{start_date}, {end_date}] but was returned. "
                f"Returned dates: {result_dates}"
            )

        # Sanity: at least the boundary records were returned.
        assert result_count >= len(inside_dates), (
            f"Expected at least {len(inside_dates)} records (inside dates), "
            f"got {result_count}"
        )
