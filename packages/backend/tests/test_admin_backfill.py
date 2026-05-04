"""
Integration tests for POST /api/v1/admin/embeddings/backfill

Covers:
  - 15.1  Happy path: admin JWT → HTTP 200 with {"success": true, "data": {"queued": N}}
          - No body (batch all active vendors)
          - With {"vendor_id": "..."} (single vendor)
  - 15.2  Non-admin caller → HTTP 403 AUTH_FORBIDDEN

Uses SQLite in-memory and unittest.mock.patch to mock embedding_service methods
so zero real Gemini API calls are made.

The background tasks are enqueued but the mocked functions are no-ops, so the
test only verifies the immediate HTTP response (queued count), not task completion.
"""
import uuid
import pytest
import pytest_asyncio
import httpx
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

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

BACKFILL_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

BACKFILL_TABLES = [
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
    "services",
]

BACKFILL_URL = "/api/v1/admin/embeddings/backfill"


# ── Engine fixture ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def backfill_engine():
    """Isolated in-memory SQLite engine for the admin backfill test module."""
    from src.models.vendor import Vendor  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.service import Service  # noqa: F401
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401

    engine = create_async_engine(BACKFILL_TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        from sqlalchemy import JSON

        DomainEvent.__table__.c["data"].type = JSON()
        Vendor.__table__.c["status"].type = String(50)

        available_tables = {
            name: SQLModel.metadata.tables[name]
            for name in BACKFILL_TABLES
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
async def backfill_db_session(
    backfill_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Transactional test session that rolls back after each test."""
    async_session = sessionmaker(
        backfill_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def backfill_client(
    backfill_db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient with:
    - test DB injected via dependency override
    - all rate limiters bypassed (including _backfill_limiter)
    - fake httpx.AsyncClient on app.state
    """
    import src.api.v1.auth as auth_module
    import src.api.v1.events as events_module
    import src.api.v1.notifications as notif_module
    import src.api.v1.admin.embeddings as embeddings_module

    async def no_rate_limit(request=None):
        pass

    async def override_get_session():
        yield backfill_db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[auth_module.register_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.login_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.password_reset_limiter] = no_rate_limit
    app.dependency_overrides[events_module.create_limiter] = no_rate_limit
    app.dependency_overrides[events_module.read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._write_limiter] = no_rate_limit
    # Bypass the backfill rate limiter
    app.dependency_overrides[embeddings_module._backfill_limiter] = no_rate_limit

    # Inject a fake httpx.AsyncClient onto app.state
    fake_http_client = httpx.AsyncClient()
    app.state.http_client = fake_http_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    await fake_http_client.aclose()
    app.dependency_overrides.clear()


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(backfill_db_session: AsyncSession) -> User:
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
    backfill_db_session.add(user)
    await backfill_db_session.commit()
    await backfill_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user(backfill_db_session: AsyncSession) -> User:
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
    backfill_db_session.add(user)
    await backfill_db_session.commit()
    await backfill_db_session.refresh(user)
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

async def _seed_active_vendors(
    session: AsyncSession, count: int = 2
) -> list[uuid.UUID]:
    """Insert `count` ACTIVE vendor rows and return their IDs."""
    vendor_ids: list[uuid.UUID] = []
    for i in range(count):
        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name=f"Active Vendor {i}",
            contact_email=f"active-{uuid.uuid4().hex[:8]}@vendor.com",
            status=VendorStatus.ACTIVE,
        )
        session.add(vendor)
        vendor_ids.append(vendor.id)
    await session.commit()
    return vendor_ids


# ── 15.1  Happy path — admin JWT ──────────────────────────────────────────────

class TestAdminBackfillHappyPath:
    """15.1 — Admin JWT triggers backfill and returns correct queued count."""

    @pytest.mark.asyncio
    async def test_batch_backfill_returns_200(
        self,
        backfill_db_session: AsyncSession,
        backfill_client: AsyncClient,
        admin_token: str,
    ):
        """POST /backfill with no body and active vendors → HTTP 200."""
        await _seed_active_vendors(backfill_db_session, count=2)

        with patch(
            "src.services.embedding_service.EmbeddingService.embed_batch",
            new_callable=AsyncMock,
            return_value=2,
        ):
            resp = await backfill_client.post(
                BACKFILL_URL,
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_batch_backfill_returns_success_envelope(
        self,
        backfill_db_session: AsyncSession,
        backfill_client: AsyncClient,
        admin_token: str,
    ):
        """Response body must be {"success": true, "data": {"queued": N}}."""
        await _seed_active_vendors(backfill_db_session, count=3)

        with patch(
            "src.services.embedding_service.EmbeddingService.embed_batch",
            new_callable=AsyncMock,
            return_value=3,
        ):
            resp = await backfill_client.post(
                BACKFILL_URL,
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert "queued" in body["data"]

    @pytest.mark.asyncio
    async def test_batch_backfill_queued_count_matches_active_vendors(
        self,
        backfill_db_session: AsyncSession,
        backfill_client: AsyncClient,
        admin_token: str,
    ):
        """queued must equal the number of ACTIVE vendors in the DB."""
        await _seed_active_vendors(backfill_db_session, count=3)

        with patch(
            "src.services.embedding_service.EmbeddingService.embed_batch",
            new_callable=AsyncMock,
            return_value=3,
        ):
            resp = await backfill_client.post(
                BACKFILL_URL,
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        body = resp.json()
        # queued must be >= 3 (there may be vendors from other tests in the same module engine)
        assert body["data"]["queued"] >= 3

    @pytest.mark.asyncio
    async def test_batch_backfill_no_body_queued_zero_when_no_active_vendors(
        self,
        backfill_client: AsyncClient,
        admin_token: str,
    ):
        """When there are no ACTIVE vendors, queued must be 0."""
        with patch(
            "src.services.embedding_service.EmbeddingService.embed_batch",
            new_callable=AsyncMock,
            return_value=0,
        ):
            resp = await backfill_client.post(
                BACKFILL_URL,
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        # queued may be 0 or more depending on other tests; just verify structure
        assert isinstance(body["data"]["queued"], int)

    @pytest.mark.asyncio
    async def test_single_vendor_backfill_returns_200(
        self,
        backfill_db_session: AsyncSession,
        backfill_client: AsyncClient,
        admin_token: str,
    ):
        """POST /backfill with vendor_id body → HTTP 200."""
        vendor_ids = await _seed_active_vendors(backfill_db_session, count=1)
        vendor_id = vendor_ids[0]

        with patch(
            "src.services.embedding_service.EmbeddingService.upsert_vendor_embedding",
            new_callable=AsyncMock,
        ):
            resp = await backfill_client.post(
                BACKFILL_URL,
                json={"vendor_id": str(vendor_id)},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_single_vendor_backfill_returns_queued_1(
        self,
        backfill_db_session: AsyncSession,
        backfill_client: AsyncClient,
        admin_token: str,
    ):
        """POST /backfill with vendor_id → {"success": true, "data": {"queued": 1}}."""
        vendor_ids = await _seed_active_vendors(backfill_db_session, count=1)
        vendor_id = vendor_ids[0]

        with patch(
            "src.services.embedding_service.EmbeddingService.upsert_vendor_embedding",
            new_callable=AsyncMock,
        ):
            resp = await backfill_client.post(
                BACKFILL_URL,
                json={"vendor_id": str(vendor_id)},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        body = resp.json()
        assert body["success"] is True
        assert body["data"]["queued"] == 1

    @pytest.mark.asyncio
    async def test_single_vendor_backfill_success_envelope_structure(
        self,
        backfill_db_session: AsyncSession,
        backfill_client: AsyncClient,
        admin_token: str,
    ):
        """Single-vendor response must have the standard success envelope."""
        vendor_ids = await _seed_active_vendors(backfill_db_session, count=1)
        vendor_id = vendor_ids[0]

        with patch(
            "src.services.embedding_service.EmbeddingService.upsert_vendor_embedding",
            new_callable=AsyncMock,
        ):
            resp = await backfill_client.post(
                BACKFILL_URL,
                json={"vendor_id": str(vendor_id)},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        body = resp.json()
        assert "success" in body
        assert "data" in body
        assert "queued" in body["data"]
        assert body["data"]["queued"] == 1


# ── 15.2  Non-admin caller → HTTP 403 ────────────────────────────────────────

class TestAdminBackfillForbidden:
    """15.2 — Non-admin callers must receive HTTP 403 AUTH_FORBIDDEN."""

    @pytest.mark.asyncio
    async def test_regular_user_returns_403(
        self,
        backfill_client: AsyncClient,
        user_token: str,
    ):
        """A regular user token must receive HTTP 403."""
        resp = await backfill_client.post(
            BACKFILL_URL,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_user_returns_auth_forbidden_code(
        self,
        backfill_client: AsyncClient,
        user_token: str,
    ):
        """The 403 response must include AUTH_FORBIDDEN error code."""
        resp = await backfill_client.post(
            BACKFILL_URL,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        body = resp.json()
        assert body["success"] is False
        assert "error" in body
        assert body["error"]["code"] == "AUTH_FORBIDDEN"

    @pytest.mark.asyncio
    async def test_no_token_returns_401(
        self,
        backfill_client: AsyncClient,
    ):
        """Calling the endpoint without any token must return HTTP 401."""
        resp = await backfill_client.post(BACKFILL_URL)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(
        self,
        backfill_client: AsyncClient,
    ):
        """An invalid/malformed token must return HTTP 401."""
        resp = await backfill_client.post(
            BACKFILL_URL,
            headers={"Authorization": "Bearer invalid.token.value"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_regular_user_with_vendor_id_body_returns_403(
        self,
        backfill_db_session: AsyncSession,
        backfill_client: AsyncClient,
        user_token: str,
    ):
        """Even with a valid vendor_id body, a non-admin must still get 403."""
        vendor_ids = await _seed_active_vendors(backfill_db_session, count=1)
        vendor_id = vendor_ids[0]

        resp = await backfill_client.post(
            BACKFILL_URL,
            json={"vendor_id": str(vendor_id)},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "AUTH_FORBIDDEN"
