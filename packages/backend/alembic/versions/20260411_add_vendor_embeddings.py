"""add_vendor_embeddings

Revision ID: 20260411_add_vendor_embeddings
Revises: 20260410_notification_preferences
Create Date: 2026-04-11

Creates the vendor_embeddings table for Module 011: RAG & Semantic Search.
Enables the pgvector extension and adds an HNSW index on the embedding column
for efficient approximate nearest-neighbour cosine similarity search.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260411_add_vendor_embeddings"
down_revision: Union[str, None] = "20260410_notification_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension idempotently — must precede table creation.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "vendor_embeddings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "vendor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vendors.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        # pgvector column — 768 dimensions for Gemini text-embedding-004.
        # Declared as Text with a CHECK constraint is not needed; the vector
        # type is registered by the extension and referenced via raw DDL below.
        sa.Column("embedding", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Alter the embedding column to the proper vector(768) type now that the
    # extension is active.  Using ALTER COLUMN avoids importing pgvector into
    # the migration file while still producing the correct column type.
    op.execute(
        "ALTER TABLE vendor_embeddings "
        "ALTER COLUMN embedding TYPE vector(768) "
        "USING embedding::vector(768)"
    )

    # HNSW index for approximate nearest-neighbour cosine similarity search.
    op.execute(
        "CREATE INDEX ix_vendor_embeddings_embedding_hnsw "
        "ON vendor_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # Standard B-tree index on vendor_id for FK lookups.
    op.create_index(
        "ix_vendor_embeddings_vendor_id",
        "vendor_embeddings",
        ["vendor_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_vendor_embeddings_vendor_id", table_name="vendor_embeddings")
    op.execute(
        "DROP INDEX IF EXISTS ix_vendor_embeddings_embedding_hnsw"
    )
    op.drop_table("vendor_embeddings")
    # Note: we intentionally do NOT drop the vector extension here because
    # other tables or future migrations may depend on it.
