# Requirements Document

## Introduction

Module 011 adds RAG-powered semantic search to the Event-AI vendor marketplace. The existing keyword search (trigram + ILIKE) is extended with vector-based semantic search using Gemini `text-embedding-004` embeddings stored in pgvector on Neon DB. This enables natural-language queries like "traditional mehndi artist in Lahore under 50,000 PKR" to surface semantically relevant vendors even when exact keywords are absent. A hybrid mode blends trigram and semantic scores for best-of-both-worlds ranking.

---

## Glossary

- **EmbeddingService**: The Python service responsible for generating, storing, and refreshing vendor vector embeddings.
- **SearchService**: The existing Python service extended to support semantic and hybrid search modes.
- **VendorEmbedding**: The SQLModel table that stores a 768-dimensional pgvector embedding for each active vendor.
- **Vendor**: An existing SQLModel entity representing a business on the Event-AI marketplace.
- **Service**: An existing SQLModel entity representing a priced offering belonging to a Vendor.
- **content_hash**: A SHA-256 digest of the text used to generate an embedding, used to detect staleness.
- **Cosine Similarity**: The distance metric used by pgvector (`<=>` operator) to rank vendors by semantic relevance.
- **Hybrid Score**: A weighted combination of trigram similarity score and cosine similarity score.
- **HNSW Index**: Hierarchical Navigable Small World index on the embedding column for approximate nearest-neighbour search.
- **Backfill**: The administrative operation that regenerates embeddings for all active vendors in bulk.
- **vendor.approved**: The domain event emitted when an admin approves a vendor registration.
- **vendor.rejected / vendor.suspended**: Domain events that trigger deletion of a vendor's embedding row.
- **respx**: The HTTP mock library used in tests to intercept Gemini API calls without incurring real costs.

---

## Requirements

### Requirement 1: Vendor Embedding Storage

**User Story:** As a platform engineer, I want a dedicated table to store vector embeddings for each vendor, so that semantic search queries can be executed efficiently against pgvector.

#### Acceptance Criteria

1. THE `VendorEmbedding` table SHALL store the fields: `id` (UUID PK), `vendor_id` (UUID FK → `vendors.id`, unique), `embedding` (vector(768)), `content_hash` (SHA-256 hex string), `model_version` (string), `created_at` (timezone-aware datetime), `updated_at` (timezone-aware datetime).
2. THE `VendorEmbedding` table SHALL enforce a unique constraint on `vendor_id` so that each vendor has at most one embedding row.
3. THE Alembic migration SHALL create the `vector` extension idempotently using `CREATE EXTENSION IF NOT EXISTS vector` before creating the `vendor_embeddings` table.
4. THE Alembic migration SHALL create an HNSW index on the `embedding` column using `CREATE INDEX ON vendor_embeddings USING hnsw (embedding vector_cosine_ops)`.
5. THE Alembic migration SHALL be reversible — the `downgrade()` function SHALL drop the `vendor_embeddings` table and the HNSW index.

---

### Requirement 2: Vendor Text Representation

**User Story:** As a platform engineer, I want a deterministic function that converts a vendor's structured data into a rich text string, so that the embedding captures all semantically relevant attributes.

#### Acceptance Criteria

1. THE `EmbeddingService` SHALL expose a `generate_vendor_text(vendor, services) -> str` function that produces a string in the format: `"{business_name}. {description}. Services: {service_names}. Location: {city}, {region}. Categories: {category_names}."`.
2. WHEN `vendor.description` is `None`, THE `EmbeddingService` SHALL omit the description segment rather than inserting the literal string `"None"`.
3. WHEN the vendor has no services, THE `EmbeddingService` SHALL produce the segment `"Services: "` with an empty list rather than raising an exception.
4. FOR ALL valid vendor inputs, THE `EmbeddingService` SHALL produce a text string that contains `vendor.business_name` and `vendor.city`.
5. THE `generate_vendor_text` function SHALL be a pure function with no I/O side effects, enabling unit testing without database or network access.

---

### Requirement 3: Embedding Generation via Gemini API

**User Story:** As a platform engineer, I want the system to call the Gemini `text-embedding-004` model to produce 768-dimensional embeddings, so that vendor text is represented in a high-quality semantic vector space.

#### Acceptance Criteria

1. THE `EmbeddingService` SHALL expose an `embed_text(text: str) -> list[float]` async function that calls the Gemini `text-embedding-004` endpoint via `httpx.AsyncClient`.
2. THE `EmbeddingService` SHALL read `gemini_api_key`, `gemini_embedding_model`, `gemini_base_url`, and `embedding_dimensions` exclusively from the `Settings` object (Pydantic `BaseSettings` + `@lru_cache`).
3. WHEN the Gemini API returns a non-2xx HTTP status, THE `EmbeddingService` SHALL raise a structured exception containing the HTTP status code and response body.
4. THE `embed_text` function SHALL return a list of exactly 768 floats for any non-empty input string.
5. THE `EmbeddingService` SHALL use the `httpx.AsyncClient` instance initialised in the FastAPI lifespan and injected via `Depends()` — it SHALL NOT create a new client per call.

