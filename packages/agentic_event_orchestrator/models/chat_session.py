import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON, text
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
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: SessionStatus = Field(default=SessionStatus.active)
    active_agent: Optional[str] = Field(default=None, max_length=100)
    metadata_: Optional[dict] = Field(default=None, sa_column=Column("metadata", JSON))
