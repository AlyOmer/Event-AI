"""
Vendor search service using PostgreSQL trigram similarity and ILIKE,
extended with pgvector-based semantic search.
"""
import uuid
from typing import List, Tuple, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload

import httpx

from ..models.vendor import Vendor, VendorStatus
from ..models.vendor_embedding import VendorEmbedding
from ..models.service import Service
from ..models.category import VendorCategoryLink
from ..schemas.vendor import VendorSearchQuery, VendorRead
from ..schemas.search import VendorWithScore
from ..config.database import get_settings
import structlog

logger = structlog.get_logger()


class SearchService:

    @classmethod
    async def search_vendors(
        cls,
        session: AsyncSession,
        query: VendorSearchQuery,
    ) -> Tuple[List[Vendor], int]:
        """
        Search active vendors with trigram + ILIKE text search and filters.
        Returns (vendors, total_count) where total_count ignores pagination.
        """
        # Build filter list — same filters applied to both data and count queries
        filters = [Vendor.status == VendorStatus.ACTIVE]

        # Text search: trigram OR ILIKE (combined with OR so either match qualifies)
        if query.q:
            term = query.q.strip()
            if term:
                ilike = f"%{term}%"
                text_filter = or_(
                    Vendor.business_name.ilike(ilike),
                    func.coalesce(Vendor.description, "").ilike(ilike),
                    func.similarity(Vendor.business_name, term) > 0.1,
                    func.similarity(func.coalesce(Vendor.description, ""), term) > 0.1,
                )
                filters.append(text_filter)

        # Category filter via subquery
        if query.category_ids:
            cat_subq = (
                select(VendorCategoryLink.vendor_id)
                .where(VendorCategoryLink.category_id.in_(query.category_ids))
                .scalar_subquery()
            )
            filters.append(Vendor.id.in_(cat_subq))

        # Location filters
        if query.city:
            filters.append(Vendor.city.ilike(f"%{query.city}%"))
        if query.region:
            filters.append(Vendor.region.ilike(f"%{query.region}%"))

        # Rating filter
        if query.min_rating is not None:
            filters.append(Vendor.rating >= query.min_rating)

        # Price filter: vendor must have at least one service with price_min <= max_price
        if query.max_price is not None:
            price_subq = (
                select(Service.vendor_id)
                .where(Service.price_min <= query.max_price)
                .scalar_subquery()
            )
            filters.append(Vendor.id.in_(price_subq))

        combined = and_(*filters)

        # Count query (no pagination, no ordering)
        count_stmt = select(func.count()).select_from(Vendor).where(combined)
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Data query with ordering and pagination
        data_stmt = (
            select(Vendor)
            .where(combined)
            .options(selectinload(Vendor.categories))
        )

        if query.q:
            term = query.q.strip()
            rank = (
                func.greatest(
                    func.similarity(Vendor.business_name, term),
                    func.similarity(func.coalesce(Vendor.description, ""), term),
                ) * 0.7
                + (Vendor.rating / 5.0) * 0.3
            )
            data_stmt = data_stmt.order_by(desc(rank))
        else:
            data_stmt = data_stmt.order_by(desc(Vendor.rating), Vendor.business_name)

        data_stmt = data_stmt.offset(query.offset).limit(query.limit)

        result = await session.execute(data_stmt)
        vendors = list(result.scalars().all())

        logger.info(
            "search.vendors",
            query=query.q,
            city=query.city,
            results=len(vendors),
            total=total,
        )
        return vendors, total

    @classmethod
    async def suggest_vendors(
        cls,
        session: AsyncSession,
        query_text: str,
        limit: int = 5,
    ) -> List[dict]:
        """Autocomplete suggestions for vendor search."""
        if not query_text or len(query_text) < 2:
            return []

        ilike = f"%{query_text}%"
        stmt = (
            select(
                Vendor.id,
                Vendor.business_name,
                Vendor.city,
                func.similarity(Vendor.business_name, query_text).label("similarity"),
            )
            .where(
                and_(
                    Vendor.status == VendorStatus.ACTIVE,
                    or_(
                        Vendor.business_name.ilike(ilike),
                        func.similarity(Vendor.business_name, query_text) > 0.2,
                    ),
                )
            )
            .order_by(desc("similarity"))
            .limit(limit)
        )

        result = await session.execute(stmt)
        return [
            {"id": str(row.id), "name": row.business_name, "city": row.city, "score": float(row.similarity)}
            for row in result
        ]


    # ------------------------------------------------------------------
    # 7.1 / 7.2 / 7.3  Semantic search via pgvector cosine distance
    # ------------------------------------------------------------------

    @classmethod
    async def semantic_search(
        cls,
        session: AsyncSession,
        query_text: str,
        limit: int = 10,
        city: Optional[str] = None,
        category_ids: Optional[List[uuid.UUID]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> List[VendorWithScore]:
        """Return vendors ranked by cosine similarity to the query embedding.

        Steps:
        1. Embed ``query_text`` via EmbeddingService.
        2. Join Vendor → VendorEmbedding and compute cosine distance.
        3. Convert distance to similarity (1 - distance).
        4. Apply ACTIVE status, optional city ILIKE, and optional category_ids
           filters.
        5. Order by distance ASC (most similar first) and limit results.

        Args:
            session: Async SQLAlchemy session.
            query_text: Natural-language search query.
            limit: Maximum number of results to return (default 10).
            city: Optional city filter (case-insensitive substring match).
            category_ids: Optional list of category UUIDs to filter by.
            http_client: Shared httpx.AsyncClient for the Gemini API call.

        Returns:
            List of VendorWithScore ordered by descending similarity.

        Raises:
            EmbeddingAPIError: Propagated from embed_text when Gemini fails.
        """
        # Import here to avoid circular imports at module load time
        from .embedding_service import embedding_service

        # Step 1 — get the query vector from Gemini
        query_vector: List[float] = await embedding_service.embed_text(
            query_text, http_client
        )

        # Step 2 — build the cosine-distance expression using pgvector's <=> operator
        # VendorEmbedding.embedding is a Vector(768) column; the <=> operator
        # returns the cosine distance in [0, 2] (pgvector convention: 0 = identical).
        distance_expr = VendorEmbedding.embedding.op("<=>")(query_vector).label(
            "distance"
        )

        # Build filter list
        filters = [Vendor.status == VendorStatus.ACTIVE]

        # Optional city filter (case-insensitive substring)
        if city:
            filters.append(Vendor.city.ilike(f"%{city}%"))

        # Optional category filter via subquery on the link table
        if category_ids:
            cat_subq = (
                select(VendorCategoryLink.vendor_id)
                .where(VendorCategoryLink.category_id.in_(category_ids))
                .scalar_subquery()
            )
            filters.append(Vendor.id.in_(cat_subq))

        # Step 3 — main query: join Vendor ↔ VendorEmbedding, compute distance,
        # apply filters, order by distance ASC, limit results.
        stmt = (
            select(Vendor, distance_expr)
            .join(VendorEmbedding, VendorEmbedding.vendor_id == Vendor.id)
            .where(and_(*filters))
            .options(selectinload(Vendor.categories))
            .order_by("distance")
            .limit(limit)
        )

        result = await session.execute(stmt)
        rows = result.all()

        # Step 4 — convert distance to similarity and build response objects
        vendor_with_scores: List[VendorWithScore] = []
        for vendor, distance in rows:
            # Cosine distance ∈ [0, 2]; similarity = 1 - distance keeps it in [-1, 1].
            # In practice pgvector normalises vectors so distance ∈ [0, 1] for unit
            # vectors, giving similarity ∈ [0, 1].
            similarity = 1.0 - float(distance)
            vendor_with_scores.append(
                VendorWithScore(
                    vendor=VendorRead.model_validate(vendor),
                    similarity_score=similarity,
                    search_mode="semantic",
                )
            )

        logger.info(
            "search.semantic",
            query=query_text,
            city=city,
            category_ids=[str(c) for c in category_ids] if category_ids else None,
            results=len(vendor_with_scores),
        )
        return vendor_with_scores


    # ------------------------------------------------------------------
    # 8.1 / 8.2 / 8.3 / 8.4  Hybrid search: trigram + semantic fusion
    # ------------------------------------------------------------------

    @classmethod
    async def hybrid_search(
        cls,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        http_client: Optional[httpx.AsyncClient] = None,
        city: Optional[str] = None,
        category_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[VendorWithScore]:
        """Return vendors ranked by a weighted combination of trigram and semantic scores.

        Algorithm:
        1. Run ``search_vendors`` (trigram/keyword) with ``limit * 2`` results.
        2. Run ``semantic_search`` with ``limit * 2`` results (if http_client available).
        3. Build a score map keyed by vendor_id with rank-normalised trigram scores
           and cosine-similarity semantic scores.
        4. Compute ``hybrid_score = w_t * trigram_score + w_s * semantic_score``
           for every vendor in the union; missing scores default to ``0.0``.
        5. Sort descending by hybrid_score, return top ``limit`` as VendorWithScore.

        Weights are read from ``settings.hybrid_trigram_weight`` and
        ``settings.hybrid_semantic_weight``.

        Falls back to keyword-only results when ``http_client`` is None or when
        the embedding API raises ``EmbeddingAPIError``.

        Args:
            session: Async SQLAlchemy session.
            query: Natural-language search query.
            limit: Maximum number of results to return (default 10).
            http_client: Shared httpx.AsyncClient for the Gemini API call.
            city: Optional city filter (case-insensitive substring match).
            category_ids: Optional list of category UUIDs to filter by.

        Returns:
            List of VendorWithScore ordered by descending hybrid score.
        """
        from .embedding_service import EmbeddingAPIError

        settings = get_settings()
        pool_size = limit * 2

        # ------------------------------------------------------------------ #
        # Step 1 — Trigram / keyword search                                   #
        # ------------------------------------------------------------------ #
        trigram_query = VendorSearchQuery(
            q=query,
            city=city,
            category_ids=category_ids,
            limit=pool_size,
            offset=0,
        )
        trigram_vendors, _ = await cls.search_vendors(session, trigram_query)

        # Rank-based normalisation: position 0 → 1.0, position N-1 → approaches 0.0
        # Formula: score = 1.0 - (rank / max(len(results), 1))
        n_trigram = len(trigram_vendors)
        trigram_scores: Dict[uuid.UUID, float] = {
            vendor.id: 1.0 - (rank / max(n_trigram, 1))
            for rank, vendor in enumerate(trigram_vendors)
        }

        # Keep a vendor object map so we can reconstruct VendorWithScore later
        vendor_objects: Dict[uuid.UUID, Vendor] = {v.id: v for v in trigram_vendors}

        # ------------------------------------------------------------------ #
        # Step 2 — Semantic search (optional; falls back on error / no client)#
        # ------------------------------------------------------------------ #
        semantic_scores: Dict[uuid.UUID, float] = {}
        semantic_vendor_reads: Dict[uuid.UUID, VendorRead] = {}

        if http_client is not None:
            try:
                semantic_results = await cls.semantic_search(
                    session=session,
                    query_text=query,
                    limit=pool_size,
                    city=city,
                    category_ids=category_ids,
                    http_client=http_client,
                )
                for item in semantic_results:
                    vid = item.vendor.id
                    semantic_scores[vid] = item.similarity_score
                    semantic_vendor_reads[vid] = item.vendor
            except EmbeddingAPIError as exc:
                logger.warning(
                    "hybrid_search.semantic_fallback",
                    reason="EmbeddingAPIError",
                    error=str(exc),
                )
                # Fall through — semantic_scores stays empty; keyword scores used alone

        # ------------------------------------------------------------------ #
        # Step 3 — Build union of all vendor IDs                              #
        # ------------------------------------------------------------------ #
        all_vendor_ids = set(trigram_scores.keys()) | set(semantic_scores.keys())

        # ------------------------------------------------------------------ #
        # Step 4 — Compute hybrid scores                                      #
        # ------------------------------------------------------------------ #
        w_t = settings.hybrid_trigram_weight
        w_s = settings.hybrid_semantic_weight

        scored: List[Tuple[uuid.UUID, float]] = []
        for vid in all_vendor_ids:
            t_score = trigram_scores.get(vid, 0.0)   # 8.3 — default missing to 0.0
            s_score = semantic_scores.get(vid, 0.0)  # 8.3 — default missing to 0.0
            hybrid_score = (t_score * w_t) + (s_score * w_s)  # 8.4 — weighted combo
            scored.append((vid, hybrid_score))

        # ------------------------------------------------------------------ #
        # Step 5 — Sort descending, take top `limit`                          #
        # ------------------------------------------------------------------ #
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:limit]

        # ------------------------------------------------------------------ #
        # Step 6 — Build response objects                                     #
        # ------------------------------------------------------------------ #
        results: List[VendorWithScore] = []
        for vid, hybrid_score in top:
            # Prefer the VendorRead from semantic results (already validated);
            # fall back to constructing one from the raw Vendor ORM object.
            if vid in semantic_vendor_reads:
                vendor_read = semantic_vendor_reads[vid]
            elif vid in vendor_objects:
                vendor_read = VendorRead.model_validate(vendor_objects[vid])
            else:
                # Should not happen, but guard defensively
                continue

            results.append(
                VendorWithScore(
                    vendor=vendor_read,
                    similarity_score=hybrid_score,
                    search_mode="hybrid",
                )
            )

        logger.info(
            "search.hybrid",
            query=query,
            city=city,
            category_ids=[str(c) for c in category_ids] if category_ids else None,
            trigram_results=n_trigram,
            semantic_results=len(semantic_scores),
            hybrid_results=len(results),
        )
        return results


search_service = SearchService()