---

### Requirement 4: Embedding Upsert and Staleness Detection

**User Story:** As a platform engineer, I want the system to upsert vendor embeddings and skip regeneration when the vendor text has not changed, so that unnecessary Gemini API calls are avoided.

#### Acceptance Criteria

1. THE `EmbeddingService` SHALL expose an `upsert_vendor_embedding(session, vendor_id) -> VendorEmbedding` async function that generates the vendor text, computes its SHA-256 hash, and upserts the embedding row.
2. WHEN an existing `VendorEmbedding` row has a `content_hash` matching the current vendor text hash, THE `EmbeddingService` SHALL return the existing row without calling the Gemini API.
3. WHEN no existing `VendorEmbedding` row exists for a vendor, THE `EmbeddingService` SHALL create a new row with the generated embedding.
4. WHEN an existing `VendorEmbedding` row has a stale `content_hash`, THE `EmbeddingService` SHALL call the Gemini API, update the `embedding`, `content_hash`, `model_version`, and `updated_at` fields, and persist the updated row.
5. THE `EmbeddingService` SHALL expose an `embed_batch(session, vendor_ids: list[UUID]) -> int` async function that calls `upsert_vendor_embedding` for each vendor ID and returns the count of successfully upserted rows.

---

### Requirement 5: Automatic Embedding Lifecycle via Domain Events

**User Story:** As a platform engineer, I want vendor embeddings to be created automatically when a vendor is approved and deleted when a vendor is rejected or suspended, so that the embedding index always reflects the current set of active vendors.

#### Acceptance Criteria

1. WHEN the `vendor.approved` domain event is emitted, THE `EmbeddingService` SHALL call `upsert_vendor_embedding` for the approved vendor as a FastAPI background task.
2. WHEN the `vendor.rejected` domain event is emitted, THE `EmbeddingService` SHALL delete the corresponding `VendorEmbedding` row if it exists.
3. WHEN the `vendor.suspended` domain event is emitted, THE `EmbeddingService` SHALL delete the corresponding `VendorEmbedding` row if it exists.
4. THE `EmbeddingService` event handlers SHALL be registered in the FastAPI lifespan function — not at module import time.
5. IF a `vendor.approved` event is received for a vendor that already has an embedding, THE `EmbeddingService` SHALL call `upsert_vendor_embedding` which will skip the Gemini call if the content hash is unchanged (idempotent).

---

### Requirement 6: Semantic Search

**User Story:** As a customer, I want to search for vendors using natural language queries, so that I can find semantically relevant vendors even when my query does not contain exact keyword matches.

#### Acceptance Criteria

1. THE `SearchService` SHALL expose a `semantic_search(session, query_text, limit=10, city=None, category_ids=None) -> list[VendorWithScore]` async function that embeds the query text and retrieves vendors ranked by cosine similarity using the pgvector `<=>` operator.
2. WHEN `city` is provided, THE `SearchService` SHALL filter results to vendors whose `city` field matches the provided value (case-insensitive).
3. WHEN `category_ids` is provided, THE `SearchService` SHALL filter results to vendors linked to at least one of the specified category IDs.
4. THE `SearchService` SHALL only return vendors with `status = ACTIVE` in semantic search results.
5. THE `SearchService` SHALL return each result as a `VendorWithScore` object containing the vendor data and a `similarity_score` float between 0.0 and 1.0.
6. WHEN no vendors match the filters or similarity threshold, THE `SearchService` SHALL return an empty list rather than raising an exception.

---

### Requirement 7: Hybrid Search

**User Story:** As a customer, I want search results that combine keyword relevance with semantic relevance, so that I get the most accurate and complete vendor recommendations.

#### Acceptance Criteria

1. THE `SearchService` SHALL expose a `hybrid_search(session, query, limit=20) -> list[VendorWithScore]` async function that combines trigram similarity score and cosine similarity score into a single hybrid score.
2. THE `SearchService` SHALL compute the hybrid score as: `(trigram_weight × trigram_score) + (semantic_weight × semantic_score)` where the default weights are `trigram_weight = 0.4` and `semantic_weight = 0.6`.
3. THE `SearchService` SHALL allow the trigram and semantic weights to be configured via the `Settings` object rather than hardcoded in the function body.
4. THE `SearchService` SHALL return results ordered by descending hybrid score.
5. WHEN a vendor has no embedding row, THE `SearchService` SHALL assign a semantic score of `0.0` for that vendor rather than excluding the vendor from hybrid results.

---

### Requirement 8: Semantic Search API Endpoint

