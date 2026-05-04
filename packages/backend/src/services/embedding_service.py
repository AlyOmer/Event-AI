"""
EmbeddingService — generates and stores vendor profile embeddings via Gemini.

Responsibilities:
- Build canonical text representations of vendor profiles
- Call the Gemini OpenAI-compatible embeddings endpoint
- Upsert VendorEmbedding rows with SHA-256 staleness detection
- Batch-embed multiple vendors with per-vendor error isolation
- Handle domain events for vendor approval/deactivation
"""
import hashlib
import uuid
from typing import Any, Dict, List, Optional

import httpx
import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.database import get_settings
from ..models.vendor import Vendor
from ..models.service import Service
from ..models.vendor_embedding import VendorEmbedding

logger = structlog.get_logger()


class EmbeddingAPIError(Exception):
    """Raised when the Gemini embeddings API returns a non-2xx response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Embedding API error {status_code}: {detail}")


class EmbeddingService:
    """Singleton service for vendor profile embedding operations."""

    # ------------------------------------------------------------------
    # 5.2  Pure text generation
    # ------------------------------------------------------------------

    @staticmethod
    def generate_vendor_text(vendor: Vendor, services: List[Service]) -> str:
        """Build a canonical text representation of a vendor for embedding.

        Pure function — no I/O, no async.  Returns a deterministic string for
        the same inputs so that SHA-256 staleness detection works correctly.

        Format:
            "Business: {name}. Location: {city}, {region}. Description: {desc}. Services: {s1 name} (PKR {min}-{max}), ..."
        """
        parts: List[str] = []

        # Business name (always present)
        business_name = (vendor.business_name or "").strip()
        parts.append(f"Business: {business_name}")

        # Location
        city = (vendor.city or "").strip()
        region = (vendor.region or "").strip()
        if city or region:
            location = ", ".join(filter(None, [city, region]))
            parts.append(f"Location: {location}")

        # Description (optional)
        if vendor.description:
            desc = vendor.description.strip()
            if desc:
                parts.append(f"Description: {desc}")

        # Services
        active_services = [s for s in services if s.is_active]
        if active_services:
            service_parts: List[str] = []
            for svc in active_services:
                name = (svc.name or "").strip()
                if not name:
                    continue
                if svc.price_min is not None and svc.price_max is not None:
                    service_parts.append(
                        f"{name} (PKR {int(svc.price_min)}-{int(svc.price_max)})"
                    )
                elif svc.price_min is not None:
                    service_parts.append(f"{name} (PKR {int(svc.price_min)}+)")
                elif svc.price_max is not None:
                    service_parts.append(f"{name} (up to PKR {int(svc.price_max)})")
                else:
                    service_parts.append(name)
            if service_parts:
                parts.append(f"Services: {', '.join(service_parts)}")

        return ". ".join(parts) + "."

    # ------------------------------------------------------------------
    # 5.3  Gemini embeddings API call
    # ------------------------------------------------------------------

    async def embed_text(
        self, text: str, http_client: httpx.AsyncClient
    ) -> List[float]:
        """Call the Gemini OpenAI-compatible embeddings endpoint.

        Args:
            text: The text to embed.
            http_client: Shared httpx.AsyncClient from app.state.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            EmbeddingAPIError: If the API returns a non-2xx status code.
        """
        settings = get_settings()
        url = f"{settings.gemini_base_url}embeddings"
        payload = {
            "model": settings.gemini_embedding_model,
            "input": text,
        }
        headers = {"Authorization": f"Bearer {settings.gemini_api_key}"}

        response = await http_client.post(url, json=payload, headers=headers)

        if response.status_code >= 300:
            raise EmbeddingAPIError(
                status_code=response.status_code,
                detail=response.text,
            )

        data = response.json()
        return data["data"][0]["embedding"]

    # ------------------------------------------------------------------
    # 5.4  Upsert with SHA-256 staleness detection
    # ------------------------------------------------------------------

    async def upsert_vendor_embedding(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        http_client: httpx.AsyncClient,
    ) -> VendorEmbedding:
        """Create or update the VendorEmbedding row for a vendor.

        Uses SHA-256 of the canonical vendor text to skip re-embedding when
        the profile has not changed since the last embedding run.

        Args:
            session: Async SQLAlchemy session.
            vendor_id: UUID of the vendor to embed.
            http_client: Shared httpx.AsyncClient from app.state.

        Returns:
            The (possibly unchanged) VendorEmbedding row.

        Raises:
            ValueError: If the vendor does not exist.
            EmbeddingAPIError: If the Gemini API call fails.
        """
        settings = get_settings()

        # Load vendor + services in one query (avoid N+1)
        stmt = (
            select(Vendor)
            .where(Vendor.id == vendor_id)
            .options(selectinload(Vendor.services))
        )
        result = await session.execute(stmt)
        vendor: Optional[Vendor] = result.scalar_one_or_none()

        if vendor is None:
            raise ValueError(f"Vendor {vendor_id} not found")

        # Build canonical text and compute its hash
        canonical_text = self.generate_vendor_text(vendor, vendor.services)
        content_hash = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()

        # Check for an existing embedding row
        existing_stmt = select(VendorEmbedding).where(
            VendorEmbedding.vendor_id == vendor_id
        )
        existing_result = await session.execute(existing_stmt)
        existing: Optional[VendorEmbedding] = existing_result.scalar_one_or_none()

        # Staleness check — skip Gemini call if content hasn't changed
        if existing is not None and existing.content_hash == content_hash:
            logger.info(
                "embedding.skipped_unchanged",
                vendor_id=str(vendor_id),
                content_hash=content_hash,
            )
            return existing

        # Call Gemini to get the embedding vector
        embedding_vector = await self.embed_text(canonical_text, http_client)

        if existing is not None:
            # Update existing row
            existing.embedding = embedding_vector
            existing.content_hash = content_hash
            existing.model_version = settings.gemini_embedding_model
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            logger.info(
                "embedding.updated",
                vendor_id=str(vendor_id),
                content_hash=content_hash,
            )
            return existing
        else:
            # Create new row
            new_embedding = VendorEmbedding(
                vendor_id=vendor_id,
                embedding=embedding_vector,
                content_hash=content_hash,
                model_version=settings.gemini_embedding_model,
            )
            session.add(new_embedding)
            await session.commit()
            await session.refresh(new_embedding)
            logger.info(
                "embedding.created",
                vendor_id=str(vendor_id),
                content_hash=content_hash,
            )
            return new_embedding

    # ------------------------------------------------------------------
    # 6.1  Domain event handler — vendor.approved
    # ------------------------------------------------------------------

    async def handle_vendor_approved(
        self,
        event_type: str,
        payload: Dict[str, Any],
        user_id: Optional[uuid.UUID],
        session: Optional[AsyncSession] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Event bus handler for vendor.approved.

        Calls upsert_vendor_embedding so the newly-approved vendor's profile
        is immediately indexed for semantic search.  Errors are logged but
        never re-raised — domain event handlers must not crash the event bus.
        """
        if session is None or http_client is None:
            logger.warning(
                "embedding.handle_vendor_approved.missing_deps",
                has_session=session is not None,
                has_http_client=http_client is not None,
            )
            return

        raw_vendor_id = payload.get("vendor_id")
        if not raw_vendor_id:
            logger.warning(
                "embedding.handle_vendor_approved.missing_vendor_id",
                payload_keys=list(payload.keys()),
            )
            return

        try:
            vendor_id = uuid.UUID(str(raw_vendor_id))
        except (ValueError, AttributeError):
            logger.warning(
                "embedding.handle_vendor_approved.invalid_vendor_id",
                raw=raw_vendor_id,
            )
            return

        try:
            await self.upsert_vendor_embedding(session, vendor_id, http_client)
            logger.info(
                "embedding.handle_vendor_approved.success",
                vendor_id=str(vendor_id),
            )
        except Exception as exc:
            logger.error(
                "embedding.handle_vendor_approved.failed",
                vendor_id=str(vendor_id),
                error=str(exc),
                error_type=type(exc).__name__,
            )

    # ------------------------------------------------------------------
    # 6.2  Domain event handler — vendor.rejected / vendor.suspended
    # ------------------------------------------------------------------

    async def handle_vendor_deactivated(
        self,
        event_type: str,
        payload: Dict[str, Any],
        user_id: Optional[uuid.UUID],
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Event bus handler for vendor.rejected and vendor.suspended.

        Deletes the VendorEmbedding row for the vendor so deactivated vendors
        are no longer returned by semantic search.  Errors are logged but
        never re-raised — domain event handlers must not crash the event bus.
        """
        if session is None:
            logger.warning("embedding.handle_vendor_deactivated.missing_session")
            return

        raw_vendor_id = payload.get("vendor_id")
        if not raw_vendor_id:
            logger.warning(
                "embedding.handle_vendor_deactivated.missing_vendor_id",
                payload_keys=list(payload.keys()),
            )
            return

        try:
            vendor_id = uuid.UUID(str(raw_vendor_id))
        except (ValueError, AttributeError):
            logger.warning(
                "embedding.handle_vendor_deactivated.invalid_vendor_id",
                raw=raw_vendor_id,
            )
            return

        try:
            stmt = delete(VendorEmbedding).where(VendorEmbedding.vendor_id == vendor_id)
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount > 0:
                logger.info(
                    "embedding.handle_vendor_deactivated.deleted",
                    vendor_id=str(vendor_id),
                    event_type=event_type,
                )
            else:
                logger.info(
                    "embedding.handle_vendor_deactivated.no_row",
                    vendor_id=str(vendor_id),
                    event_type=event_type,
                )
        except Exception as exc:
            logger.error(
                "embedding.handle_vendor_deactivated.failed",
                vendor_id=str(vendor_id),
                error=str(exc),
                error_type=type(exc).__name__,
            )

    # ------------------------------------------------------------------
    # 5.5  Batch embedding with per-vendor error isolation
    # ------------------------------------------------------------------

    async def embed_batch(
        self,
        session: AsyncSession,
        vendor_ids: List[uuid.UUID],
        http_client: httpx.AsyncClient,
    ) -> int:
        """Embed multiple vendors, logging errors per-vendor without aborting.

        Args:
            session: Async SQLAlchemy session.
            vendor_ids: List of vendor UUIDs to embed.
            http_client: Shared httpx.AsyncClient from app.state.

        Returns:
            Count of successfully embedded vendors.
        """
        success_count = 0

        for vendor_id in vendor_ids:
            try:
                await self.upsert_vendor_embedding(session, vendor_id, http_client)
                success_count += 1
            except Exception as exc:
                logger.error(
                    "embedding.batch_vendor_failed",
                    vendor_id=str(vendor_id),
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        logger.info(
            "embedding.batch_complete",
            total=len(vendor_ids),
            succeeded=success_count,
            failed=len(vendor_ids) - success_count,
        )
        return success_count


# Singleton instance — matches project convention
embedding_service = EmbeddingService()
