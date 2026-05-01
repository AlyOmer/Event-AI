"""
Integration tests for admin vendors endpoints:
  GET  /api/v1/admin/vendors/
  PATCH /api/v1/admin/vendors/{vendor_id}/status

Uses httpx.AsyncClient + ASGITransport with an isolated in-memory SQLite
session — no real database or server required.

Test fixtures:
- admin_user     — User with role="admin"
- regular_user   — User with role="user"
- admin_token    — JWT for admin_user
- user_token     — JWT for regular_user
- pending_vendor — Vendor with status=PENDING
- active_vendor  — Vendor with status=ACTIVE
"""
import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import String
from sqlmodel import SQLModel
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.config.database import get_session
from src.api.deps import get_event_bus
from src.models.user import User, RefreshToken, PasswordResetToken  # noqa: F401
from src.models.domain_event import DomainEvent  # noqa: F401
from src.models.booking import Booking  # noqa: F401
from src.models.notification import Notification  # noqa: F401
from src.models.notification_preference import NotificationPreference  # noqa: F401
from src.models.vendor import Vendor, VendorStatus
from src.services.auth_service import AuthService

# ── Test database ─────────────────────────────────────────────────────────────

VENDORS_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

VENDORS_TABLES = [
    "users",
    "refresh_tokens",
    "password_reset_tokens",
    "domain_events",
    "bookings",
    "notifications",
    "notification_preferences",
    "vendors",
    "categories",
    "vendor_categories",
]


