# Design Document — Module 011: RAG & Semantic Search

## Overview

This module adds vector-based semantic search to the Event-AI vendor marketplace. Vendor profiles are embedded using Gemini `text-embedding-004` (768 dimensions) and stored in pgvector on Neon DB. The existing `SearchService` is extended with `semantic_search` and `hybrid_search` methods. Two new public endpoints and one admin endpoint are added. Embeddings are kept fresh via domain event hooks and an admin backfill endpoint.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (packages/backend)                             │
│                                                                 │
│  Lifespan                                                       │
│  ├── httpx.AsyncClient  ──────────────────────────────────────► Gemini API
│  ├── EventEmitter.on("vendor.approved", handle_vendor_approved) │
│  └── EventEmitter.on("vendor.rejected/suspended", handle_del)  │
│                                                                 │
│  Routes                                                         │
│  ├── GET  /api/v1/public_vendors/semantic  ──► SearchService    │
│  ├── GET  /api/v1/public_vendors/search    ──► SearchService    │
│  └── POST /api/v1/admin/embeddings/backfill ─► EmbeddingService │
│                                                                 │
│  Services                                                       │
│  ├── EmbeddingService                                           │
│  │   ├── generate_vendor_text(vendor, services) -> str          │
│  │   ├── embed_text(text) -> list[float]  ──► httpx → Gemini   │
│  │   ├── upsert_vendor_embedding(session, vendor_id)            │
│  │   └── embed_batch(session, vendor_ids) -> int                │
│  └── SearchService (extended)                                   │
│      ├── search_vendors(...)   [existing trigram]               │
│      ├── semantic_search(session, query_text, ...)              │
│      └── hybrid_search(session, query, ...)                     │
│                                                                 │
│  Models                                                         │
│  └── VendorEmbedding (new SQLModel table)                       │
│                                                                 │
│  DB: Neon PostgreSQL + pgvector                                 │
│  └── vendor_embeddings (HNSW index on embedding col)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### `VendorEmbedding` — `src/models/vendor_embedding.py`

```python
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column

class VendorEmbedding(SQLModel, table=True):
    __tablename__ = "vendor_embeddings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    vendor_id: uuid.UUID = Field(foreign_key="vendors.id", unique=True, index=True)
    embedding: list[float] = Field(sa_column=Column(Vector(768), nullable=False))
    content_hash: str = Field(max_length=64)          # SHA-256 hex
    model_version: str = Field(default="text-embedding-004")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### `VendorWithScore` — `src/schemas/search.py`

```python
from pydantic import BaseModel
from .vendor import VendorRead

class VendorWithScore(BaseModel):
    vendor: VendorRead
    similarity_score: float
    search_mode: str  # "semantic" | "hybrid" | "keyword"
```

---

## Settings Extension — `src/config/settings.py`

New fields added to the existing `Settings` class:

```python
gemini_embedding_model: str = "text-embedding-004"
gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
embedding_dimensions: int = 768
hybrid_trigram_weight: float = 0.4
hybrid_semantic_weight: float = 0.6
```

`gemini_api_key` is assumed to already exist. All fields are read from `.env` via `pydantic_settings.BaseSettings`.

---

## EmbeddingService — `src/services/embedding_service.py`

### `generate_vendor_text`

Pure function, no I/O. Builds the canonical text representation:

```
"{business_name}. {description}. Services: {s1, s2}. Location: {city}, {region}. Categories: {c1, c2}."
```

- Omits the description segment when `vendor.description is None`.
- Joins service names and category names with `", "`.
- Returns a deterministic string for the same inputs.

### `embed_text`

```python
async def embed_text(self, text: str, http_client: httpx.AsyncClient) -> list[float]:
    url = f"{settings.gemini_base_url}embeddings"
    payload = {"model": settings.gemini_embedding_model, "input": text}
    headers = {"Authorization": f"Bearer {settings.gemini_api_key}"}
    response = await http_client.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]
```

Uses the OpenAI-compatible embeddings endpoint format (`/v1beta/openai/embeddings`).

### `upsert_vendor_embedding`

1. Load vendor + services + categories from DB.
2. Call `generate_vendor_text`.
3. Compute `SHA-256(text)`.
4. Query existing `VendorEmbedding` by `vendor_id`.
5. If exists and `content_hash` matches → return existing row (no Gemini call).
6. Otherwise call `embed_text`, upsert row, return updated row.

### `embed_batch`

Iterates `vendor_ids`, calls `upsert_vendor_embedding` for each, counts successes. Logs failures per vendor without aborting the batch.

### Event Handlers

```python
async def handle_vendor_approved(event_data: dict, session: AsyncSession, http_client: httpx.AsyncClient):
    vendor_id = UUID(event_data["vendor_id"])
    await embedding_service.upsert_vendor_embedding(session, vendor_id, http_client)

