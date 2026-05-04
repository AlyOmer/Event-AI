"""
Integration tests for GET /api/v1/public_vendors/search

Covers:
  - 10.1  mode validation (keyword | semantic | hybrid, default hybrid)
  - 10.2  delegation to the correct SearchService method per mode
  - 10.3  consistent response envelope for all modes
  - 10.4  rate limit (60/min) — verified via dependency override

Uses SQLite in-memory and unittest.mock.patch to mock the service layer,
so no real DB queries (which use PostgreSQL-specific functions) are needed.
"""
import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone
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
from src.schemas.vendor import VendorRead
from src.schemas.search import VendorWithScore

# ── Test database ─────────────────────────────────────────────────────────────

SEARCH_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

SEARCH_TABLES = [
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


def _make_vendor_read(vendor_id: uuid.UUID | None = None) -> VendorRead:
    """Build a VendorRead directly from a dict (no ORM lazy-load needed)."""
    now = datetime.now(timezone.utc)
    return VendorRead(
        id=vendor_id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        business_name="Lahore Mehndi Artists",
        contact_email="mehndi@vendor.com",
        status=VendorStatus.ACTIVE,
        city="Lahore",
        region="Punjab",
        rating=4.5,
        total_reviews=10,
        categories=[],
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture(scope="module")
async def search_engine():
    """Isolated in-memory SQLite engine for the search test module."""
    from src.models.vendor import Vendor  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.service import Service  # noqa: F401
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401

    engine = create_async_engine(SEARCH_TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import JSON

        DomainEvent.__table__.c["data"].type = JSON()
        Vendor.__table__.c["status"].type = String(50)

        available_tables = {
            name: SQLModel.metadata.tables[name]
            for name in SEARCH_TABLES
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
async def search_db_session(search_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(search_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def search_client(search_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with test DB, rate limiting bypassed, and fake http_client on app.state."""
    import src.api.v1.auth as auth_module
    import src.api.v1.events as events_module
    import src.api.v1.notifications as notif_module
    import src.api.v1.public_vendors as pv_module

    async def no_rate_limit(request=None):
        pass

    async def override_get_session():
        yield search_db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[auth_module.register_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.login_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.password_reset_limiter] = no_rate_limit
    app.dependency_overrides[events_module.create_limiter] = no_rate_limit
    app.dependency_overrides[events_module.read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._write_limiter] = no_rate_limit
    # Bypass the /search and /semantic rate limiters
    app.dependency_overrides[pv_module._search_limiter] = no_rate_limit
    app.dependency_overrides[pv_module._semantic_limiter] = no_rate_limit

    # Inject a real httpx.AsyncClient onto app.state so the route can read it.
    fake_http_client = httpx.AsyncClient()
    app.state.http_client = fake_http_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    await fake_http_client.aclose()
    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSearchEndpointValidation:
    """10.1 — Input validation tests."""

    @pytest.mark.asyncio
    async def test_missing_q_returns_422(self, search_client: AsyncClient):
        resp = await search_client.get("/api/v1/public_vendors/search")
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_QUERY_REQUIRED"

    @pytest.mark.asyncio
    async def test_empty_q_returns_422(self, search_client: AsyncClient):
        resp = await search_client.get("/api/v1/public_vendors/search", params={"q": "   "})
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_QUERY_REQUIRED"

    @pytest.mark.asyncio
    async def test_invalid_mode_returns_422(self, search_client: AsyncClient):
        resp = await search_client.get(
            "/api/v1/public_vendors/search",
            params={"q": "mehndi", "mode": "fuzzy"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_INVALID_MODE"

    @pytest.mark.asyncio
    async def test_limit_above_50_rejected(self, search_client: AsyncClient):
        """FastAPI Query(ge=1, le=50) rejects limit > 50 with 422."""
        resp = await search_client.get(
            "/api/v1/public_vendors/search",
            params={"q": "mehndi", "mode": "keyword", "limit": 100},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_modes_accepted(self, search_client: AsyncClient):
        """All three valid mode values should not return 422 for mode validation."""
        for mode in ("keyword", "semantic", "hybrid"):
            with patch(
                "src.services.search_service.SearchService.search_vendors",
                new_callable=AsyncMock,
                return_value=([], 0),
            ), patch(
                "src.services.search_service.SearchService.semantic_search",
                new_callable=AsyncMock,
                return_value=[],
            ), patch(
                "src.services.search_service.SearchService.hybrid_search",
                new_callable=AsyncMock,
                return_value=[],
            ):
                resp = await search_client.get(
                    "/api/v1/public_vendors/search",
                    params={"q": "mehndi", "mode": mode},
                )
            assert resp.status_code == 200, f"mode={mode} unexpectedly rejected"


class TestSearchEndpointKeywordMode:
    """10.2 / 10.3 — keyword mode delegates to search_vendors and returns envelope."""

    @pytest.mark.asyncio
    async def test_keyword_mode_returns_success_envelope(self, search_client: AsyncClient):
        vendor_read = _make_vendor_read()
        fake_vendor = Vendor(
            id=vendor_read.id,
            user_id=vendor_read.user_id,
            business_name=vendor_read.business_name,
            contact_email=vendor_read.contact_email,
            status=VendorStatus.ACTIVE,
            city=vendor_read.city,
            region=vendor_read.region,
            rating=vendor_read.rating,
        )

        with patch(
            "src.services.search_service.SearchService.search_vendors",
            new_callable=AsyncMock,
            return_value=([fake_vendor], 1),
        ), patch(
            "src.schemas.vendor.VendorRead.model_validate",
            return_value=vendor_read,
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "Lahore Mehndi", "mode": "keyword"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["mode"] == "keyword"
        assert body["meta"]["query"] == "Lahore Mehndi"
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_keyword_mode_wraps_vendors_in_vendor_with_score(
        self, search_client: AsyncClient
    ):
        vendor_read = _make_vendor_read()
        fake_vendor = Vendor(
            id=vendor_read.id,
            user_id=vendor_read.user_id,
            business_name=vendor_read.business_name,
            contact_email=vendor_read.contact_email,
            status=VendorStatus.ACTIVE,
            city=vendor_read.city,
            region=vendor_read.region,
            rating=vendor_read.rating,
        )

        with patch(
            "src.services.search_service.SearchService.search_vendors",
            new_callable=AsyncMock,
            return_value=([fake_vendor], 1),
        ), patch(
            "src.schemas.vendor.VendorRead.model_validate",
            return_value=vendor_read,
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "Lahore Mehndi", "mode": "keyword"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        item = body["data"][0]
        assert "vendor" in item
        assert "similarity_score" in item
        assert "search_mode" in item
        assert item["search_mode"] == "keyword"
        assert item["similarity_score"] == 0.0

    @pytest.mark.asyncio
    async def test_keyword_mode_empty_results(self, search_client: AsyncClient):
        with patch(
            "src.services.search_service.SearchService.search_vendors",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "nonexistent vendor xyz", "mode": "keyword"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_default_mode_is_hybrid(self, search_client: AsyncClient):
        """When mode is omitted, the meta should reflect 'hybrid'."""
        with patch(
            "src.services.search_service.SearchService.hybrid_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "mehndi"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["mode"] == "hybrid"


class TestSearchEndpointSemanticMode:
    """10.2 / 10.3 — semantic mode delegates to semantic_search and returns envelope."""

    @pytest.mark.asyncio
    async def test_semantic_mode_returns_success_envelope(self, search_client: AsyncClient):
        vendor_read = _make_vendor_read()
        fake_result = VendorWithScore(
            vendor=vendor_read,
            similarity_score=0.92,
            search_mode="semantic",
        )

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[fake_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "traditional mehndi artist", "mode": "semantic"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["meta"]["mode"] == "semantic"
        assert body["meta"]["query"] == "traditional mehndi artist"
        assert len(body["data"]) == 1
        assert body["data"][0]["search_mode"] == "semantic"
        assert body["data"][0]["similarity_score"] == pytest.approx(0.92)

    @pytest.mark.asyncio
    async def test_semantic_mode_embedding_error_returns_503(self, search_client: AsyncClient):
        from src.services.embedding_service import EmbeddingAPIError

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            side_effect=EmbeddingAPIError(503, "Gemini unavailable"),
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "mehndi", "mode": "semantic"},
            )

        assert resp.status_code == 503
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AI_EMBEDDING_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_semantic_mode_empty_results(self, search_client: AsyncClient):
        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "obscure query", "mode": "semantic"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0


class TestSearchEndpointHybridMode:
    """10.2 / 10.3 — hybrid mode delegates to hybrid_search and returns envelope."""

    @pytest.mark.asyncio
    async def test_hybrid_mode_returns_success_envelope(self, search_client: AsyncClient):
        vendor_read = _make_vendor_read()
        fake_result = VendorWithScore(
            vendor=vendor_read,
            similarity_score=0.75,
            search_mode="hybrid",
        )

        with patch(
            "src.services.search_service.SearchService.hybrid_search",
            new_callable=AsyncMock,
            return_value=[fake_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "mehndi Lahore", "mode": "hybrid"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["meta"]["mode"] == "hybrid"
        assert body["meta"]["query"] == "mehndi Lahore"
        assert len(body["data"]) == 1
        assert body["data"][0]["search_mode"] == "hybrid"
        assert body["data"][0]["similarity_score"] == pytest.approx(0.75)

    @pytest.mark.asyncio
    async def test_hybrid_mode_embedding_error_returns_503(self, search_client: AsyncClient):
        from src.services.embedding_service import EmbeddingAPIError

        with patch(
            "src.services.search_service.SearchService.hybrid_search",
            new_callable=AsyncMock,
            side_effect=EmbeddingAPIError(503, "Gemini unavailable"),
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "mehndi", "mode": "hybrid"},
            )

        assert resp.status_code == 503
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AI_EMBEDDING_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_hybrid_mode_empty_results(self, search_client: AsyncClient):
        with patch(
            "src.services.search_service.SearchService.hybrid_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/search",
                params={"q": "obscure query", "mode": "hybrid"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0


class TestSearchEndpointResponseEnvelopeConsistency:
    """10.3 — All modes return the same envelope shape."""

    @pytest.mark.asyncio
    async def test_all_modes_return_same_envelope_shape(self, search_client: AsyncClient):
        vendor_read = _make_vendor_read()
        fake_result = VendorWithScore(
            vendor=vendor_read,
            similarity_score=0.5,
            search_mode="hybrid",
        )

        for mode in ("keyword", "semantic", "hybrid"):
            if mode == "keyword":
                ctx = patch(
                    "src.services.search_service.SearchService.search_vendors",
                    new_callable=AsyncMock,
                    return_value=([], 0),
                )
            elif mode == "semantic":
                ctx = patch(
                    "src.services.search_service.SearchService.semantic_search",
                    new_callable=AsyncMock,
                    return_value=[fake_result],
                )
            else:
                ctx = patch(
                    "src.services.search_service.SearchService.hybrid_search",
                    new_callable=AsyncMock,
                    return_value=[fake_result],
                )

            with ctx:
                resp = await search_client.get(
                    "/api/v1/public_vendors/search",
                    params={"q": "Lahore Mehndi", "mode": mode},
                )

            assert resp.status_code == 200, f"mode={mode} failed: {resp.text}"
            body = resp.json()
            # All modes must have these top-level keys
            assert "success" in body, f"mode={mode}: missing 'success'"
            assert "data" in body, f"mode={mode}: missing 'data'"
            assert "meta" in body, f"mode={mode}: missing 'meta'"
            # All modes must have these meta keys
            assert "total" in body["meta"], f"mode={mode}: missing meta.total"
            assert "query" in body["meta"], f"mode={mode}: missing meta.query"
            assert "mode" in body["meta"], f"mode={mode}: missing meta.mode"
            assert body["meta"]["mode"] == mode, f"mode={mode}: meta.mode mismatch"
            assert body["meta"]["query"] == "Lahore Mehndi", f"mode={mode}: meta.query mismatch"
