import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON, text


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    __table_args__ = {"schema": "ai"}

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="ai.chat_sessions.id", index=True)
    sequence: int
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_name: Optional[str] = Field(default=None, max_length=100)
    tool_calls: Optional[list] = Field(default=None, sa_column=Column(JSON))
    token_count: Optional[int] = None
    latency_ms: Optional[int] = None
