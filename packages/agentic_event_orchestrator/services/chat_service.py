import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_session import ChatSession, SessionStatus
from models.message import Message, MessageRole

logger = logging.getLogger(__name__)


class ChatService:
    async def get_or_create_session(
        self,
        session: AsyncSession,
        user_id: UUID,
        session_id: str | None,
    ) -> ChatSession:
        if session_id:
            try:
                sid = UUID(session_id)
                result = await session.execute(
                    select(ChatSession).where(ChatSession.id == sid)
                )
                existing = result.scalar_one_or_none()
                if (
                    existing
                    and existing.user_id == user_id
                    and existing.status == SessionStatus.active
                ):
                    existing.last_activity_at = datetime.now(timezone.utc)
                    await session.commit()
                    logger.debug("Reusing session %s for user %s", sid, user_id)
                    return existing
            except (ValueError, AttributeError) as exc:
                logger.warning("Invalid session_id %r: %s — creating new session", session_id, exc)

        new_session = ChatSession(user_id=user_id)
        session.add(new_session)
        await session.commit()
        logger.debug("Created new session %s for user %s", new_session.id, user_id)
        return new_session

    async def save_turn(
        self,
        session: AsyncSession,
        chat_session: ChatSession,
        user_content: str,
        assistant_content: str,
        agent_name: str,
        latency_ms: int,
    ) -> tuple[Message, Message]:
        result = await session.execute(
            select(func.max(Message.sequence)).where(
                Message.session_id == chat_session.id
            )
        )
        max_seq: int = result.scalar_one_or_none() or 0

        now = datetime.now(timezone.utc)
        user_msg = Message(
            session_id=chat_session.id,
            sequence=max_seq + 1,
            role=MessageRole.user,
            content=user_content,
            created_at=now,
        )
        asst_msg = Message(
            session_id=chat_session.id,
            sequence=max_seq + 2,
            role=MessageRole.assistant,
            content=assistant_content,
            agent_name=agent_name,
            latency_ms=latency_ms,
            created_at=now,
        )
        session.add_all([user_msg, asst_msg])
        await session.commit()
        logger.debug(
            "Saved turn (seq %d/%d) for session %s",
            max_seq + 1,
            max_seq + 2,
            chat_session.id,
        )
        return user_msg, asst_msg

    async def expire_old_sessions(
        self,
        session: AsyncSession,
        ttl_days: int,
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.status == SessionStatus.active,
                ChatSession.last_activity_at < cutoff,
            )
        )
        stale = result.scalars().all()
        for s in stale:
            s.status = SessionStatus.expired
        await session.commit()
        count = len(stale)
        logger.info("Expired %d sessions older than %d days", count, ttl_days)
        return count

    async def get_session_messages(
        self,
        session: AsyncSession,
        session_id: UUID,
        limit: int = 50,
    ) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.sequence.asc())
            .limit(limit)
        )
        return result.scalars().all()
