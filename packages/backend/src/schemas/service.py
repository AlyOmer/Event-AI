import uuid
from typing import Optional
from pydantic import BaseModel, Field

class ServiceBase(BaseModel):
    name: str = Field(..., max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    capacity: Optional[int] = Field(None, ge=1)
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    requirements: Optional[str] = None
    is_active: bool = True

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    capacity: Optional[int] = Field(None, ge=1)
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    requirements: Optional[str] = None
    is_active: Optional[bool] = None

class ServiceRead(ServiceBase):
    id: uuid.UUID
    vendor_id: uuid.UUID
    
    class Config:
        from_attributes = True
