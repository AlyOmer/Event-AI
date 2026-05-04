"""
Unit tests for EmbeddingService.

Covers:
  - 12.1  generate_vendor_text: normal vendor, None description, no services, no categories
  - 12.2  Property-based test (Hypothesis): business_name and city always appear in output
  - 12.3  upsert_vendor_embedding idempotency: Gemini called exactly once for unchanged content

Uses SQLite in-memory for the idempotency test and respx to mock the Gemini
embeddings endpoint — zero real network calls.
"""
import hashlib
import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator

import httpx
import respx
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import String
from sqlmodel import SQLModel

from src.models.vendor import Vendor, VendorStatus
from src.models.service import Service
from src.models.vendor_embedding import VendorEmbedding
from src.services.embedding_service import EmbeddingService

# ── Helpers ───────────────────────────────────────────────────────────────────

EMBEDDING_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

EMBEDDING_TABLES = [
    "users",
    "vendors",
    "categories",
    "vendor_categories",
    "services",
    "vendor_embeddings",
]


def _make_vendor(
    *,
    business_name: str = "Lahore Mehndi Artists",
    city: str = "Lahore",
    region: str = "Punjab",
    description: str | None = "Expert mehndi for weddings.",
    contact_email: str | None = None,
) -> Vendor:
    """Build an in-memory Vendor object (not persisted to DB)."""
    return Vendor(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        business_name=business_name,
        city=city,
        region=region,
        description=description,
        contact_email=contact_email or f"{uuid.uuid4().hex[:8]}@vendor.com",
        status=VendorStatus.ACTIVE,
    )


def _make_service(
    *,
    name: str = "Bridal Mehndi",
    price_min: float | None = 5000.0,
    price_max: float | None = 15000.0,
    is_active: bool = True,
) -> Service:
    """Build an in-memory Service object (not persisted to DB)."""
    return Service(
        id=uuid.uuid4(),
        vendor_id=uuid.uuid4(),
        name=name,
        price_min=price_min,
        price_max=price_max,
        is_active=is_active,
    )


# ── 12.1  generate_vendor_text unit tests ─────────────────────────────────────

class TestGenerateVendorText:
    """Unit tests for EmbeddingService.generate_vendor_text (pure function)."""

    def test_normal_vendor_contains_business_name(self):
        """Output must contain the vendor's business_name."""
        vendor = _make_vendor(business_name="Karachi Caterers")
        services = [_make_service(name="Full Catering")]
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Karachi Caterers" in text

    def test_normal_vendor_contains_city_and_region(self):
        """Output must contain city and region in the Location segment."""
        vendor = _make_vendor(city="Karachi", region="Sindh")
        services = []
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Karachi" in text
        assert "Sindh" in text

    def test_normal_vendor_contains_description(self):
        """When description is set, output must include the Description segment."""
        vendor = _make_vendor(description="Award-winning caterers since 1990.")
        services = []
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Description:" in text
        assert "Award-winning caterers since 1990." in text

    def test_normal_vendor_contains_active_services(self):
        """Active services must appear in the Services segment."""
        vendor = _make_vendor()
        services = [
            _make_service(name="Bridal Mehndi", price_min=5000, price_max=15000),
            _make_service(name="Party Mehndi", price_min=2000, price_max=5000),
        ]
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Services:" in text
        assert "Bridal Mehndi" in text
        assert "Party Mehndi" in text

    def test_normal_vendor_text_ends_with_period(self):
        """Output must always end with a period."""
        vendor = _make_vendor()
        services = [_make_service()]
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert text.endswith(".")

    def test_none_description_omits_description_segment(self):
        """When description is None, the Description segment must not appear."""
        vendor = _make_vendor(description=None)
        services = []
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Description:" not in text

    def test_empty_string_description_omits_description_segment(self):
        """When description is an empty string, the Description segment must not appear."""
        vendor = _make_vendor(description="")
        services = []
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Description:" not in text

    def test_whitespace_only_description_omits_description_segment(self):
        """When description is whitespace-only, the Description segment must not appear."""
        vendor = _make_vendor(description="   ")
        services = []
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Description:" not in text

    def test_no_services_omits_services_segment(self):
        """When services list is empty, the Services segment must not appear."""
        vendor = _make_vendor()
        text = EmbeddingService.generate_vendor_text(vendor, [])
        assert "Services:" not in text

    def test_all_inactive_services_omits_services_segment(self):
        """When all services are inactive, the Services segment must not appear."""
        vendor = _make_vendor()
        services = [
            _make_service(name="Inactive Service", is_active=False),
        ]
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Services:" not in text

    def test_no_categories_does_not_crash(self):
        """Vendors with no categories should produce valid output without errors."""
        vendor = _make_vendor()
        # categories are not part of the text — just verify no crash
        vendor.categories = []
        text = EmbeddingService.generate_vendor_text(vendor, [])
        assert isinstance(text, str)
        assert len(text) > 0

    def test_service_with_price_range_formatted_correctly(self):
        """Service with both price_min and price_max should show PKR range."""
        vendor = _make_vendor()
        services = [_make_service(name="Bridal Mehndi", price_min=5000, price_max=15000)]
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "PKR 5000-15000" in text

    def test_service_with_only_price_min_formatted_correctly(self):
        """Service with only price_min should show 'PKR X+' format."""
        vendor = _make_vendor()
        services = [_make_service(name="Custom Mehndi", price_min=3000, price_max=None)]
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "PKR 3000+" in text

    def test_service_with_only_price_max_formatted_correctly(self):
        """Service with only price_max should show 'up to PKR X' format."""
        vendor = _make_vendor()
        services = [_make_service(name="Budget Mehndi", price_min=None, price_max=8000)]
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "up to PKR 8000" in text

    def test_service_with_no_price_shows_name_only(self):
        """Service with no price info should appear with just its name."""
        vendor = _make_vendor()
        services = [_make_service(name="Consultation", price_min=None, price_max=None)]
        text = EmbeddingService.generate_vendor_text(vendor, services)
        assert "Consultation" in text
        assert "PKR" not in text

    def test_output_is_deterministic(self):
        """Same inputs must always produce the same output (required for SHA-256 staleness)."""
        vendor = _make_vendor(business_name="Stable Vendor", city="Islamabad")
        services = [_make_service(name="Photography")]
        text1 = EmbeddingService.generate_vendor_text(vendor, services)
        text2 = EmbeddingService.generate_vendor_text(vendor, services)
        assert text1 == text2


