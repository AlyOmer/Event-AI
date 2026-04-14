"""
Vendor search service using PostgreSQL trigram similarity and ILIKE.
"""
import uuid
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload

from ..models.vendor import Vendor, VendorStatus
from ..models.service import Service
from ..models.category import VendorCategoryLink
from ..schemas.vendor import VendorSearchQuery
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


search_service = SearchService()
