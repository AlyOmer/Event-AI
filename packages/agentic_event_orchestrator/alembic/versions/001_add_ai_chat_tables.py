"""Add AI chat tables

Revision ID: 001_ai_chat_tables
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_ai_chat_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ai schema
    op.execute("CREATE SCHEMA IF NOT EXISTS ai")

    # Create chat_sessions table
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("active_agent", sa.String(length=100), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="ai",
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"], schema="ai")

    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB, nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["ai.chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="ai",
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"], schema="ai")
    op.create_index("ix_messages_created_at", "messages", ["created_at"], schema="ai")

    # Create agent_executions table
    op.create_table(
        "agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("error", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["ai.chat_sessions.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["ai.messages.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="ai",
    )
    op.create_index("ix_agent_executions_session_id", "agent_executions", ["session_id"], schema="ai")

    # Create message_feedback table
    op.create_table(
        "message_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.String(length=10), nullable=False),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["ai.messages.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="ai",
    )
    op.create_index("ix_message_feedback_message_id", "message_feedback", ["message_id"], schema="ai")


def downgrade() -> None:
    op.drop_table("message_feedback", schema="ai")
    op.drop_table("agent_executions", schema="ai")
    op.drop_table("messages", schema="ai")
    op.drop_table("chat_sessions", schema="ai")
    op.execute("DROP SCHEMA IF EXISTS ai CASCADE")