# ── 12.2  Property-based test (Hypothesis) ────────────────────────────────────

class TestGenerateVendorTextProperties:
    """
    Property-based tests for EmbeddingService.generate_vendor_text.

    **Validates: Requirements 5.2**
    """

    @given(
        business_name=st.text(min_size=1, max_size=50),
        city=st.text(min_size=1, max_size=50),
    )
    @h_settings(max_examples=50)
    def test_business_name_always_in_output(self, business_name: str, city: str):
        """business_name must always appear in the generated text for any valid input."""
        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name=business_name,
            city=city,
            region="Punjab",
            contact_email=f"{uuid.uuid4().hex[:8]}@vendor.com",
            status=VendorStatus.ACTIVE,
        )
        text = EmbeddingService.generate_vendor_text(vendor, [])
        assert business_name.strip() in text

    @given(
        business_name=st.text(min_size=1, max_size=50),
        city=st.text(min_size=1, max_size=50),
    )
    @h_settings(max_examples=50)
    def test_city_always_in_output_when_non_empty(self, business_name: str, city: str):
        """city must always appear in the generated text when it is non-empty."""
        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name=business_name,
            city=city,
            region="Punjab",
            contact_email=f"{uuid.uuid4().hex[:8]}@vendor.com",
            status=VendorStatus.ACTIVE,
        )
        text = EmbeddingService.generate_vendor_text(vendor, [])
        # city is included in the Location segment when non-empty after strip
        if city.strip():
            assert city.strip() in text

    @given(
        business_name=st.text(min_size=1, max_size=50),
        city=st.text(min_size=1, max_size=50),
    )
    @h_settings(max_examples=50)
    def test_output_always_ends_with_period(self, business_name: str, city: str):
        """Output must always end with a period regardless of input."""
        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name=business_name,
            city=city,
            region="Punjab",
            contact_email=f"{uuid.uuid4().hex[:8]}@vendor.com",
            status=VendorStatus.ACTIVE,
        )
        text = EmbeddingService.generate_vendor_text(vendor, [])
        assert text.endswith(".")


