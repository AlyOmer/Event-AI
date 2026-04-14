"""
VendorAvailability model — tracks per-vendor-per-service-per-date slot state
with optimistic locking support.
"""
import uuid
from datetime import datetime, date as date_type, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime, UniqueConstraint, String


class AvailabilityStatus:
    AVAILABLE = "available"
    LOCKED = "locked"
    BOOKED = "booked"
    BLOCKED = "blocked"


class VendorAvailability(SQLModel, table=True):
    __tablename__ = "vendor_availability"
    __table_args__ = (
        UniqueConstraint("vendor_id", "service_id", "date", name="uq_vendor_service_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", index=True)
    service_id: Optional[uuid.UUID] = Field(default=None, foreign_key="services.id", index=True)
    date: date_type = Field(index=True)

    # Status: available | locked | booked | blocked
    status: str = Field(default=AvailabilityStatus.AVAILABLE, max_length=20)

    # Locking fields (set when status=locked)
    locked_by: Optional[uuid.UUID] = Field(default=None)
    locked_until: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    locked_reason: Optional[str] = Field(default=None, max_length=255)

    # Booking reference (set when status=booked)
    booking_id: Optional[uuid.UUID] = Field(default=None, foreign_key="bookings.id")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
