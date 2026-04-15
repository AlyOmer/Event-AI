import asyncio
from sqlalchemy import Column, String, Enum as SAEnum
from enum import Enum
from sqlmodel import SQLModel, Field, create_engine
from sqlalchemy.ext.asyncio import create_async_engine

class SessionStatus(str, Enum):
    active = "active"

class ChatSessionFixed(SQLModel, table=True):
    __tablename__ = "chat_test"
    id: int = Field(primary_key=True)
    status: SessionStatus = Field(sa_column=Column(SAEnum(SessionStatus, native_enum=False, length=20)))

print("Compiled!")
