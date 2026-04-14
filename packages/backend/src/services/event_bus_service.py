"""
Event Bus Service for asynchronous domain event dispatching and persistence.
Fulfils requirements of Spec 009.
"""
import uuid
from typing import Any, Dict, List, Optional, Callable, Coroutine
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.domain_event import DomainEvent
import structlog

logger = structlog.get_logger()

# Listener signature: async fn(event_type, payload, user_id, session=None)
EventListener = Callable[..., Coroutine[Any, Any, None]]


class EventBusService:
    def __init__(self):
        self._listeners: Dict[str, List[EventListener]] = {}

    def subscribe(self, event_type: str, listener: EventListener):
        """Subscribe to a specific event type."""
        self._listeners.setdefault(event_type, []).append(listener)
        logger.debug("event_bus.subscribed", event_type=event_type)

    async def emit(
        self,
        session: AsyncSession,
        event_type: str,
        payload: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[str] = None,
    ):
        """
        Emit a domain event:
        1. Persists it to the database (same session — Outbox Pattern lite).
        2. Triggers registered async listeners, passing session for atomicity.
        """
        try:
            session.add(DomainEvent(
                event_type=event_type,
                data=payload,
                correlation_id=correlation_id or str(uuid.uuid4()),
                source="backend_service",
                user_id=user_id,
            ))
            logger.info("event_bus.emitted", event_type=event_type, user_id=str(user_id))

            for listener in self._listeners.get(event_type, []):
                try:
                    await listener(event_type, payload, user_id, session=session)
                except Exception as e:
                    logger.error("event_bus.listener_error", event_type=event_type, error=str(e))

        except Exception as e:
            logger.error("event_bus.emit_failed", event_type=event_type, error=str(e))
            raise


# Global singleton instance
event_bus = EventBusService()
