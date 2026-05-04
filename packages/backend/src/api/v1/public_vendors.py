import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.schemas.vendor import VendorRead, VendorSearchQuery
from src.schemas.search import VendorWithScore
from src.services.search_service import search_service
from src.services.vendor_service import vendor_service
from src.services.embedding_service import EmbeddingAPIError
from src.middleware.rate_limit import rate_limit_dependency

router = APIRouter(tags=["Public Vendors"])

# ── Rate limiters ─────────────────────────────────────────────────────────────
_semantic_limiter = rate_limit_dependency(max_attempts=60, window_seconds=60)
_search_limiter = rate_limit_dependency(max_attempts=60, window_seconds=60)

_VALID_MODES = {"keyword", "semantic", "hybrid"}


def _err(code: str, message: str) -> dict:
    """Build a standard error detail dict."""
    return {"code": code, "message": message}


# ── Semantic search endpoint (must be before /{id} to avoid path conflicts) ───

@router.get("/semantic", response_model=Dict[str, Any])
async def semantic_search_vendors(
    request: Request,
    q: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    city: Optional[str] = Query(None),
    category_ids: Optional[List[uuid.UUID]] = Query(None),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_semantic_limiter),
):
    """
    Semantic (vector) search for active vendors using natural-language queries.

    Embeds the query via Gemini text-embedding-004 and retrieves vendors ranked
    by cosine similarity from pgvector.

    Rate limit: 60 requests/minute per IP.
    """
    # 9.2 — validate q is present and non-empty
    if not q or not q.strip():
        raise HTTPException(
            status_code=422,
            detail=_err(
                "VALIDATION_QUERY_REQUIRED",
                "Query parameter 'q' is required and must not be empty.",
            ),
        )

    # 9.3 — get shared http_client from app.state
    http_client = request.app.state.http_client

    try:
        results = await search_service.semantic_search(
            session=session,
            query_text=q.strip(),
            limit=limit,
            city=city,
            category_ids=category_ids,
            http_client=http_client,
        )
    except EmbeddingAPIError:
        raise HTTPException(
            status_code=503,
            detail=_err(
                "AI_EMBEDDING_UNAVAILABLE",
                "The embedding service is currently unavailable. Please try again later.",
            ),
        )

    # 9.4 — return standard response envelope
    return {
        "success": True,
        "data": [item.model_dump() for item in results],
        "meta": {
            "total": len(results),
            "query": q.strip(),
        },
    }


@router.get("/search", response_model=Dict[str, Any])
async def hybrid_search_vendors(
    request: Request,
    q: Optional[str] = Query(None),
    mode: str = Query("hybrid"),
    limit: int = Query(10, ge=1, le=50),
    city: Optional[str] = Query(None),
    category_ids: Optional[List[uuid.UUID]] = Query(None),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_search_limiter),
):
    """
    Unified vendor search supporting keyword, semantic, and hybrid modes.

    - ``mode=keyword``  — trigram + ILIKE text search (no embedding required)
    - ``mode=semantic`` — pgvector cosine similarity via Gemini embeddings
    - ``mode=hybrid``   — weighted combination of trigram and semantic scores (default)

    Rate limit: 60 requests/minute per IP.
    """
    # 10.1 — validate q is present and non-empty
    if not q or not q.strip():
        raise HTTPException(
            status_code=422,
            detail=_err(
                "VALIDATION_QUERY_REQUIRED",
                "Query parameter 'q' is required and must not be empty.",
            ),
        )

    # 10.1 — validate mode
    if mode not in _VALID_MODES:
        raise HTTPException(
            status_code=422,
            detail=_err(
                "VALIDATION_INVALID_MODE",
                f"Invalid mode '{mode}'. Must be one of: keyword, semantic, hybrid.",
            ),
        )

    query_text = q.strip()
    http_client = request.app.state.http_client

    # 10.2 — delegate to the appropriate service method
    try:
        if mode == "keyword":
            vendors, total = await search_service.search_vendors(
                session,
                VendorSearchQuery(
                    q=query_text,
                    city=city,
                    category_ids=category_ids,
                    limit=limit,
                    offset=0,
                ),
            )
            results: List[VendorWithScore] = [
                VendorWithScore(
                    vendor=VendorRead.model_validate(v),
                    similarity_score=0.0,
                    search_mode="keyword",
                )
                for v in vendors
            ]

        elif mode == "semantic":
            results = await search_service.semantic_search(
                session=session,
                query_text=query_text,
                limit=limit,
                city=city,
                category_ids=category_ids,
                http_client=http_client,
            )
            total = len(results)

        else:  # hybrid
            results = await search_service.hybrid_search(
                session=session,
                query=query_text,
                limit=limit,
                http_client=http_client,
                city=city,
                category_ids=category_ids,
            )
            total = len(results)

    except EmbeddingAPIError:
        raise HTTPException(
            status_code=503,
            detail=_err(
                "AI_EMBEDDING_UNAVAILABLE",
                "The embedding service is currently unavailable. Please try again later.",
            ),
        )

    # 10.3 — consistent response envelope for all modes
    return {
        "success": True,
        "data": [item.model_dump() for item in results],
        "meta": {
            "total": total,
            "query": query_text,
            "mode": mode,
        },
    }


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