@pytest_asyncio.fixture(scope="module")
async def vendors_engine():
    """Isolated in-memory SQLite engine for the vendors test module."""
    from src.models.vendor import Vendor  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.service import Service  # noqa: F401
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401

    engine = create_async_engine(VENDORS_TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import JSON
        DomainEvent.__table__.c["data"].type = JSON()
        Vendor.__table__.c["status"].type = String(50)

        available_tables = {
            name: SQLModel.metadata.tables[name]
            for name in VENDORS_TABLES
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
async def vendors_db_session(vendors_engine) -> AsyncGenerator[AsyncSession, None]:
    """Transactional test session that rolls back after each test."""
    async_session = sessionmaker(vendors_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def vendors_client(vendors_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with test DB session injected, rate limiting and event bus bypassed."""
    import src.api.v1.auth as auth_module
    import src.api.v1.events as events_module
    import src.api.v1.notifications as notif_module

    async def no_rate_limit(request=None):
        pass

    async def override_get_session():
        yield vendors_db_session

    # Mock event bus so PATCH tests don't need a real event bus
    mock_event_bus = AsyncMock()
    mock_event_bus.emit = AsyncMock(return_value=None)

    def override_get_event_bus():
        return mock_event_bus

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_event_bus] = override_get_event_bus
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
async def admin_user(vendors_db_session: AsyncSession) -> User:
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
    vendors_db_session.add(user)
    await vendors_db_session.commit()
    await vendors_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user(vendors_db_session: AsyncSession) -> User:
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
    vendors_db_session.add(user)
    await vendors_db_session.commit()
    await vendors_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
def admin_token(admin_user: User) -> str:
    token, _ = AuthService.create_access_token(admin_user)
    return token


@pytest_asyncio.fixture
def user_token(regular_user: User) -> str:
    token, _ = AuthService.create_access_token(regular_user)
    return token


# ── Vendor fixtures ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def pending_vendor(vendors_db_session: AsyncSession) -> Vendor:
    """A Vendor with status=PENDING."""
    vendor = Vendor(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        business_name="Test Pending Vendor",
        contact_email=f"pending-{uuid.uuid4().hex[:8]}@vendor.com",
        status=VendorStatus.PENDING,
        city="Karachi",
        region="Sindh",
    )
    vendors_db_session.add(vendor)
    await vendors_db_session.commit()
    await vendors_db_session.refresh(vendor)
    return vendor


@pytest_asyncio.fixture
async def active_vendor(vendors_db_session: AsyncSession) -> Vendor:
    """A Vendor with status=ACTIVE."""
    vendor = Vendor(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        business_name="Test Active Vendor",
        contact_email=f"active-{uuid.uuid4().hex[:8]}@vendor.com",
        status=VendorStatus.ACTIVE,
        city="Lahore",
        region="Punjab",
    )
    vendors_db_session.add(vendor)
    await vendors_db_session.commit()
    await vendors_db_session.refresh(vendor)
    return vendor


# ── Tests: GET /api/v1/admin/vendors/ ─────────────────────────────────────────

VENDORS_LIST_URL = "/api/v1/admin/vendors/"


class TestAdminVendorsList:
    """GET /api/v1/admin/vendors/ — paginated vendor list."""

    @pytest.mark.asyncio
    async def test_returns_paginated_list_with_correct_meta(
        self,
        vendors_db_session: AsyncSession,
        vendors_client: AsyncClient,
        pending_vendor: Vendor,
        active_vendor: Vendor,
        admin_token: str,
    ):
        """Response must include data array and meta with total, page, limit, pages."""
        resp = await vendors_client.get(
            VENDORS_LIST_URL,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        meta = body["meta"]
        assert "total" in meta
        assert "page" in meta
        assert "limit" in meta
        assert "pages" in meta
        assert meta["page"] == 1
        assert meta["total"] >= 2  # at least pending + active vendor

    @pytest.mark.asyncio
    async def test_status_filter_returns_only_pending(
        self,
        vendors_client: AsyncClient,
        pending_vendor: Vendor,
        active_vendor: Vendor,
        admin_token: str,
    ):
        """?status=PENDING must return only PENDING vendors."""
        resp = await vendors_client.get(
            VENDORS_LIST_URL,
            params={"status": "PENDING"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        for item in data:
            assert item["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_q_filter_matches_business_name(
        self,
        vendors_client: AsyncClient,
        pending_vendor: Vendor,
        admin_token: str,
    ):
        """?q=Pending must match business_name containing 'Pending'."""
        resp = await vendors_client.get(
            VENDORS_LIST_URL,
            params={"q": "Pending"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        names = [item["business_name"] for item in data]
        assert any("Pending" in name for name in names)

    @pytest.mark.asyncio
    async def test_q_filter_matches_contact_email(
        self,
        vendors_client: AsyncClient,
        pending_vendor: Vendor,
        admin_token: str,
    ):
        """?q=pending- must match contact_email containing 'pending-'."""
        resp = await vendors_client.get(
            VENDORS_LIST_URL,
            params={"q": "pending-"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_returns_403_for_non_admin(
        self,
        vendors_client: AsyncClient,
        user_token: str,
    ):
        """Non-admin token must receive HTTP 403."""
        resp = await vendors_client.get(
            VENDORS_LIST_URL,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_FORBIDDEN"

    @pytest.mark.asyncio
    async def test_vendor_item_has_owner_email_field(
        self,
        vendors_client: AsyncClient,
        pending_vendor: Vendor,
        admin_token: str,
    ):
        """Each vendor item must include owner_email mapped from contact_email."""
        resp = await vendors_client.get(
            VENDORS_LIST_URL,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        for item in data:
            assert "owner_email" in item


# ── Tests: PATCH /api/v1/admin/vendors/{id}/status ────────────────────────────

class TestAdminVendorStatusUpdate:
    """PATCH /api/v1/admin/vendors/{id}/status — update vendor status."""

    @pytest.mark.asyncio
    async def test_approve_pending_vendor_sets_active(
        self,
        vendors_db_session: AsyncSession,
        vendors_client: AsyncClient,
        pending_vendor: Vendor,
        admin_token: str,
    ):
        """PATCH with status=ACTIVE on a PENDING vendor must set it to ACTIVE."""
        resp = await vendors_client.patch(
            f"/api/v1/admin/vendors/{pending_vendor.id}/status",
            json={"status": "ACTIVE"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_reject_pending_vendor_sets_rejected(
        self,
        vendors_db_session: AsyncSession,
        vendors_client: AsyncClient,
        pending_vendor: Vendor,
        admin_token: str,
    ):
        """PATCH with status=REJECTED on a PENDING vendor must set it to REJECTED."""
        resp = await vendors_client.patch(
            f"/api/v1/admin/vendors/{pending_vendor.id}/status",
            json={"status": "REJECTED"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_non_existent_vendor_returns_404(
        self,
        vendors_client: AsyncClient,
        admin_token: str,
    ):
        """PATCH on a non-existent vendor_id must return HTTP 404."""
        non_existent_id = uuid.uuid4()
        resp = await vendors_client.patch(
            f"/api/v1/admin/vendors/{non_existent_id}/status",
            json={"status": "ACTIVE"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["success"] is False

    @pytest.mark.asyncio
    async def test_returns_403_for_non_admin(
        self,
        vendors_client: AsyncClient,
        pending_vendor: Vendor,
        user_token: str,
    ):
        """Non-admin token must receive HTTP 403 on status update."""
        resp = await vendors_client.patch(
            f"/api/v1/admin/vendors/{pending_vendor.id}/status",
            json={"status": "ACTIVE"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_FORBIDDEN"

    @pytest.mark.asyncio
    async def test_suspend_active_vendor(
        self,
        vendors_db_session: AsyncSession,
        vendors_client: AsyncClient,
        active_vendor: Vendor,
        admin_token: str,
    ):
        """PATCH with status=SUSPENDED on an ACTIVE vendor must set it to SUSPENDED."""
        resp = await vendors_client.patch(
            f"/api/v1/admin/vendors/{active_vendor.id}/status",
            json={"status": "SUSPENDED"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "SUSPENDED"
