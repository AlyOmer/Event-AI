"""
PreferenceService — per-user notification opt-in/out management.
"""
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import NotificationType
from src.models.notification_preference import NotificationPreference
import structlog

logger = structlog.get_logger()


class PreferenceService:

    async def get_preferences(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> List[dict]:
        result = await session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        rows = result.scalars().all()
        return [
            {"notification_type": r.notification_type, "enabled": r.enabled}
            for r in rows
        ]

    async def upsert_preference(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        enabled: bool,
    ) -> dict:
        result = await session.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.notification_type == notification_type.value,
            )
        )
        pref = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if pref:
            pref.enabled = enabled
            pref.updated_at = now
        else:
            pref = NotificationPreference(
                user_id=user_id,
                notification_type=notification_type.value,
                enabled=enabled,
            )
            session.add(pref)

        await session.commit()
        await session.refresh(pref)
        logger.info("preference.upserted", user_id=str(user_id), type=notification_type.value, enabled=enabled)
        return {"notification_type": pref.notification_type, "enabled": pref.enabled}

    async def is_enabled(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        notification_type: NotificationType,
    ) -> bool:
        """Returns True if no preference row exists (opt-in default) or row.enabled is True."""
        result = await session.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.notification_type == notification_type.value,
            )
        )
        pref = result.scalar_one_or_none()
        return pref.enabled if pref is not None else True


preference_service = PreferenceService()
