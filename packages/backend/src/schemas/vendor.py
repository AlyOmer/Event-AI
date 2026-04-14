import uuid
from typing import Optional, List
from pydantic import BaseModel, EmailStr, HttpUrl, Field
from ..models.vendor import VendorStatus
from .category import CategoryRead
from datetime import datetime


class VendorBase(BaseModel):
    business_name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    website: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = None
    region: Optional[str] = None


class VendorCreate(VendorBase):
    category_ids: List[uuid.UUID] = Field(default_factory=list)


class VendorUpdate(BaseModel):
    business_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = None
    region: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    category_ids: Optional[List[uuid.UUID]] = None


class VendorRead(VendorBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: VendorStatus
    rating: float
    total_reviews: int
    logo_url: Optional[str] = None
    categories: List[CategoryRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VendorSearchQuery(BaseModel):
    q: Optional[str] = None
    category_ids: Optional[List[uuid.UUID]] = None
    city: Optional[str] = None
    region: Optional[str] = None
    min_rating: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = Field(20, le=100)
    offset: int = 0
