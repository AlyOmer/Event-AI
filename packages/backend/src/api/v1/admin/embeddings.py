"""
Admin Embeddings API

POST /backfill — trigger a background embedding backfill for one or all active vendors.

Mounted at /api/v1/admin/embeddings in main.py.

Sub-tasks implemented:
  11.1  Route definition
  11.2  JWT admin authentication via Depends(require_admin) → HTTP 403 for non-admin
  11.3  No vendor_id → query all active vendor IDs, enqueue embed_batch as BackgroundTask
  11.4  vendor_id provided → enqueue upsert_vendor_embedding for that single vendor
  11.5  Return {"success": true, "data": {"queued": N}} immediately
  11.6  10/min rate limit
"""
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_admin
from src.config.database import async_session_maker, get_session
from src.middleware.rate_limit import rate_limit_dependency
from src.models.user import User
from src.models.vendor import Vendor, VendorStatus
from src.services.embedding_service import embedding_service

logger = structlog.get_logger()

router = APIRouter(tags=["Admin Embeddings"])

# ── Rate limiter: 10 requests / minute ───────────────────────────────────────
_backfill_limiter = rate_limit_dependency(max_attempts=10, window_seconds=60)


# ── Request schema ────────────────────────────────────────────────────────────

class BackfillRequest(BaseModel):
    """Optional request body for the backfill endpoint."""

    vendor_id: Optional[uuid.UUID] = None


# ── Error helper ──────────────────────────────────────────────────────────────

def _err(code: str, message: str) -> dict:
    """Build a standard error detail dict."""
    return {"code": code, "message": message}


# ── Background task wrappers ──────────────────────────────────────────────────

async def _run_single_vendor_embedding(
    vendor_id: uuid.UUID,
    http_client,
) -> None:
    """Background task: embed a single vendor using its own DB session."""
    async with async_session_maker() as session:
        try:
            await embedding_service.upsert_vendor_embedding(session, vendor_id, http_client)
            logger.info("admin.backfill.single.done", vendor_id=str(vendor_id))
        except Exception as exc:
            logger.error(
                "admin.backfill.single.failed",
                vendor_id=str(vendor_id),
                error=str(exc),
                error_type=type(exc).__name__,
            )


async def _run_batch_embedding(
    vendor_ids: list[uuid.UUID],
    http_client,
) -> None:
    """Background task: embed a batch of vendors using its own DB session."""
    async with async_session_maker() as session:
        try:
            count = await embedding_service.embed_batch(session, vendor_ids, http_client)
            logger.info(
                "admin.backfill.batch.done",
                total=len(vendor_ids),
                succeeded=count,
            )
        except Exception as exc:
            logger.error(
                "admin.backfill.batch.failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/backfill", response_model=None)
async def backfill_embeddings(
    request: Request,
    background_tasks: BackgroundTasks,
    body: Optional[BackfillRequest] = None,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_backfill_limiter),
):
    """
    Admin-only: Trigger a background embedding backfill.

    - If ``vendor_id`` is provided in the request body, enqueues a single-vendor
      embedding update and returns ``{"queued": 1}``.
    - If no ``vendor_id`` is provided (or body is omitted), queries all ACTIVE
      vendor IDs and enqueues a batch embedding run, returning ``{"queued": N}``.

    The response is returned immediately; embedding work happens in the background.

    Rate limit: 10 requests/minute per IP.
    """
    http_client = request.app.state.http_client
    vendor_id = body.vendor_id if body else None

    if vendor_id is not None:
        # 11.4 — single vendor backfill
        background_tasks.add_task(
            _run_single_vendor_embedding,
            vendor_id,
            http_client,
        )
        queued = 1
        logger.info(
            "admin.backfill.enqueued_single",
            admin_id=str(current_user.id),
            vendor_id=str(vendor_id),
        )
    else:
        # 11.3 — batch backfill: query all active vendor IDs first
        stmt = select(Vendor.id).where(Vendor.status == VendorStatus.ACTIVE)
        result = await session.execute(stmt)
        vendor_ids: list[uuid.UUID] = list(result.scalars().all())
        queued = len(vendor_ids)

        background_tasks.add_task(
            _run_batch_embedding,
            vendor_ids,
            http_client,
        )
        logger.info(
            "admin.backfill.enqueued_batch",
            admin_id=str(current_user.id),
            queued=queued,
        )

    # 11.5 — return immediately
    return {
        "success": True,
        "data": {"queued": queued},
    }
