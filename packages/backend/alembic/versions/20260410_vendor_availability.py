"""vendor_availability

Revision ID: 20260410_vendor_availability
Revises: 20260410_event_management
Create Date: 2026-04-10

Creates the vendor_availability table for the Booking System (009).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260410_vendor_availability"
down_revision: Union[str, None] = "20260410_event_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendor_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="SET NULL"), nullable=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_reason", sa.Text, nullable=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("vendor_id", "service_id", "date", name="uq_vendor_service_date"),
    )
    op.create_index("ix_vendor_availability_vendor_id", "vendor_availability", ["vendor_id"])
    op.create_index("ix_vendor_availability_service_id", "vendor_availability", ["service_id"])
    op.create_index("ix_vendor_availability_date", "vendor_availability", ["date"])
    op.create_index("ix_vendor_availability_status", "vendor_availability", ["status"])


def downgrade() -> None:
    op.drop_index("ix_vendor_availability_status", table_name="vendor_availability")
    op.drop_index("ix_vendor_availability_date", table_name="vendor_availability")
    op.drop_index("ix_vendor_availability_service_id", table_name="vendor_availability")
    op.drop_index("ix_vendor_availability_vendor_id", table_name="vendor_availability")
    op.drop_table("vendor_availability")
