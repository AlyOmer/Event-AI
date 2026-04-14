"""event_management

Revision ID: 20260410_event_management
Revises: 20250409_vendor_marketplace
Create Date: 2026-04-10

Adds event_types and events tables for the Event Management module (005).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260410_event_management"
down_revision: Union[str, None] = ("20250409_vendor_marketplace", "572da3239ca3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # event_types table
    op.create_table(
        "event_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("icon", sa.String(255), nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_event_types_name", "event_types", ["name"], unique=True)
    op.create_index("ix_event_types_is_active", "event_types", ["is_active"])

    # event_status enum — idempotent
    op.execute(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_status_enum') THEN "
        "    CREATE TYPE event_status_enum AS ENUM ('draft', 'planned', 'active', 'completed', 'canceled'); "
        "  END IF; "
        "END $$;"
    )

    # events table
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_types.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default=sa.text("'Asia/Karachi'")),
        sa.Column("venue_name", sa.String(255), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=False, server_default=sa.text("'Pakistan'")),
        sa.Column("guest_count", sa.Integer, nullable=True),
        sa.Column("budget", sa.Float, nullable=True),
        sa.Column("special_requirements", sa.Text, nullable=True),
        sa.Column("status", postgresql.ENUM("draft", "planned", "active", "completed", "canceled", name="event_status_enum", create_type=False), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("cancellation_reason", sa.String(500), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_events_user_id", "events", ["user_id"])
    op.create_index("ix_events_event_type_id", "events", ["event_type_id"])
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_start_date", "events", ["start_date"])
    op.create_index("ix_events_name", "events", ["name"])


def downgrade() -> None:
    op.drop_index("ix_events_name", table_name="events")
    op.drop_index("ix_events_start_date", table_name="events")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_index("ix_events_event_type_id", table_name="events")
    op.drop_index("ix_events_user_id", table_name="events")
    op.drop_table("events")
    op.execute("DROP TYPE IF EXISTS event_status_enum")
    op.drop_index("ix_event_types_is_active", table_name="event_types")
    op.drop_index("ix_event_types_name", table_name="event_types")
    op.drop_table("event_types")