async def handle_vendor_deactivated(event_data: dict, session: AsyncSession):
    vendor_id = UUID(event_data["vendor_id"])
    stmt = delete(VendorEmbedding).where(VendorEmbedding.vendor_id == vendor_id)
    await session.execute(stmt)
    await session.commit()
```

Registered in lifespan:

```python
event_emitter.on("vendor.approved", handle_vendor_approved)
event_emitter.on("vendor.rejected", handle_vendor_deactivated)
event_emitter.on("vendor.suspended", handle_vendor_deactivated)
```

---

## SearchService Extensions — `src/services/search_service.py`

### `semantic_search`

```python
async def semantic_search(
    self,
    session: AsyncSession,
    query_text: str,
    limit: int = 10,
    city: Optional[str] = None,
    category_ids: Optional[list[UUID]] = None,
    http_client: Optional[httpx.AsyncClient] = None,
) -> list[VendorWithScore]:
```

1. Call `embedding_service.embed_text(query_text, http_client)` → `query_vector`.
2. Build SQLAlchemy query joining `Vendor` → `VendorEmbedding` on `vendor_id`.
3. Compute cosine distance: `VendorEmbedding.embedding.cosine_distance(query_vector)`.
4. Convert distance to similarity: `similarity = 1 - distance`.
5. Apply `status = ACTIVE`, optional `city` (ILIKE), optional `category_ids` (subquery) filters.
6. Order by distance ASC (closest first), limit to `limit`.
7. Return `list[VendorWithScore]`.

### `hybrid_search`

```python
async def hybrid_search(
    self,
    session: AsyncSession,
    query: str,
    limit: int = 20,
    http_client: Optional[httpx.AsyncClient] = None,
    settings: Optional[Settings] = None,
) -> list[VendorWithScore]:
```

1. Run trigram search (existing logic) → `trigram_results: list[Vendor]` with scores.
2. Run `semantic_search` → `semantic_results: list[VendorWithScore]`.
3. Build score maps keyed by `vendor_id`.
4. Union all vendor IDs from both result sets.
5. For each vendor: `hybrid_score = (w_t × trigram_score) + (w_s × semantic_score)` where missing scores default to `0.0`.
6. Sort by `hybrid_score` descending, return top `limit`.

Weights read from `settings.hybrid_trigram_weight` and `settings.hybrid_semantic_weight`.

---

## API Endpoints

### `GET /api/v1/public_vendors/semantic`

File: `src/api/v1/public_vendors.py` (new route added to existing router)

```
Query params:
  q           str       required
  city        str       optional
  category_ids UUID[]   optional
  limit       int       default=10, max=50

Response 200:
  {"success": true, "data": [VendorWithScore], "meta": {"total": N, "query": "..."}}

Response 422:
  {"success": false, "error": {"code": "VALIDATION_QUERY_REQUIRED", "message": "..."}}

Response 503:
  {"success": false, "error": {"code": "AI_EMBEDDING_UNAVAILABLE", "message": "..."}}
```

Rate limit: 60/min per IP (via `slowapi` or existing rate-limit middleware).

### `GET /api/v1/public_vendors/search`

Augments the existing search endpoint with a `mode` parameter.

```
Query params:
  mode        "keyword"|"semantic"|"hybrid"   default="hybrid"
  q           str       optional
  city        str       optional
  category_ids UUID[]   optional
  limit       int       default=20, max=100
  offset      int       default=0

Response 200:
  {"success": true, "data": [...], "meta": {...}}
```

Delegates to the appropriate `SearchService` method based on `mode`.

### `POST /api/v1/admin/embeddings/backfill`

File: `src/api/v1/admin/embeddings.py` (new file)

```
Auth: JWT Bearer (admin role required)

Request body (optional):
  {"vendor_id": "uuid"}   — omit to backfill all active vendors

Response 200:
  {"success": true, "data": {"queued": N}}

Response 403:
  {"success": false, "error": {"code": "AUTH_FORBIDDEN", "message": "..."}}
```

Rate limit: 10/min per IP.

The endpoint loads all active vendor IDs (or the single specified ID), then calls `BackgroundTasks.add_task(embedding_service.embed_batch, session, vendor_ids)`.

---

## Alembic Migration

File: `alembic/versions/xxxx_add_vendor_embeddings.py`

```python
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "vendor_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("vendors.id"), unique=True, nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "CREATE INDEX ON vendor_embeddings USING hnsw (embedding vector_cosine_ops)"
    )

def downgrade():
    op.execute("DROP INDEX IF EXISTS vendor_embeddings_embedding_idx")
    op.drop_table("vendor_embeddings")
