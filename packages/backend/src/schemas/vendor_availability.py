"""
Pydantic schemas for vendor availability endpoints.
"""
import uuid
from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class AvailabilityUpsert(BaseModel):
    """Request body for creating/updating a single availability slot.

    Note: 'booked' is intentionally excluded — that status is set only by
    the booking service when a booking is confirmed.
    """
    date: date
    status: Literal["available", "blocked", "tentative"]
    service_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=500)


class BulkAvailabilityUpsert(BaseModel):
    """Request body for bulk-upserting availability slots in one transaction."""
    entries: List[AvailabilityUpsert] = Field(..., min_length=1, max_length=90)


class AvailabilityRead(BaseModel):
    """Response schema for a single availability record."""
    id: uuid.UUID
    vendor_id: uuid.UUID
    service_id: Optional[uuid.UUID]
    date: date
    status: str
    notes: Optional[str]
    booking_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
