import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON, text, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class SessionStatus(str, Enum):
    active = "active"
    closed = "closed"
    expired = "expired"


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"
    __table_args__ = {"schema": "ai"}

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    user_id: uuid.UUID = Field(index=True)
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_activity_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    status: str = Field(
        default=SessionStatus.active.value,
        sa_column=Column("status", String(20), server_default="active", nullable=False),
    )
    active_agent: Optional[str] = Field(default=None, max_length=100)
    metadata_: Optional[dict] = Field(default=None, sa_column=Column("metadata", JSON))
