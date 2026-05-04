import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector


class VendorEmbedding(SQLModel, table=True):
    """Stores the pgvector embedding for a vendor's profile text.

    One row per vendor (unique constraint on vendor_id).  The embedding column
    holds a 768-dimensional float vector produced by Gemini text-embedding-004.
    content_hash is the SHA-256 hex digest of the canonical vendor text; it is
    used to skip re-embedding when the profile has not changed.
    """

    __tablename__ = "vendor_embeddings"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    vendor_id: uuid.UUID = Field(
        foreign_key="vendors.id",
        unique=True,
        index=True,
    )
    # 768-dimensional vector — pgvector column type registered by the extension.
    # Nullable at the SQLModel level so the object can be constructed before the
    # embedding is fetched; the DB column itself is NOT NULL (enforced by the
    # migration).
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(768), nullable=False),
    )
    # SHA-256 hex digest (64 chars) of the canonical vendor text.
    content_hash: str = Field(max_length=64)
    # Embedding model identifier, e.g. "text-embedding-004".
    model_version: str = Field(default="text-embedding-004", max_length=64)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )
