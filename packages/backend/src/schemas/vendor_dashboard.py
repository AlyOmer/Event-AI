"""
Pydantic schemas for the vendor dashboard endpoint.
"""
import uuid
from datetime import date
from typing import Optional, List
from pydantic import BaseModel

from ..models.booking import BookingStatus


class RecentBookingItem(BaseModel):
    id: uuid.UUID
    service_name: Optional[str]
    event_date: date
    status: BookingStatus
    total_price: float
    currency: str
    client_name: Optional[str]

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    active_services: int
    total_services: int
    recent_bookings: List[RecentBookingItem]
