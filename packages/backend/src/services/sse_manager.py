"""
SSE Connection Manager — in-process pub/sub for real-time push (008).

The singleton is stored on app.state (initialized in lifespan).
Use get_connection_manager() as a FastAPI dependency.
"""
import asyncio
import uuid
from typing import Any, Dict, List

import structlog
from fastapi import Request

logger = structlog.get_logger()

DEFAULT_QUEUE_MAXSIZE = 50


class SSEConnectionManager:
    def __init__(self, queue_maxsize: int = DEFAULT_QUEUE_MAXSIZE):
        self._connections: Dict[uuid.UUID, List[asyncio.Queue]] = {}
        self._dropped: Dict[uuid.UUID, int] = {}
        self._queue_maxsize = queue_maxsize

    def connect(self, user_id: uuid.UUID) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._queue_maxsize)
        self._connections.setdefault(user_id, []).append(q)
        logger.debug("sse.connected", user_id=str(user_id))
        return q

    def disconnect(self, user_id: uuid.UUID, queue: asyncio.Queue) -> None:
        conns = self._connections.get(user_id, [])
        if queue in conns:
            conns.remove(queue)
        if not conns:
            self._connections.pop(user_id, None)
        logger.debug("sse.disconnected", user_id=str(user_id))

    def dropped_count(self, user_id: uuid.UUID) -> int:
        """Return the number of messages dropped due to queue overflow for a user."""
        return self._dropped.get(user_id, 0)

    async def push(self, user_id: uuid.UUID, event_type: str, data: Dict[str, Any]) -> None:
        """Push to all queues for a user. Uses evict-oldest on overflow."""
        for q in list(self._connections.get(user_id, [])):
            try:
                q.put_nowait({"event": event_type, "data": data})
            except asyncio.QueueFull:
                # Evict oldest message, insert newest
                try:
                    q.get_nowait()  # discard oldest
                    q.put_nowait({"event": event_type, "data": data})
                    self._dropped[user_id] = self._dropped.get(user_id, 0) + 1
                    logger.warning(
                        "sse.queue_overflow_evicted",
                        user_id=str(user_id),
                        event_type=event_type,
                        queue_size=q.qsize(),
                        total_dropped=self._dropped[user_id],
                    )
                except Exception as e:
                    logger.error(
                        "sse.push_failed_after_eviction",
                        user_id=str(user_id),
                        event_type=event_type,
                        error=str(e),
                    )


def get_connection_manager(request: Request) -> SSEConnectionManager:
    """FastAPI dependency — reads SSEConnectionManager from app.state."""
    return request.app.state.connection_manager
