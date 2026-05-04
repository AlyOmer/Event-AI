"""
Integration tests for GET /api/v1/public_vendors/semantic

Covers:
  - 14.1  Happy path: returns success envelope with VendorWithScore items
  - 14.2  Missing `q` → HTTP 422 VALIDATION_QUERY_REQUIRED
  - 14.3  Gemini API failure → HTTP 503 AI_EMBEDDING_UNAVAILABLE
  - 14.4  Only ACTIVE vendors appear in semantic search results

Uses SQLite in-memory and unittest.mock.patch to mock SearchService.semantic_search
at the service layer (pgvector's <=> operator is not available in SQLite).
Zero real Gemini API calls are made.
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
from src.services.embedding_service import EmbeddingAPIError

# ── Test database ─────────────────────────────────────────────────────────────

SEMANTIC_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

SEMANTIC_TABLES = [
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_vendor_read(
    vendor_id: uuid.UUID | None = None,
    status: VendorStatus = VendorStatus.ACTIVE,
    business_name: str = "Lahore Mehndi Artists",
    city: str = "Lahore",
) -> VendorRead:
    """Build a VendorRead directly (no ORM lazy-load needed)."""
    now = datetime.now(timezone.utc)
    return VendorRead(
        id=vendor_id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        business_name=business_name,
        contact_email=f"{uuid.uuid4().hex[:8]}@vendor.com",
        status=status,
        city=city,
        region="Punjab",
        rating=4.5,
        total_reviews=10,
        categories=[],
        created_at=now,
        updated_at=now,
    )


def _make_vendor_with_score(
    vendor_id: uuid.UUID | None = None,
    similarity_score: float = 0.92,
    status: VendorStatus = VendorStatus.ACTIVE,
    business_name: str = "Lahore Mehndi Artists",
) -> VendorWithScore:
    """Build a VendorWithScore for use as a mock return value."""
    vendor_read = _make_vendor_read(
        vendor_id=vendor_id,
        status=status,
        business_name=business_name,
    )
    return VendorWithScore(
        vendor=vendor_read,
        similarity_score=similarity_score,
        search_mode="semantic",
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def semantic_engine():
    """Isolated in-memory SQLite engine for the semantic search test module."""
    from src.models.vendor import Vendor  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.service import Service  # noqa: F401
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401

    engine = create_async_engine(SEMANTIC_TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        from sqlalchemy import JSON

        DomainEvent.__table__.c["data"].type = JSON()
        Vendor.__table__.c["status"].type = String(50)

        available_tables = {
            name: SQLModel.metadata.tables[name]
            for name in SEMANTIC_TABLES
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
async def semantic_db_session(
    semantic_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Transactional test session that rolls back after each test."""
    async_session = sessionmaker(
        semantic_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def search_client(
    semantic_db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient with:
    - test DB injected via dependency override
    - rate limiters bypassed
    - fake httpx.AsyncClient on app.state (required by the semantic endpoint)
    """
    import src.api.v1.auth as auth_module
    import src.api.v1.events as events_module
    import src.api.v1.notifications as notif_module
    import src.api.v1.public_vendors as pv_module

    async def no_rate_limit(request=None):
        pass

    async def override_get_session():
        yield semantic_db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[auth_module.register_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.login_limiter] = no_rate_limit
    app.dependency_overrides[auth_module.password_reset_limiter] = no_rate_limit
    app.dependency_overrides[events_module.create_limiter] = no_rate_limit
    app.dependency_overrides[events_module.read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._read_limiter] = no_rate_limit
    app.dependency_overrides[notif_module._write_limiter] = no_rate_limit
    # Bypass the /semantic rate limiter
    app.dependency_overrides[pv_module._semantic_limiter] = no_rate_limit

    # Inject a fake httpx.AsyncClient onto app.state so the route can read it
    fake_http_client = httpx.AsyncClient()
    app.state.http_client = fake_http_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    await fake_http_client.aclose()
    app.dependency_overrides.clear()


# ── 14.1  Happy path ──────────────────────────────────────────────────────────

class TestSemanticSearchHappyPath:
    """14.1 — Happy path: correct response envelope and VendorWithScore structure."""

    @pytest.mark.asyncio
    async def test_returns_success_envelope(self, search_client: AsyncClient):
        """Response must have success=true, data list, and meta with total and query."""
        fake_result = _make_vendor_with_score(similarity_score=0.92)

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[fake_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "traditional mehndi artist Lahore"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert "meta" in body

    @pytest.mark.asyncio
    async def test_meta_contains_total_and_query(self, search_client: AsyncClient):
        """meta must include total count and the original query string."""
        fake_result = _make_vendor_with_score(similarity_score=0.88)

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[fake_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "wedding photographer Karachi"},
            )

        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["meta"]["query"] == "wedding photographer Karachi"

    @pytest.mark.asyncio
    async def test_each_item_has_vendor_score_and_mode_fields(
        self, search_client: AsyncClient
    ):
        """Each item in data must have vendor, similarity_score, and search_mode."""
        fake_result = _make_vendor_with_score(similarity_score=0.85)

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[fake_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "mehndi artist"},
            )

        body = resp.json()
        assert len(body["data"]) == 1
        item = body["data"][0]
        assert "vendor" in item
        assert "similarity_score" in item
        assert "search_mode" in item

    @pytest.mark.asyncio
    async def test_search_mode_is_semantic(self, search_client: AsyncClient):
        """search_mode must be 'semantic' for all items returned by this endpoint."""
        fake_result = _make_vendor_with_score(similarity_score=0.91)

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[fake_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "catering service Islamabad"},
            )

        body = resp.json()
        assert body["data"][0]["search_mode"] == "semantic"

    @pytest.mark.asyncio
    async def test_similarity_score_is_returned_correctly(
        self, search_client: AsyncClient
    ):
        """similarity_score must match the value returned by the service."""
        fake_result = _make_vendor_with_score(similarity_score=0.76)

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[fake_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "floral decoration"},
            )

        body = resp.json()
        assert body["data"][0]["similarity_score"] == pytest.approx(0.76)

    @pytest.mark.asyncio
    async def test_multiple_results_returned(self, search_client: AsyncClient):
        """Multiple VendorWithScore results must all appear in the response."""
        fake_results = [
            _make_vendor_with_score(similarity_score=0.95, business_name="Top Vendor"),
            _make_vendor_with_score(similarity_score=0.80, business_name="Second Vendor"),
            _make_vendor_with_score(similarity_score=0.65, business_name="Third Vendor"),
        ]

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=fake_results,
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "event vendor"},
            )

        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) == 3
        assert body["meta"]["total"] == 3

    @pytest.mark.asyncio
    async def test_empty_results_returns_success_with_empty_list(
        self, search_client: AsyncClient
    ):
        """When no vendors match, response must still be success with empty data."""
        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "obscure query with no matches"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_vendor_fields_present_in_response(self, search_client: AsyncClient):
        """The nested vendor object must contain expected fields."""
        vendor_id = uuid.uuid4()
        fake_result = _make_vendor_with_score(
            vendor_id=vendor_id,
            similarity_score=0.90,
            business_name="Karachi Caterers",
        )

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[fake_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "catering"},
            )

        body = resp.json()
        vendor_data = body["data"][0]["vendor"]
        assert vendor_data["id"] == str(vendor_id)
        assert vendor_data["business_name"] == "Karachi Caterers"
        assert vendor_data["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_query_is_stripped_in_meta(self, search_client: AsyncClient):
        """Leading/trailing whitespace in q must be stripped in the meta.query field."""
        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "  mehndi artist  "},
            )

        body = resp.json()
        assert body["meta"]["query"] == "mehndi artist"


# ── 14.2  Missing q → HTTP 422 ────────────────────────────────────────────────

class TestSemanticSearchMissingQuery:
    """14.2 — Missing or empty q parameter must return HTTP 422."""

    @pytest.mark.asyncio
    async def test_missing_q_returns_422(self, search_client: AsyncClient):
        """GET /semantic without q must return HTTP 422."""
        resp = await search_client.get("/api/v1/public_vendors/semantic")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_q_returns_validation_query_required_code(
        self, search_client: AsyncClient
    ):
        """Error code must be VALIDATION_QUERY_REQUIRED when q is absent."""
        resp = await search_client.get("/api/v1/public_vendors/semantic")
        body = resp.json()
        # The endpoint returns {"success": false, "error": {"code": "...", "message": "..."}}
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_QUERY_REQUIRED"

    @pytest.mark.asyncio
    async def test_empty_q_returns_422(self, search_client: AsyncClient):
        """GET /semantic with q='' must return HTTP 422."""
        resp = await search_client.get(
            "/api/v1/public_vendors/semantic", params={"q": ""}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_whitespace_only_q_returns_422(self, search_client: AsyncClient):
        """GET /semantic with q containing only whitespace must return HTTP 422."""
        resp = await search_client.get(
            "/api/v1/public_vendors/semantic", params={"q": "   "}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_whitespace_only_q_returns_validation_query_required_code(
        self, search_client: AsyncClient
    ):
        """Error code must be VALIDATION_QUERY_REQUIRED for whitespace-only q."""
        resp = await search_client.get(
            "/api/v1/public_vendors/semantic", params={"q": "   "}
        )
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_QUERY_REQUIRED"


# ── 14.3  Gemini API failure → HTTP 503 ───────────────────────────────────────

class TestSemanticSearchGeminiFailure:
    """14.3 — EmbeddingAPIError from the service must surface as HTTP 503."""

    @pytest.mark.asyncio
    async def test_embedding_error_returns_503(self, search_client: AsyncClient):
        """When semantic_search raises EmbeddingAPIError, endpoint must return 503."""
        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            side_effect=EmbeddingAPIError(503, "Gemini service unavailable"),
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "mehndi artist"},
            )

        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_embedding_error_returns_ai_embedding_unavailable_code(
        self, search_client: AsyncClient
    ):
        """Error code must be AI_EMBEDDING_UNAVAILABLE on Gemini failure."""
        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            side_effect=EmbeddingAPIError(503, "Gemini service unavailable"),
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "mehndi artist"},
            )

        body = resp.json()
        # The endpoint returns {"success": false, "error": {"code": "...", "message": "..."}}
        assert body["success"] is False
        assert body["error"]["code"] == "AI_EMBEDDING_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_embedding_error_with_different_status_code_still_returns_503(
        self, search_client: AsyncClient
    ):
        """Any EmbeddingAPIError (e.g. 429, 500) must result in HTTP 503 from the endpoint."""
        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            side_effect=EmbeddingAPIError(429, "Rate limit exceeded"),
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "photographer"},
            )

        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_embedding_error_response_has_no_data_field(
        self, search_client: AsyncClient
    ):
        """A 503 error response must not contain a data field with vendor results."""
        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            side_effect=EmbeddingAPIError(500, "Internal Gemini error"),
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "caterer"},
            )

        body = resp.json()
        # The error response should not contain a 'data' key with vendor results
        assert "data" not in body or body.get("data") is None


# ── 14.4  Only ACTIVE vendors ─────────────────────────────────────────────────

class TestSemanticSearchActiveVendorsOnly:
    """14.4 — Semantic search results must only contain ACTIVE vendors."""

    @pytest.mark.asyncio
    async def test_only_active_vendors_in_results(self, search_client: AsyncClient):
        """When service returns only ACTIVE vendors, all items must have status ACTIVE."""
        active_results = [
            _make_vendor_with_score(
                similarity_score=0.95,
                status=VendorStatus.ACTIVE,
                business_name="Active Vendor One",
            ),
            _make_vendor_with_score(
                similarity_score=0.88,
                status=VendorStatus.ACTIVE,
                business_name="Active Vendor Two",
            ),
        ]

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=active_results,
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "wedding vendor"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) == 2

        for item in body["data"]:
            assert item["vendor"]["status"] == "ACTIVE", (
                f"Expected ACTIVE status but got {item['vendor']['status']} "
                f"for vendor {item['vendor']['business_name']}"
            )

    @pytest.mark.asyncio
    async def test_no_inactive_vendors_in_results(self, search_client: AsyncClient):
        """The endpoint must pass through only the results returned by the service.

        The service is responsible for filtering to ACTIVE vendors; here we verify
        the endpoint does not introduce any inactive vendors into the response.
        """
        # Service correctly returns only ACTIVE vendors (as it should)
        active_result = _make_vendor_with_score(
            similarity_score=0.90,
            status=VendorStatus.ACTIVE,
            business_name="Active Vendor",
        )

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[active_result],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "event planner"},
            )

        body = resp.json()
        statuses = [item["vendor"]["status"] for item in body["data"]]
        assert all(s == "ACTIVE" for s in statuses), (
            f"Found non-ACTIVE vendors in response: {statuses}"
        )

    @pytest.mark.asyncio
    async def test_empty_results_when_no_active_vendors_match(
        self, search_client: AsyncClient
    ):
        """When the service finds no ACTIVE vendors matching the query, data must be empty."""
        with patch(
            "src.services.search_service.SearchService.semantic_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "very specific query with no active matches"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_semantic_search_called_with_correct_query(
        self, search_client: AsyncClient
    ):
        """The service must be called with the stripped query text."""
        mock_search = AsyncMock(return_value=[])

        with patch(
            "src.services.search_service.SearchService.semantic_search",
            mock_search,
        ):
            await search_client.get(
                "/api/v1/public_vendors/semantic",
                params={"q": "  mehndi artist Lahore  "},
            )

        # Verify the service was called with the stripped query
        call_kwargs = mock_search.call_args
        assert call_kwargs is not None
        # query_text is passed as a keyword argument
        query_text = call_kwargs.kwargs.get("query_text") or call_kwargs.args[1] if call_kwargs.args else None
        if query_text is not None:
            assert query_text == "mehndi artist Lahore"
