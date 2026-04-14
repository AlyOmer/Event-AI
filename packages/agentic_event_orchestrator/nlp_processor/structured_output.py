from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class EventRequirements(BaseModel):
    event_type: str = Field(..., description="The type of event, e.g., wedding, birthday, conference.")
    attendees: int = Field(..., description="Number of people attending the event.")
    date: str = Field(..., description="Date of the event in YYYY-MM-DD format.")
    budget: float = Field(..., description="Total budget for the event.")
    location: Optional[str] = Field(None, description="City or location for the event.")
    preferences: List[str] = Field(default_factory=list, description="List of specific preferences or requirements.")

class VendorSelection(BaseModel):
    vendor_id: str
    service_id: str
    cost: float
    reason: str

class EventPlan(BaseModel):
    event_details: EventRequirements
    selected_vendors: List[VendorSelection]
    total_cost: float
    schedule: List[str]
