"""Memory router — DELETE /api/v1/ai/memory/{user_id}."""
import logging

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from services.memory_service import MemoryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["memory"])


def _get_user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        import hashlib
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            user_id = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
    return user_id or "anonymous"


@router.delete("/memory/{user_id}")
async def delete_memory(user_id: str, request: Request):
    """Delete all Mem0 memory for a user (right-to-forget)."""
    requesting_user = _get_user_id(request)

    # Users can only delete their own memory
    if requesting_user != user_id and requesting_user != "anonymous":
        raise HTTPException(status_code=403, detail="Cannot delete another user's memory")

    settings = request.app.state.settings
    memory_svc = MemoryService(api_key=settings.mem0_api_key)
    await memory_svc.delete_user_memory(user_id)

    return JSONResponse(content={"success": True, "data": {"deleted": True, "user_id": user_id}})