**User Story:** As a frontend developer, I want a dedicated semantic search endpoint, so that the user portal can offer natural-language vendor discovery.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/public_vendors/semantic` accepting query parameters: `q` (required, string), `city` (optional), `category_ids` (optional, list of UUIDs), `limit` (optional, integer, default 10, max 50).
2. THE Backend SHALL return a response envelope `{"success": true, "data": [...], "meta": {"total": N, "query": "..."}}`.
3. WHEN `q` is absent or empty, THE Backend SHALL return HTTP 422 with error code `VALIDATION_QUERY_REQUIRED`.
4. THE Backend SHALL apply a rate limit of 60 requests per minute per IP on the semantic search endpoint.
5. THE semantic search endpoint SHALL require no authentication (public access).
6. WHEN the `EmbeddingService` fails to embed the query (e.g., Gemini API error), THE Backend SHALL return HTTP 503 with error code `AI_EMBEDDING_UNAVAILABLE`.

---

### Requirement 9: Hybrid Search API Endpoint

**User Story:** As a frontend developer, I want the existing vendor search endpoint to support a `mode` parameter, so that clients can choose between keyword, semantic, and hybrid search strategies.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/public_vendors/search` accepting a `mode` query parameter with allowed values: `keyword`, `semantic`, `hybrid` (default: `hybrid`).
2. WHEN `mode=keyword`, THE Backend SHALL delegate to the existing `SearchService.search_vendors` trigram search.
3. WHEN `mode=semantic`, THE Backend SHALL delegate to `SearchService.semantic_search`.
4. WHEN `mode=hybrid`, THE Backend SHALL delegate to `SearchService.hybrid_search`.
5. THE Backend SHALL return a consistent response envelope regardless of the selected mode.
6. THE Backend SHALL apply a rate limit of 60 requests per minute per IP on the hybrid search endpoint.

---

### Requirement 10: Admin Backfill Endpoint

**User Story:** As an admin, I want to trigger a bulk embedding regeneration for all active vendors, so that I can recover from embedding drift or model version upgrades.

#### Acceptance Criteria

1. THE Backend SHALL expose `POST /api/v1/admin/embeddings/backfill` requiring JWT admin authentication.
2. WHEN called without a `vendor_id` body parameter, THE Backend SHALL enqueue `EmbeddingService.embed_batch` for all active vendors as a FastAPI background task and return `{"success": true, "data": {"queued": N}}` immediately.
3. WHEN called with a specific `vendor_id` UUID in the request body, THE Backend SHALL enqueue `upsert_vendor_embedding` for only that vendor and return `{"success": true, "data": {"queued": 1}}`.
4. THE Backend SHALL apply a rate limit of 10 requests per minute on the backfill endpoint.
5. IF the requesting user does not have admin role, THE Backend SHALL return HTTP 403 with error code `AUTH_FORBIDDEN`.

---

### Requirement 11: Settings Configuration

**User Story:** As a platform engineer, I want all embedding-related configuration to be managed through the centralised `Settings` object, so that no secrets or tuning parameters are scattered across modules.

#### Acceptance Criteria

1. THE `Settings` class SHALL include the fields: `gemini_api_key: str`, `gemini_embedding_model: str` (default `"text-embedding-004"`), `gemini_base_url: str` (default `"https://generativelanguage.googleapis.com/v1beta/openai/"`), `embedding_dimensions: int` (default `768`), `hybrid_trigram_weight: float` (default `0.4`), `hybrid_semantic_weight: float` (default `0.6`).
2. THE `Settings` class SHALL be instantiated exactly once via `@lru_cache` and injected via `Depends(get_settings)`.
3. THE `EmbeddingService` and `SearchService` SHALL read all configuration exclusively from the injected `Settings` object — no `os.environ.get()` calls are permitted in these modules.

---

### Requirement 12: Test Suite

**User Story:** As a platform engineer, I want a comprehensive test suite for the RAG module, so that regressions are caught before deployment and zero real LLM API calls are made during CI.

#### Acceptance Criteria

1. THE test suite SHALL include unit tests for `generate_vendor_text()` that verify correct text construction without any database or network access.
2. THE test suite SHALL include unit tests for `hybrid_search()` scoring logic using mock embedding vectors, verifying that the weighted combination formula is applied correctly.
3. THE test suite SHALL include integration tests for `GET /api/v1/public_vendors/semantic` that mock the Gemini HTTP endpoint using `respx` — zero real Gemini API calls SHALL be made.
4. FOR ALL valid vendor inputs, THE test suite SHALL include a property-based test verifying that `generate_vendor_text(vendor, services)` always produces a string containing `vendor.business_name` and `vendor.city`.
5. THE test suite SHALL be executable with `uv run pytest` and SHALL pass with no external network dependencies.
6. THE test suite SHALL mock `embed_text` using `respx` for all integration tests that exercise the semantic or hybrid search code paths.
