import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON


class ExecutionStatus(str, Enum):
    completed = "completed"
    errored = "errored"
    timeout = "timeout"


class AgentExecution(SQLModel, table=True):
    __tablename__ = "agent_executions"
    __table_args__ = {"schema": "ai"}

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="ai.chat_sessions.id", index=True)
    message_id: uuid.UUID = Field(foreign_key="ai.messages.id")
    agent_name: str = Field(max_length=100)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    status: ExecutionStatus = Field(default=ExecutionStatus.completed)
    tokens_used: Optional[int] = None
    error: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    metadata_: Optional[dict] = Field(default=None, sa_column=Column("metadata", JSON))
