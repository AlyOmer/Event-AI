"""add_notification_types_event_vendor

Revision ID: 20260410_notification_types_event_vendor
Revises: 20260410_notifications
Create Date: 2026-04-10

Adds event_created, event_status_changed, event_cancelled, vendor_approved,
vendor_rejected to the notification_type Postgres ENUM.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "20260410_notification_types_event_vendor"
down_revision: Union[str, None] = "20260410_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_VALUES = [
    "event_created",
    "event_status_changed",
    "event_cancelled",
    "vendor_approved",
    "vendor_rejected",
]


def upgrade() -> None:
    for value in NEW_VALUES:
        op.execute(
            f"ALTER TYPE notification_type ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    # Postgres does not support removing enum values without recreating the type.
    # This is intentionally a no-op — removing enum values requires a full type
    # recreation which is destructive. Document this limitation.
    pass
