"""Feedback router — POST /api/v1/ai/feedback."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.dependencies import get_session, get_settings_dep
from models.message import Message
from models.message_feedback import MessageFeedback, FeedbackRating
from models.chat_session import ChatSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str  # "up" or "down"
    comment: Optional[str] = None
    user_id: Optional[str] = None


def _get_user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        import hashlib
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            user_id = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
    return user_id or "anonymous"


@router.post("/feedback")
async def submit_feedback(
    body: FeedbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user_id = body.user_id or _get_user_id(request)

    # Validate rating
    if body.rating not in ("up", "down"):
        raise HTTPException(status_code=422, detail="rating must be 'up' or 'down'")

    # Validate message_id format
    try:
        msg_uuid = uuid.UUID(body.message_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid message_id format")

    # Verify message exists
    result = await db.execute(select(Message).where(Message.id == msg_uuid))
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Store feedback
    try:
        feedback = MessageFeedback(
            message_id=msg_uuid,
            user_id=uuid.UUID(user_id) if len(user_id) == 36 else uuid.uuid5(uuid.NAMESPACE_DNS, user_id),
            rating=FeedbackRating(body.rating),
            comment=body.comment[:1000] if body.comment else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(feedback)
        await db.commit()
    except Exception as e:
        logger.error("Failed to save feedback: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save feedback")

    return JSONResponse(content={"success": True, "data": {"feedback_id": str(feedback.id)}})
