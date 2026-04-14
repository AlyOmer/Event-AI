# Tasks — Module 011: RAG & Semantic Search

## Task List

- [ ] 1. Alembic Migration: vendor_embeddings table
  - [ ] 1.1 Create migration file with `CREATE EXTENSION IF NOT EXISTS vector`, `vendor_embeddings` table DDL, and HNSW index
  - [ ] 1.2 Implement reversible `downgrade()` that drops the HNSW index and the table
  - [ ] 1.3 Verify migration runs cleanly against Neon DB branch with `uv run alembic upgrade head`

- [ ] 2. VendorEmbedding SQLModel
  - [ ] 2.1 Create `src/models/vendor_embedding.py` with `VendorEmbedding` SQLModel table (id, vendor_id, embedding Vector(768), content_hash, model_version, created_at, updated_at)
  - [ ] 2.2 Add `VendorEmbedding` to `src/models/__init__.py` exports

- [ ] 3. Settings Extension
  - [ ] 3.1 Add `gemini_embedding_model`, `gemini_base_url`, `embedding_dimensions`, `hybrid_trigram_weight`, `hybrid_semantic_weight` fields to the `Settings` class in `src/config/settings.py`

- [ ] 4. VendorWithScore Schema
  - [ ] 4.1 Create `src/schemas/search.py` with `VendorWithScore` Pydantic model (vendor: VendorRead, similarity_score: float, search_mode: str)

- [ ] 5. EmbeddingService — core functions
  - [ ] 5.1 Create `src/services/embedding_service.py`
  - [ ] 5.2 Implement `generate_vendor_text(vendor, services) -> str` as a pure function
  - [ ] 5.3 Implement `embed_text(text, http_client) -> list[float]` using `httpx.AsyncClient` against the Gemini OpenAI-compatible embeddings endpoint
  - [ ] 5.4 Implement `upsert_vendor_embedding(session, vendor_id, http_client) -> VendorEmbedding` with SHA-256 staleness detection
  - [ ] 5.5 Implement `embed_batch(session, vendor_ids, http_client) -> int` with per-vendor error logging

- [ ] 6. EmbeddingService — domain event handlers
  - [ ] 6.1 Implement `handle_vendor_approved(event_data, session, http_client)` that calls `upsert_vendor_embedding` as a background task
  - [ ] 6.2 Implement `handle_vendor_deactivated(event_data, session)` that deletes the `VendorEmbedding` row for the vendor
  - [ ] 6.3 Register both handlers on `vendor.approved`, `vendor.rejected`, and `vendor.suspended` events inside the FastAPI lifespan function

- [ ] 7. SearchService — semantic_search
  - [ ] 7.1 Add `semantic_search(session, query_text, limit, city, category_ids, http_client) -> list[VendorWithScore]` to `SearchService`
  - [ ] 7.2 Implement pgvector cosine distance query joining `Vendor` and `VendorEmbedding`, converting distance to similarity score
  - [ ] 7.3 Apply `status = ACTIVE`, optional `city` (ILIKE), and optional `category_ids` filters

- [ ] 8. SearchService — hybrid_search
  - [ ] 8.1 Add `hybrid_search(session, query, limit, http_client, settings) -> list[VendorWithScore]` to `SearchService`
  - [ ] 8.2 Implement score merging: union trigram and semantic result sets, apply weighted combination, sort descending
  - [ ] 8.3 Default missing scores to `0.0` for vendors present in only one result set
  - [ ] 8.4 Read weights from `settings.hybrid_trigram_weight` and `settings.hybrid_semantic_weight`

- [ ] 9. Public Vendor API — semantic endpoint
  - [ ] 9.1 Add `GET /api/v1/public_vendors/semantic` route to `src/api/v1/public_vendors.py`
  - [ ] 9.2 Validate `q` is present and non-empty; return HTTP 422 `VALIDATION_QUERY_REQUIRED` otherwise
  - [ ] 9.3 Catch `EmbeddingAPIError` and return HTTP 503 `AI_EMBEDDING_UNAVAILABLE`
  - [ ] 9.4 Return response envelope `{"success": true, "data": [...], "meta": {"total": N, "query": "..."}}`
  - [ ] 9.5 Apply 60/min rate limit

- [ ] 10. Public Vendor API — hybrid search endpoint
  - [ ] 10.1 Add `GET /api/v1/public_vendors/search` route (or extend existing) with `mode` query param (`keyword` | `semantic` | `hybrid`, default `hybrid`)
  - [ ] 10.2 Delegate to `search_vendors`, `semantic_search`, or `hybrid_search` based on `mode`
  - [ ] 10.3 Return consistent response envelope for all modes
  - [ ] 10.4 Apply 60/min rate limit

- [ ] 11. Admin Backfill Endpoint
  - [ ] 11.1 Create `src/api/v1/admin/embeddings.py` with `POST /api/v1/admin/embeddings/backfill`
  - [ ] 11.2 Require JWT admin authentication; return HTTP 403 `AUTH_FORBIDDEN` for non-admin callers
  - [ ] 11.3 When no `vendor_id` provided, query all active vendor IDs and enqueue `embed_batch` as a `BackgroundTask`
  - [ ] 11.4 When `vendor_id` provided, enqueue `upsert_vendor_embedding` for that single vendor
  - [ ] 11.5 Return `{"success": true, "data": {"queued": N}}` immediately
  - [ ] 11.6 Apply 10/min rate limit
  - [ ] 11.7 Register the admin embeddings router in the main FastAPI app

- [ ] 12. Unit Tests — EmbeddingService
  - [ ] 12.1 Write unit tests for `generate_vendor_text` covering: normal vendor, None description, no services, no categories
  - [ ] 12.2 Write property-based test (Hypothesis) verifying `generate_vendor_text` always contains `business_name` and `city` for any valid vendor input
  - [ ] 12.3 Write unit test for `upsert_vendor_embedding` idempotency: mock `respx` to intercept Gemini, call twice with same data, assert Gemini called exactly once

- [ ] 13. Unit Tests — SearchService hybrid scoring
  - [ ] 13.1 Write unit tests for `hybrid_search` scoring formula with mock embedding vectors, verifying weighted combination is applied correctly
  - [ ] 13.2 Write property-based test (Hypothesis) verifying hybrid score is always in `[0.0, 1.0]` for any `t, s ∈ [0,1]` with `w_t + w_s = 1.0`

- [ ] 14. Integration Tests — semantic search endpoint
  - [ ] 14.1 Write integration test for `GET /api/v1/public_vendors/semantic` happy path using `respx` to mock Gemini embeddings endpoint
  - [ ] 14.2 Write integration test for missing `q` → HTTP 422
  - [ ] 14.3 Write integration test for Gemini API failure → HTTP 503 `AI_EMBEDDING_UNAVAILABLE`
  - [ ] 14.4 Write integration test verifying only `ACTIVE` vendors appear in semantic search results

- [ ] 15. Integration Tests — admin backfill endpoint
  - [ ] 15.1 Write integration test for `POST /api/v1/admin/embeddings/backfill` with valid admin JWT, mock Gemini via `respx`
  - [ ] 15.2 Write integration test for non-admin caller → HTTP 403

- [ ] 16. Dependency wiring and smoke test
  - [ ] 16.1 Add `get_http_client` dependency function to `src/config/dependencies.py` (or equivalent) that returns `request.app.state.http_client`
  - [ ] 16.2 Confirm `httpx.AsyncClient` is initialised in lifespan and stored on `app.state`
  - [ ] 16.3 Run `uv run pytest` and confirm all new tests pass with zero real Gemini API calls
