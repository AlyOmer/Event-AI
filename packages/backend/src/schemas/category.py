import uuid
from typing import Optional
from pydantic import BaseModel, Field

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon_url: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon_url: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class CategoryRead(CategoryBase):
    id: uuid.UUID
    
    class Config:
        from_attributes = True