# ── 12.3  upsert_vendor_embedding idempotency test ────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def embedding_engine():
    """
    Isolated in-memory SQLite engine for the embedding idempotency tests.

    Patches:
    - Vendor.status: PostgreSQL ENUM → String (SQLite has no native ENUM)
    - VendorEmbedding.embedding: pgvector Vector → JSON (SQLite has no vector type)
    """
    # Import all models so SQLModel registers their metadata
    from src.models.user import User, RefreshToken, PasswordResetToken  # noqa: F401
    from src.models.domain_event import DomainEvent  # noqa: F401
    from src.models.booking import Booking  # noqa: F401
    from src.models.notification import Notification  # noqa: F401
    from src.models.notification_preference import NotificationPreference  # noqa: F401
    from src.models.category import Category, VendorCategoryLink  # noqa: F401
    from src.models.approval import ApprovalRequest  # noqa: F401
    from src.models.inquiry import CustomerInquiry  # noqa: F401
    from src.models.event import Event, EventType  # noqa: F401

    engine = create_async_engine(EMBEDDING_TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        # Patch PostgreSQL ENUM → String for Vendor.status
        Vendor.__table__.c["status"].type = String(50)

        # Patch pgvector Vector → JSON for SQLite compatibility
        from sqlalchemy import JSON
        VendorEmbedding.__table__.c["embedding"].type = JSON()

        available_tables = {
            name: SQLModel.metadata.tables[name]
            for name in EMBEDDING_TABLES
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
async def embedding_db_session(embedding_engine) -> AsyncGenerator[AsyncSession, None]:
    """Transactional test session that rolls back after each test."""
    async_session = sessionmaker(
        embedding_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


class TestUpsertVendorEmbeddingIdempotency:
    """
    12.3 — upsert_vendor_embedding must call Gemini exactly once for unchanged content.

    The SHA-256 staleness check should skip the Gemini API on the second call
    when the vendor profile has not changed.
    """

    @pytest.mark.asyncio
    async def test_gemini_called_exactly_once_for_unchanged_vendor(
        self, embedding_db_session: AsyncSession
    ):
        """
        Calling upsert_vendor_embedding twice with the same vendor data must
        result in exactly one Gemini API call (second call is skipped by the
        SHA-256 staleness check).
        """
        from src.config.database import get_settings

        settings = get_settings()
        gemini_url = f"{settings.gemini_base_url}embeddings"

        # Create and persist a test vendor with a service
        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name="Idempotency Test Vendor",
            city="Islamabad",
            region="ICT",
            description="A vendor for idempotency testing.",
            contact_email=f"{uuid.uuid4().hex[:8]}@idempotency.com",
            status=VendorStatus.ACTIVE,
        )
        embedding_db_session.add(vendor)
        await embedding_db_session.commit()
        await embedding_db_session.refresh(vendor)

        service = Service(
            id=uuid.uuid4(),
            vendor_id=vendor.id,
            name="Photography",
            price_min=10000.0,
            price_max=50000.0,
            is_active=True,
        )
        embedding_db_session.add(service)
        await embedding_db_session.commit()

        # Compute the expected content hash
        canonical_text = EmbeddingService.generate_vendor_text(vendor, [service])
        expected_hash = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()

        fake_embedding = [0.1] * 768
        mock_response_body = {"data": [{"embedding": fake_embedding}]}

        with respx.mock(assert_all_called=False) as mock_router:
            gemini_route = mock_router.post(gemini_url).mock(
                return_value=httpx.Response(200, json=mock_response_body)
            )

            service_instance = EmbeddingService()

            async with httpx.AsyncClient() as http_client:
                # First call — should hit Gemini and create the embedding row
                result1 = await service_instance.upsert_vendor_embedding(
                    embedding_db_session, vendor.id, http_client
                )

                # Second call — content unchanged, should skip Gemini
                result2 = await service_instance.upsert_vendor_embedding(
                    embedding_db_session, vendor.id, http_client
                )

        # Gemini must have been called exactly once
        assert gemini_route.call_count == 1, (
            f"Expected Gemini to be called exactly once, but it was called "
            f"{gemini_route.call_count} time(s)."
        )

        # Both calls must return a VendorEmbedding with the correct hash
        assert result1.content_hash == expected_hash
        assert result2.content_hash == expected_hash

        # Both results refer to the same vendor
        assert result1.vendor_id == vendor.id
        assert result2.vendor_id == vendor.id

    @pytest.mark.asyncio
    async def test_gemini_called_again_when_vendor_content_changes(
        self, embedding_db_session: AsyncSession
    ):
        """
        When the vendor profile changes between calls, Gemini must be called
        a second time to produce a fresh embedding.
        """
        from src.config.database import get_settings

        settings = get_settings()
        gemini_url = f"{settings.gemini_base_url}embeddings"

        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name="Changing Vendor",
            city="Lahore",
            region="Punjab",
            description="Original description.",
            contact_email=f"{uuid.uuid4().hex[:8]}@changing.com",
            status=VendorStatus.ACTIVE,
        )
        embedding_db_session.add(vendor)
        await embedding_db_session.commit()
        await embedding_db_session.refresh(vendor)

        fake_embedding = [0.2] * 768
        mock_response_body = {"data": [{"embedding": fake_embedding}]}

        with respx.mock(assert_all_called=False) as mock_router:
            gemini_route = mock_router.post(gemini_url).mock(
                return_value=httpx.Response(200, json=mock_response_body)
            )

            service_instance = EmbeddingService()

            async with httpx.AsyncClient() as http_client:
                # First call — creates the embedding
                await service_instance.upsert_vendor_embedding(
                    embedding_db_session, vendor.id, http_client
                )

                # Mutate the vendor's description to invalidate the hash
                vendor.description = "Updated description after change."
                embedding_db_session.add(vendor)
                await embedding_db_session.commit()
                await embedding_db_session.refresh(vendor)

                # Second call — content changed, must call Gemini again
                await service_instance.upsert_vendor_embedding(
                    embedding_db_session, vendor.id, http_client
                )

        # Gemini must have been called twice (once per unique content hash)
        assert gemini_route.call_count == 2, (
            f"Expected Gemini to be called twice for changed content, but it was "
            f"called {gemini_route.call_count} time(s)."
        )

    @pytest.mark.asyncio
    async def test_upsert_raises_for_nonexistent_vendor(
        self, embedding_db_session: AsyncSession
    ):
        """upsert_vendor_embedding must raise ValueError for an unknown vendor_id."""
        service_instance = EmbeddingService()
        nonexistent_id = uuid.uuid4()

        async with httpx.AsyncClient() as http_client:
            with pytest.raises(ValueError, match=str(nonexistent_id)):
                await service_instance.upsert_vendor_embedding(
                    embedding_db_session, nonexistent_id, http_client
                )
