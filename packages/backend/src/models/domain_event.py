import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class DomainEvent(SQLModel, table=True):
    __tablename__ = "domain_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_type: str = Field(index=True, max_length=100)
    version: int = Field(default=1)
    source: str = Field(max_length=50, default="backend")
    correlation_id: Optional[str] = Field(default=None, max_length=100, index=True)
    user_id: Optional[uuid.UUID] = Field(default=None, index=True)
    
    # Store arbitrary payload data using JSONB explicitly for postgres
    data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
