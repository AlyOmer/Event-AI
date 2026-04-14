import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.schemas.vendor import VendorRead, VendorSearchQuery
from src.services.search_service import search_service
from src.services.vendor_service import vendor_service

router = APIRouter(tags=["Public Vendors"])

@router.get("/", response_model=Dict[str, Any])
async def search_public_vendors(
    q: str = None,
    category_ids: List[uuid.UUID] = Query(None),
    city: str = None,
    region: str = None,
    min_rating: float = None,
    max_price: float = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    session: AsyncSession = Depends(get_session)
):
    """
    Public vendor search with full-text + trigram similarity ranking.
    Supports filtering by category, location, rating, and price range.
    """
    # Validate query length
    if q and len(q) > 200:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": "Search query too long (max 200 characters)"},
        )
    
    query = VendorSearchQuery(
        q=q,
        category_ids=category_ids,
        city=city,
        region=region,
        min_rating=min_rating,
        max_price=max_price,
        limit=limit,
        offset=offset
    )
    items, total = await search_service.search_vendors(session, query)
    return {
        "success": True,
        "data": items,
        "meta": {
            "total": total,
            "offset": offset,
            "limit": limit,
            "query": q
        }
    }


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, max_length=50),
    limit: int = Query(5, le=10),
    session: AsyncSession = Depends(get_session)
):
    """Autocomplete suggestions for vendor names."""
    suggestions = await search_service.suggest_vendors(session, q, limit)
    return {
        "success": True,
        "data": suggestions
    }

@router.get("/{id}", response_model=VendorRead)
async def get_public_vendor(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get public vendor profile by ID."""
    vendor = await vendor_service.get_by_id(session, id)
    if not vendor:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND_VENDOR_PROFILE", "message": "Vendor not found"},
        )

    from src.models.vendor import VendorStatus
    if vendor.status != VendorStatus.ACTIVE:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND_VENDOR_PROFILE", "message": "Vendor is not currently active"},
        )
        
    return vendor
