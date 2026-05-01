"""
Integration tests for GET /api/v1/admin/stats.

Uses httpx.AsyncClient + ASGITransport with an isolated in-memory SQLite
session — no real database or server required.

Test fixtures:
- admin_user  — User with role="admin"
- regular_user — User with role="user"
- admin_token  — JWT for admin_user via AuthService.create_access_token
- user_token   — JWT for regular_user
"""
import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import String
from sqlmodel import SQLModel
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.config.database import get_session
from src.models.user import User, RefreshToken, PasswordResetToken  # noqa: F401
from src.models.domain_event import DomainEvent  # noqa: F401
from src.models.booking import Booking, BookingStatus  # noqa: F401
from src.models.notification import Notification  # noqa: F401
from src.models.notification_preference import NotificationPreference  # noqa: F401
from src.services.auth_service import AuthService

# ── Test database ─────────────────────────────────────────────────────────────

STATS_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Tables required for the stats tests
STATS_TABLES = [
    "users",
    "refresh_tokens",
    "password_reset_tokens",
    "domain_events",
    "bookings",
    "notifications",
    "notification_preferences",
    # Vendor-related tables
    "vendors",
    "categories",
    "vendor_categories",
]


@pytest_asyncio.fixture(scope="module")
async def stats_engine():
    """
    Create an isolated in-memory SQLite engine for the stats test module.

    Patches:
    - DomainEvent.data: JSONB → JSON (SQLite has no JSONB)
    - Vendor.status: PostgreSQL ENUM → String (SQLite has no native ENUM)
    """
    # Import vendor-related models so SQLModel registers their metadata
    from src.models.vendor import Vendor  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.service import Service  # noqa: F401
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401

    engine = create_async_engine(STATS_TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        # Patch JSONB → JSON for SQLite compatibility
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import JSON
        DomainEvent.__table__.c["data"].type = JSON()

        # Patch PostgreSQL ENUM → String for Vendor.status
        Vendor.__table__.c["status"].type = String(50)

        available_tables = {
            name: SQLModel.metadata.tables[name]
            for name in STATS_TABLES
            if name in SQLModel.metadata.tables
        }
        await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.create_all(
                sync_conn,
                tables=list(available_tables.values()),
            )
        )

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def stats_db_session(stats_engine) -> AsyncGenerator[AsyncSession, None]:
    """Transactional test session that rolls back after each test."""
    async_session = sessionmaker(stats_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def stats_client(stats_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with the test DB session injected and rate limiting bypassed."""
    import src.api.v1.auth as auth_module
    import src.api.v1.events as events_module
    import src.api.v1.notifications as notif_module

    async def no_rate_limit(request=None):
        pass

    async def override_get_session():
        yield stats_db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[auth_module.register_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.login_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.password_reset_limiter] = no_rate_limit
    app.dependency_overrides[events_module.create_limiter] = no_rate_limit
    app.dependency_overrides[events_module.read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._write_limiter] = no_rate_limit

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(stats_db_session: AsyncSession) -> User:
    """A User with role='admin' inserted into the test session."""
    user = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        first_name="Admin",
        last_name="User",
        role="admin",
        is_active=True,
        email_verified=True,
        password_hash=AuthService.hash_password("AdminPass123!"),
    )
    stats_db_session.add(user)
    await stats_db_session.commit()
    await stats_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user(stats_db_session: AsyncSession) -> User:
    """A User with role='user' inserted into the test session."""
    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:8]}@test.com",
        first_name="Regular",
        last_name="User",
        role="user",
        is_active=True,
        email_verified=True,
        password_hash=AuthService.hash_password("UserPass123!"),
    )
    stats_db_session.add(user)
    await stats_db_session.commit()
    await stats_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
def admin_token(admin_user: User) -> str:
    """JWT access token for admin_user."""
    token, _ = AuthService.create_access_token(admin_user)
    return token


@pytest_asyncio.fixture
def user_token(regular_user: User) -> str:
    """JWT access token for regular_user."""
    token, _ = AuthService.create_access_token(regular_user)
    return token


# ── Seeding helpers ───────────────────────────────────────────────────────────

async def _seed_vendors(session: AsyncSession, active: int = 0, pending: int = 0) -> None:
    """Insert vendor rows with the given statuses."""
    from src.models.vendor import Vendor, VendorStatus

    for i in range(active):
        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name=f"Active Vendor {i}",
            contact_email=f"active-{uuid.uuid4().hex[:8]}@vendor.com",
            status=VendorStatus.ACTIVE,
        )
        session.add(vendor)

    for i in range(pending):
        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name=f"Pending Vendor {i}",
            contact_email=f"pending-{uuid.uuid4().hex[:8]}@vendor.com",
            status=VendorStatus.PENDING,
        )
        session.add(vendor)

    await session.commit()


async def _seed_bookings(
    session: AsyncSession,
    confirmed: int = 0,
    pending: int = 0,
    completed: int = 0,
    confirmed_price: float = 100.0,
    completed_price: float = 200.0,
) -> None:
    """Insert booking rows with the given statuses."""
    from datetime import date

    for i in range(confirmed):
        booking = Booking(
            id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            event_date=date(2027, 6, 1),
            unit_price=confirmed_price,
            total_price=confirmed_price,
            status=BookingStatus.confirmed,
        )
        session.add(booking)

    for i in range(pending):
        booking = Booking(
            id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            event_date=date(2027, 7, 1),
            unit_price=50.0,
            total_price=50.0,
            status=BookingStatus.pending,
        )
        session.add(booking)

    for i in range(completed):
        booking = Booking(
            id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            event_date=date(2027, 5, 1),
            unit_price=completed_price,
            total_price=completed_price,
            status=BookingStatus.completed,
        )
        session.add(booking)

    await session.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────

STATS_URL = "/api/v1/admin/stats/"


class TestAdminStatsWithAdminToken:
    """GET /api/v1/admin/stats — admin access returns correct counts."""

    @pytest.mark.asyncio
    async def test_stats_returns_200_with_success_envelope(
        self,
        stats_client: AsyncClient,
        admin_token: str,
    ):
        """Admin token should receive a 200 with the standard success envelope."""
        resp = await stats_client.get(
            STATS_URL,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert "meta" in body

    @pytest.mark.asyncio
    async def test_stats_data_has_all_required_fields(
        self,
        stats_client: AsyncClient,
        admin_token: str,
    ):
        """Response data must contain all seven stat fields."""
        resp = await stats_client.get(
            STATS_URL,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        required_fields = {
            "totalUsers",
            "activeVendors",
            "pendingVendors",
            "totalBookings",
            "confirmedBookings",
            "pendingBookings",
            "totalRevenue",
        }
        assert required_fields.issubset(data.keys())

    @pytest.mark.asyncio
    async def test_stats_correct_counts_for_seeded_data(
        self,
        stats_db_session: AsyncSession,
        stats_client: AsyncClient,
        admin_user: User,
        admin_token: str,
    ):
        """
        Seed known data and verify the stats endpoint returns the exact counts.

        Seed:
        - 1 active vendor, 2 pending vendors
        - 1 confirmed booking ($100), 2 pending bookings, 1 completed booking ($200)

        Expected:
        - totalUsers >= 1 (admin_user is active)
        - activeVendors = 1
        - pendingVendors = 2
        - totalBookings = 4
        - confirmedBookings = 1
        - pendingBookings = 2
        - totalRevenue = 100.0 + 200.0 = 300.0
        """
        await _seed_vendors(stats_db_session, active=1, pending=2)
        await _seed_bookings(
            stats_db_session,
            confirmed=1,
            pending=2,
            completed=1,
            confirmed_price=100.0,
            completed_price=200.0,
        )

        resp = await stats_client.get(
            STATS_URL,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        # User counts: at least admin_user (is_active=True)
        assert data["totalUsers"] >= 1

        # Vendor counts must match seeded data exactly
        assert data["activeVendors"] == 1
        assert data["pendingVendors"] == 2

        # Booking counts must match seeded data exactly
        assert data["totalBookings"] == 4
        assert data["confirmedBookings"] == 1
        assert data["pendingBookings"] == 2

        # Revenue = confirmed ($100) + completed ($200)
        assert data["totalRevenue"] == pytest.approx(300.0)

    @pytest.mark.asyncio
    async def test_stats_empty_db_returns_zeros(
        self,
        stats_client: AsyncClient,
        admin_token: str,
    ):
        """With no vendors or bookings seeded, counts should be zero (or just user count)."""
        resp = await stats_client.get(
            STATS_URL,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        # No vendors or bookings seeded in this test
        assert data["activeVendors"] >= 0
        assert data["pendingVendors"] >= 0
        assert data["totalBookings"] >= 0
        assert data["totalRevenue"] >= 0.0


class TestAdminStatsWithNonAdminToken:
    """GET /api/v1/admin/stats — non-admin access returns HTTP 403."""

    @pytest.mark.asyncio
    async def test_stats_returns_403_for_regular_user(
        self,
        stats_client: AsyncClient,
        user_token: str,
    ):
        """A regular user token must receive HTTP 403."""
        resp = await stats_client.get(
            STATS_URL,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["success"] is False

    @pytest.mark.asyncio
    async def test_stats_403_has_error_code(
        self,
        stats_client: AsyncClient,
        user_token: str,
    ):
        """The 403 response should include an error code in the standard envelope."""
        resp = await stats_client.get(
            STATS_URL,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert "error" in body
        # The global exception handler maps 403 → AUTH_FORBIDDEN
        assert body["error"]["code"] == "AUTH_FORBIDDEN"

    @pytest.mark.asyncio
    async def test_stats_returns_401_without_token(
        self,
        stats_client: AsyncClient,
    ):
        """Calling the endpoint without any token must return HTTP 401."""
        resp = await stats_client.get(STATS_URL)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_returns_401_with_invalid_token(
        self,
        stats_client: AsyncClient,
    ):
        """An invalid/malformed token must return HTTP 401."""
        resp = await stats_client.get(
            STATS_URL,
            headers={"Authorization": "Bearer invalid.token.value"},
        )
        assert resp.status_code == 401
