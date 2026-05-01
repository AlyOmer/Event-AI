"""
Integration tests for admin users endpoint:
  GET /api/v1/admin/users/

Uses httpx.AsyncClient + ASGITransport with an isolated in-memory SQLite
session — no real database or server required.

Test fixtures:
- admin_user   — User with role="admin"
- regular_user — User with role="user"
- vendor_user  — User with role="vendor" and a linked Vendor
- admin_token  — JWT for admin_user
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
from src.models.booking import Booking  # noqa: F401
from src.models.notification import Notification  # noqa: F401
from src.models.notification_preference import NotificationPreference  # noqa: F401
from src.models.vendor import Vendor, VendorStatus
from src.services.auth_service import AuthService

# ── Test database ─────────────────────────────────────────────────────────────

USERS_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

USERS_TABLES = [
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
async def users_engine():
    """Isolated in-memory SQLite engine for the users test module."""
    from src.models.vendor import Vendor  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.service import Service  # noqa: F401
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401

    engine = create_async_engine(USERS_TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import JSON
        DomainEvent.__table__.c["data"].type = JSON()
        Vendor.__table__.c["status"].type = String(50)

        available_tables = {
            name: SQLModel.metadata.tables[name]
            for name in USERS_TABLES
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
async def users_db_session(users_engine) -> AsyncGenerator[AsyncSession, None]:
    """Transactional test session that rolls back after each test."""
    async_session = sessionmaker(users_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def users_client(users_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with test DB session injected and rate limiting bypassed."""
    import src.api.v1.auth as auth_module
    import src.api.v1.events as events_module
    import src.api.v1.notifications as notif_module

    async def no_rate_limit(request=None):
        pass

    async def override_get_session():
        yield users_db_session

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
async def admin_user(users_db_session: AsyncSession) -> User:
    """A User with role='admin'."""
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
    users_db_session.add(user)
    await users_db_session.commit()
    await users_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user(users_db_session: AsyncSession) -> User:
    """A User with role='user'."""
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
    users_db_session.add(user)
    await users_db_session.commit()
    await users_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def vendor_user(users_db_session: AsyncSession) -> tuple[User, Vendor]:
    """A User with role='vendor' and a linked Vendor."""
    user = User(
        id=uuid.uuid4(),
        email=f"vendor-{uuid.uuid4().hex[:8]}@test.com",
        first_name="Vendor",
        last_name="User",
        role="vendor",
        is_active=True,
        email_verified=True,
        password_hash=AuthService.hash_password("VendorPass123!"),
    )
    users_db_session.add(user)
    await users_db_session.commit()
    await users_db_session.refresh(user)

    vendor = Vendor(
        id=uuid.uuid4(),
        user_id=user.id,
        business_name="Test Vendor Business",
        contact_email=user.email,
        status=VendorStatus.ACTIVE,
        city="Karachi",
        region="Sindh",
    )
    users_db_session.add(vendor)
    await users_db_session.commit()
    await users_db_session.refresh(vendor)

    return user, vendor


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


# ── Tests: GET /api/v1/admin/users/ ───────────────────────────────────────────

USERS_LIST_URL = "/api/v1/admin/users/"


class TestAdminUsersList:
    """GET /api/v1/admin/users/ — paginated user list with optional vendor join."""

    @pytest.mark.asyncio
    async def test_returns_paginated_list_with_correct_meta(
        self,
        users_client: AsyncClient,
        admin_user: User,
        regular_user: User,
        admin_token: str,
    ):
        """Response must include data array and meta with total, page, limit, pages."""
        resp = await users_client.get(
            USERS_LIST_URL,
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
        assert meta["total"] >= 2  # at least admin + regular user

    @pytest.mark.asyncio
    async def test_role_filter_returns_only_vendor_users(
        self,
        users_client: AsyncClient,
        admin_user: User,
        vendor_user: tuple[User, Vendor],
        admin_token: str,
    ):
        """?role=vendor must return only users with role='vendor'."""
        resp = await users_client.get(
            USERS_LIST_URL,
            params={"role": "vendor"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        for item in data:
            assert item["role"] == "vendor"

    @pytest.mark.asyncio
    async def test_q_filter_matches_email(
        self,
        users_client: AsyncClient,
        regular_user: User,
        admin_token: str,
    ):
        """?q=user- must match email containing 'user-'."""
        resp = await users_client.get(
            USERS_LIST_URL,
            params={"q": "user-"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_q_filter_matches_first_name(
        self,
        users_client: AsyncClient,
        regular_user: User,
        admin_token: str,
    ):
        """?q=Regular must match first_name containing 'Regular'."""
        resp = await users_client.get(
            USERS_LIST_URL,
            params={"q": "Regular"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        names = [item["first_name"] for item in data if item["first_name"]]
        assert any("Regular" in name for name in names)

    @pytest.mark.asyncio
    async def test_q_filter_matches_last_name(
        self,
        users_client: AsyncClient,
        admin_user: User,
        admin_token: str,
    ):
        """?q=User must match last_name containing 'User'."""
        resp = await users_client.get(
            USERS_LIST_URL,
            params={"q": "User"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_returns_403_for_non_admin(
        self,
        users_client: AsyncClient,
        user_token: str,
    ):
        """Non-admin token must receive HTTP 403."""
        resp = await users_client.get(
            USERS_LIST_URL,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_FORBIDDEN"

    @pytest.mark.asyncio
    async def test_user_with_vendor_includes_vendor_summary(
        self,
        users_client: AsyncClient,
        vendor_user: tuple[User, Vendor],
        admin_token: str,
    ):
        """User with linked vendor must include vendor summary in response."""
        user, vendor = vendor_user
        resp = await users_client.get(
            USERS_LIST_URL,
            params={"role": "vendor"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        
        # Find the vendor user in the response
        vendor_user_item = next((item for item in data if item["email"] == user.email), None)
        assert vendor_user_item is not None
        assert vendor_user_item["vendor"] is not None
        assert vendor_user_item["vendor"]["id"] == str(vendor.id)
        assert vendor_user_item["vendor"]["business_name"] == vendor.business_name
        assert vendor_user_item["vendor"]["status"] == vendor.status

    @pytest.mark.asyncio
    async def test_user_without_vendor_has_null_vendor(
        self,
        users_client: AsyncClient,
        regular_user: User,
        admin_token: str,
    ):
        """User without linked vendor must have vendor=null in response."""
        resp = await users_client.get(
            USERS_LIST_URL,
            params={"role": "user"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        
        # Find the regular user in the response
        regular_user_item = next((item for item in data if item["email"] == regular_user.email), None)
        assert regular_user_item is not None
        assert regular_user_item["vendor"] is None

    @pytest.mark.asyncio
    async def test_user_item_has_all_required_fields(
        self,
        users_client: AsyncClient,
        admin_user: User,
        admin_token: str,
    ):
        """Each user item must include all required fields from AdminUserRead schema."""
        resp = await users_client.get(
            USERS_LIST_URL,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        
        required_fields = {
            "id", "email", "first_name", "last_name", "role",
            "is_active", "email_verified", "last_login_at", "created_at", "vendor"
        }
        for item in data:
            assert required_fields.issubset(item.keys())