```

---

## File Layout

```
packages/backend/
├── alembic/versions/
│   └── xxxx_add_vendor_embeddings.py
└── src/
    ├── models/
    │   └── vendor_embedding.py          # NEW
    ├── schemas/
    │   └── search.py                    # NEW — VendorWithScore
    ├── services/
    │   ├── embedding_service.py         # NEW
    │   └── search_service.py            # EXTENDED
    ├── api/v1/
    │   ├── public_vendors.py            # EXTENDED — /semantic + /search
    │   └── admin/
    │       └── embeddings.py            # NEW — /admin/embeddings/backfill
    └── config/
        └── settings.py                  # EXTENDED — new fields
```

---

## Dependency Injection Flow

```
lifespan
  └── app.state.http_client = httpx.AsyncClient()

get_http_client(request: Request) -> httpx.AsyncClient
  └── return request.app.state.http_client

semantic_search endpoint
  ├── session: AsyncSession = Depends(get_session)
  ├── http_client: httpx.AsyncClient = Depends(get_http_client)
  └── settings: Settings = Depends(get_settings)
```

`EmbeddingService` and `SearchService` receive `http_client` and `settings` as parameters — they are not singletons that hold state.

---

## Correctness Properties

### Property 1: `generate_vendor_text` always contains business_name and city

For any valid `Vendor` object with a non-empty `business_name` and non-None `city`, `generate_vendor_text(vendor, services)` must contain both values as substrings.

- Type: property-based test (Hypothesis)
- Rationale: The embedding quality depends entirely on the text representation. If business_name or city is missing, semantic search for location-specific queries will fail silently.

### Property 2: Hybrid score is a convex combination

For any pair of trigram score `t ∈ [0,1]` and semantic score `s ∈ [0,1]`, the hybrid score `h = w_t × t + w_s × s` must satisfy `0.0 ≤ h ≤ 1.0` when `w_t + w_s = 1.0`.

- Type: property-based test (Hypothesis)
- Rationale: Out-of-range scores would corrupt ranking order and could cause downstream display bugs.

### Property 3: Upsert is idempotent when content is unchanged

Calling `upsert_vendor_embedding` twice for the same vendor with unchanged data must result in exactly one Gemini API call (the second call is a no-op due to hash match).

- Type: example-based unit test with mock
- Rationale: Prevents runaway API costs during backfill retries or repeated event delivery.

### Property 4: Semantic search returns only ACTIVE vendors

For any query, `semantic_search` must never return a vendor whose `status != ACTIVE`.

- Type: integration test (example-based)
- Rationale: Inactive vendors must not appear in public search results regardless of embedding similarity.

---

## Error Handling

| Failure | Behaviour |
|---|---|
| Gemini API returns non-2xx | `embed_text` raises `EmbeddingAPIError`; endpoint returns HTTP 503 `AI_EMBEDDING_UNAVAILABLE` |
| Vendor not found during upsert | `upsert_vendor_embedding` raises `NotFoundError`; backfill logs and continues |
| pgvector extension missing | Migration fails with clear error; health endpoint reports degraded state |
| `embed_batch` partial failure | Logs per-vendor errors, returns count of successes only |
| Rate limit exceeded | Returns HTTP 429 with `Retry-After` header |

---

## Testing Strategy

| Test | File | Type | Mock |
|---|---|---|---|
| `generate_vendor_text` correctness | `tests/unit/test_embedding_service.py` | Unit | None |
| `generate_vendor_text` property (business_name + city always present) | `tests/unit/test_embedding_service.py` | Property (Hypothesis) | None |
| `hybrid_search` scoring formula | `tests/unit/test_search_service.py` | Unit | Mock embeddings |
| Hybrid score bounds property | `tests/unit/test_search_service.py` | Property (Hypothesis) | None |
| `upsert_vendor_embedding` idempotency | `tests/unit/test_embedding_service.py` | Unit | `respx` mock Gemini |
| `GET /semantic` happy path | `tests/integration/test_public_vendors.py` | Integration | `respx` mock Gemini |
| `GET /semantic` missing `q` → 422 | `tests/integration/test_public_vendors.py` | Integration | None |
| `GET /semantic` Gemini failure → 503 | `tests/integration/test_public_vendors.py` | Integration | `respx` mock Gemini error |
| `POST /admin/embeddings/backfill` auth | `tests/integration/test_admin_embeddings.py` | Integration | `respx` mock Gemini |
| Semantic search returns only ACTIVE vendors | `tests/integration/test_search_service.py` | Integration | `respx` mock Gemini |

All tests run with `uv run pytest`. Zero real Gemini API calls in any test.
