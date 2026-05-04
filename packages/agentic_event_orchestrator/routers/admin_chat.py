"""Admin chat router — session and message log viewer."""
import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from config.dependencies import get_session
from models.chat_session import ChatSession, SessionStatus
from models.message import Message
from models.message_feedback import MessageFeedback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin/chat", tags=["admin-chat"])

AI_SERVICE_API_KEY = None  # loaded from app.state.settings


def _require_admin(request: Request):
    """Simple admin check via X-API-Key header."""
    settings = request.app.state.settings
    api_key = request.headers.get("X-API-Key", "")
    if settings.ai_service_api_key and api_key != settings.ai_service_api_key:
        raise HTTPException(status_code=403, detail="AUTH_FORBIDDEN")


def _hash_user_id(user_id) -> str:
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:12]


@router.get("/sessions")
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_session),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    _=Depends(_require_admin),
):
    query = select(ChatSession).order_by(ChatSession.started_at.desc()).limit(limit).offset(offset)
    if status:
        try:
            query = query.where(ChatSession.status == SessionStatus(status))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status}")

    result = await db.execute(query)
    sessions = result.scalars().all()

    # Get message counts
    data = []
    for s in sessions:
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.session_id == s.id)
        )
        msg_count = count_result.scalar_one_or_none() or 0
        data.append({
            "session_id": str(s.id),
            "user_id_hash": _hash_user_id(s.user_id),
            "started_at": s.started_at.isoformat(),
            "last_activity_at": s.last_activity_at.isoformat(),
            "status": s.status,
            "active_agent": s.active_agent,
            "message_count": msg_count,
        })

    return JSONResponse(content={"success": True, "data": data, "meta": {"total": len(data), "offset": offset}})


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    _=Depends(_require_admin),
):
    import uuid
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session_id")

    result = await db.execute(
        select(Message).where(Message.session_id == sid).order_by(Message.sequence.asc())
    )
    messages = result.scalars().all()

    data = [{
        "message_id": str(m.id),
        "sequence": m.sequence,
        "role": m.role,
        "content": m.content,
        "agent_name": m.agent_name,
        "created_at": m.created_at.isoformat(),
        "latency_ms": m.latency_ms,
    } for m in messages]

    return JSONResponse(content={"success": True, "data": data})


@router.get("/feedback/stats")
async def feedback_stats(
    request: Request,
    db: AsyncSession = Depends(get_session),
    _=Depends(_require_admin),
):
    # Aggregate feedback by rating
    up_count = await db.execute(
        select(func.count(MessageFeedback.id)).where(MessageFeedback.rating == "up")
    )
    down_count = await db.execute(
        select(func.count(MessageFeedback.id)).where(MessageFeedback.rating == "down")
    )

    return JSONResponse(content={
        "success": True,
        "data": {
            "thumbs_up": up_count.scalar_one_or_none() or 0,
            "thumbs_down": down_count.scalar_one_or_none() or 0,
        }
    })


@router.get("/faithfulness")
async def get_faithfulness_metrics(
    request: Request,
    db: AsyncSession = Depends(get_session),
    session_id: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    _=Depends(_require_admin),
):
    """
    Get RAG faithfulness evaluation metrics.
    
    Returns recent RAG Triad evaluations:
    - Context Relevance
    - Groundedness (hallucination risk indicator)
    - Answer Relevance
    
    If session_id provided, filter to that session.
    """
    from services.trulens_evaluator import trulens_evaluator
    import uuid
    
    # For now, return summary stats and recent evaluations
    # In production, these would be stored in a dedicated evaluation table
    
    # Get recent messages with agent responses for evaluation
    query = select(Message).where(
        Message.role == "assistant",
        Message.agent_name == "VendorDiscoveryAgent"
    ).order_by(Message.created_at.desc()).limit(limit)
    
    if session_id:
        try:
            sid = uuid.UUID(session_id)
            query = query.where(Message.session_id == sid)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid session_id")
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    evaluations = []
    hallucination_count = 0
    
    for msg in messages:
        # Get the preceding user message for context
        user_msg_result = await db.execute(
            select(Message).where(
                Message.session_id == msg.session_id,
                Message.role == "user",
                Message.sequence < msg.sequence
            ).order_by(Message.sequence.desc()).limit(1)
        )
        user_msg = user_msg_result.scalar_one_or_none()
        
        if user_msg:
            # Run evaluation (async)
            eval_result = await trulens_evaluator.evaluate(
                question=user_msg.content,
                answer=msg.content,
                context=[],  # Would need to retrieve from RAG context store
                session_id=str(msg.session_id),
            )
            
            if eval_result.hallucination_risk:
                hallucination_count += 1
            
            evaluations.append({
                "message_id": str(msg.id),
                "session_id": str(msg.session_id),
                "context_relevance": eval_result.context_relevance,
                "groundedness": eval_result.groundedness,
                "answer_relevance": eval_result.answer_relevance,
                "hallucination_risk": eval_result.hallucination_risk,
                "timestamp": eval_result.timestamp,
            })
    
    # Calculate aggregate metrics
    if evaluations:
        avg_groundedness = sum(e["groundedness"] for e in evaluations) / len(evaluations)
        avg_context_relevance = sum(e["context_relevance"] for e in evaluations) / len(evaluations)
        avg_answer_relevance = sum(e["answer_relevance"] for e in evaluations) / len(evaluations)
    else:
        avg_groundedness = avg_context_relevance = avg_answer_relevance = 0.0
    
    return JSONResponse(content={
        "success": True,
        "data": {
            "summary": {
                "total_evaluations": len(evaluations),
                "hallucination_risks": hallucination_count,
                "avg_groundedness": round(avg_groundedness, 3),
                "avg_context_relevance": round(avg_context_relevance, 3),
                "avg_answer_relevance": round(avg_answer_relevance, 3),
                "groundedness_threshold": trulens_evaluator._groundedness_threshold,
            },
            "evaluations": evaluations[:10],  # Return top 10
        }
    })
