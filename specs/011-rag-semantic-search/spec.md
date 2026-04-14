# Feature Specification: RAG & Semantic Search

**Feature Branch**: `feature/rag-semantic-search`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: "RAG & Semantic Search — pgvector embeddings for vendor/venue matching by meaning"

---

## User Scenarios & Testing

### User Story 1 — Semantic Vendor Search (Priority: P1)

A user (or the AI agent) searches for vendors using natural language like "outdoor wedding venue with garden in Lahore under 5 lakh". Instead of keyword matching, the system embeds the query and performs cosine similarity search against vendor embeddings stored in pgvector, returning vendors ranked by semantic relevance.

**Why this priority**: This is the core value proposition — replacing the current keyword-based scoring (`_calculate_score`) with meaning-based retrieval. Without this, the AI agent can only match exact words.

**Independent Test**: Call `GET /api/v1/vendors/search/semantic?q=luxury+mehndi+hall+islamabad&limit=5` and verify results are ranked by cosine similarity with relevance scores.

**Acceptance Scenarios**:

1. **Given** vendors with embeddings stored in `vendor_embeddings`, **When** a user queries "budget-friendly caterer for walima in Lahore", **Then** the system returns vendors semantically related to walima catering in Lahore, ranked by cosine similarity score.
2. **Given** a query with no close semantic matches, **When** search is executed, **Then** the system returns an empty list (or low-confidence results below the similarity threshold of 0.5).
3. **Given** vendors with both pgvector embeddings and keyword/category filters, **When** a query includes a budget constraint, **Then** results are pre-filtered by budget in SQL before the vector similarity ranking.
4. **Given** 500+ vendors with embeddings, **When** a semantic search is performed, **Then** the response returns within 200ms (p95).

---

### User Story 2 — Vendor Embedding Generation Pipeline (Priority: P1)

When a vendor is registered or updated (name, description, services, keywords, service areas change), the system generates a combined text representation and creates/updates a 1536-dimension embedding via the LLM embedding API, stored in `vendor_embeddings`.

**Why this priority**: Without embeddings, semantic search is impossible. The pipeline must run before any search can work.

**Independent Test**: Create a vendor via `POST /api/v1/vendors`, verify a `vendor.registered` domain event triggers embedding generation, and confirm a row exists in `vendor_embeddings` with a non-null embedding vector.

**Acceptance Scenarios**:

1. **Given** a new vendor is registered with category, description, and keywords, **When** the `vendor.registered` event is emitted, **Then** the AI service generates an embedding from the combined text `"{name} | {category} | {description} | {keywords} | {service_areas}"` and stores it in `vendor_embeddings`.
2. **Given** a vendor updates their description, **When** the `vendor.updated` event fires, **Then** the embedding is regenerated and the `vendor_embeddings` row is upserted.
3. **Given** the LLM embedding API is temporarily unavailable, **When** embedding generation fails, **Then** the system retries 3 times with exponential backoff and logs the failure — the vendor remains searchable via keyword fallback.
4. **Given** a bulk vendor import of 100 vendors, **When** embeddings are generated, **Then** the system batches API calls (max 20 per batch) to avoid rate limits.

---

### User Story 3 — AI Agent Uses Semantic Search Tool (Priority: P1)

The VendorDiscoveryAgent uses a `@function_tool` that calls the semantic search endpoint, replacing the current keyword-based `search_vendors` tool. The agent naturally describes what the user needs, and the tool finds semantically matching vendors.

**Why this priority**: The AI agent is the primary consumer of vendor search — upgrading it from keywords to semantics makes the agent dramatically smarter.

**Independent Test**: In an agent chat session, ask "find me a photographer who does drone shots for outdoor weddings in Islamabad" and verify the agent calls the semantic search tool and returns relevant vendors.

**Acceptance Scenarios**:

1. **Given** a user asks the agent for vendor recommendations, **When** the agent calls `semantic_search_vendors(query, location, budget)`, **Then** the tool calls the semantic search endpoint and returns top-k vendors with similarity scores.
2. **Given** the semantic search returns results, **Then** all vendor data is sanitized via `sanitize_external_content()` before being passed to the agent context (OWASP ASI06 defense).
3. **Given** semantic search returns zero results, **Then** the tool falls back to keyword-based search as a degraded mode.

---

### User Story 4 — Event Embedding for Smart Matching (Priority: P2)

When a user creates an event with requirements, the system generates an event embedding from the requirements text. This enables "reverse matching" — finding vendors whose profiles are most similar to the event's needs.

**Why this priority**: Builds on vendor embeddings to enable proactive vendor recommendations for event plans.

**Independent Test**: Create an event with `requirements: "200 guest traditional wedding, outdoor venue, Pakistani cuisine"`, verify an embedding is stored in `event_embeddings`, then call a matching endpoint to get recommended vendors.

**Acceptance Scenarios**:

1. **Given** a new event is created with requirements, **When** `event.created` fires, **Then** the AI service generates an event embedding and stores it in `event_embeddings`.
2. **Given** an event embedding exists, **When** `GET /api/v1/events/:id/recommended-vendors` is called, **Then** the system performs cosine similarity between the event embedding and all vendor embeddings, returning the top 10 matches.

---

### User Story 5 — Review-Augmented Vendor Embeddings (Priority: P3)

When a user submits a review for a vendor, the review text is appended to the vendor's embedding content and the embedding is regenerated. This makes vendor search reflect real user experiences over time.

**Why this priority**: Enriches the embedding quality with real-world feedback, but depends on the Review system being built first.

**Independent Test**: Submit a review for a vendor, verify the `review.submitted` event triggers embedding regeneration with the review text included.

**Acceptance Scenarios**:

1. **Given** a vendor with 5 reviews, **When** a new review is submitted, **Then** the combined text for embedding generation includes: `"{name} | {category} | {description} | {keywords} | Top review excerpts: {review_1}, {review_2}, ..."`.
2. **Given** the embedding is regenerated, **Then** semantic search results reflect the new review content.

---

### Edge Cases

- What happens if a vendor has no description or keywords? → Generate embedding from `"{name} | {category}"` only; flag for admin review.
- What if the embedding dimension changes (e.g., model upgrade from 1536 to 3072)? → Run a batch migration to regenerate all embeddings; the schema uses `vector(1536)` which must be altered via migration.
- What if two vendors have near-identical embeddings? → They will both appear in results ranked closely; the UI should deduplicate by vendor ID.
- How does the system handle vendors who are deactivated? → Pre-filter by `status = 'ACTIVE'` in SQL before vector similarity.
- What if the user query is in Urdu/Roman Urdu? → The embedding model handles multilingual input (Gemini embeddings support Urdu); results should still be semantically relevant.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST generate 1536-dimension embeddings for vendors using the Gemini embedding API (`text-embedding-004` or equivalent).
- **FR-002**: System MUST store embeddings in the `vendor_embeddings` table using pgvector's `vector(1536)` column type in Neon DB.
- **FR-003**: System MUST expose a semantic search endpoint: `GET /api/v1/vendors/search/semantic` accepting `q` (query text), `location`, `category`, `budget_max`, and `limit` parameters.
- **FR-004**: System MUST perform cosine similarity search using pgvector's `<=>` operator with a configurable similarity threshold (default 0.5).
- **FR-005**: System MUST pre-filter results by SQL conditions (status, location, budget) before applying vector similarity to minimize search space.
- **FR-006**: System MUST regenerate vendor embeddings on `vendor.registered`, `vendor.updated`, and `review.submitted` domain events.
- **FR-007**: System MUST batch embedding API calls (max 20 per batch) with rate limiting to avoid LLM API quota exhaustion.
- **FR-008**: System MUST expose a `@function_tool` (`semantic_search_vendors`) for the AI agent that wraps the semantic search endpoint.
- **FR-009**: System MUST fall back to keyword-based search when semantic search returns zero results or the embedding service is unavailable.
- **FR-010**: System MUST sanitize all vendor data retrieved from the database before passing to agent context (defense against memory poisoning).
- **FR-011**: System MUST generate event embeddings on `event.created` and expose a `GET /api/v1/events/:id/recommended-vendors` endpoint.
- **FR-012**: LangChain MUST only be used for document processing and retrieval chain composition. Agent orchestration MUST use the OpenAI Agents SDK exclusively.
- **FR-013**: Embedding generation MUST be handled by the AI service (`packages/agentic_event_orchestrator`), never by the Node.js backend.
- **FR-014**: The embedding pipeline MUST be initialized in the FastAPI `lifespan` function and use `Depends()` for injection — no lazy initialization.

### Key Entities

- **VendorEmbedding**: Stores the vendor's 1536-dim embedding vector, the combined text content used to generate it, and metadata (model version, generation timestamp). One-to-one with Vendor.
- **EventEmbedding**: Stores the event's requirements embedding for reverse vendor matching. One-to-one with Event.
- **Vendor**: Source entity providing name, category, description, keywords, service_areas, and reviews for embedding text composition.
- **Review**: User feedback text that enriches vendor embeddings over time.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Semantic search returns more relevant results than keyword search — measured by manual evaluation showing ≥70% of top-5 results are relevant to the query intent.
- **SC-002**: Embedding generation completes within 2 seconds per vendor (single) and 30 seconds per batch of 20.
- **SC-003**: Semantic search endpoint responds within 200ms (p95) for a database of 500+ vendors.
- **SC-004**: 100% of vendor create/update events trigger embedding generation — zero vendors without embeddings after pipeline stabilization.
- **SC-005**: Zero raw `os.environ.get()` or `sys.path.insert` calls in the embedding pipeline — all configuration via Pydantic `BaseSettings`.
- **SC-006**: Embedding pipeline achieves 80%+ test coverage with zero LLM API calls (embeddings mocked via `respx`).
- **SC-007**: The AI agent's `semantic_search_vendors` tool successfully replaces keyword-based search in agent flows with no regression in user experience.

---

## Constitution Compliance Checklist

Every implementation decision in this feature MUST satisfy the following constitution mandates:

| Constitution Rule | Section | Requirement for RAG & Semantic Search |
|---|---|---|
| **pgvector in Neon DB** | II (AI Stack) | All embeddings MUST be stored in pgvector within Neon DB — no external vector databases (Qdrant, Pinecone, etc.). |
| **LangChain for retrieval only** | II (AI Stack), VII.1 | LangChain MUST only be used for document processing, chunking, and retrieval chains. Agent orchestration MUST use the OpenAI Agents SDK. |
| **Event-Driven Architecture** | III.1–III.8 | Embedding generation MUST be triggered by domain events (`vendor.registered`, `vendor.updated`, `review.submitted`) — never inline in route handlers. |
| **At-least-once delivery + idempotency** | III.5 | Embedding generation consumers MUST be idempotent. Re-processing the same event produces the same embedding (upsert). |
| **Async DB via `create_async_engine`** | IV.1 | All pgvector queries MUST use async engines with `pool_pre_ping=True`. |
| **Prevent N+1 queries** | IV.2 | Vendor retrieval for embedding generation MUST use eager loading (`selectinload`) for services, keywords, reviews. |
| **Lifespan for resources** | VII.9 | Embedding model client, async DB engine MUST be initialized in FastAPI `lifespan` and stored on `app.state`. No lazy init. |
| **`Depends()` for DI** | VII.10 | DB sessions and embedding clients MUST be injected into endpoints and tools via `Depends()`. |
| **Pydantic `BaseSettings`** | VII.11 | Embedding model name, API key, dimension size MUST be configured via `BaseSettings` + `@lru_cache`. No `os.environ.get()`. |
| **API → Function → Tool pattern** | VII.12 | Semantic search: REST endpoint wraps business logic function, `@function_tool` wraps endpoint for agent use. |
| **Tool docstrings mandatory** | VII.14 | `semantic_search_vendors` MUST have a clear docstring. Return type MUST be `str` (JSON). |
| **SSE streaming** | VII.13 | If agent uses semantic search in a chat flow, results MUST stream via `EventSourceResponse`. |
| **No `sys.path.insert`** | X (Python) | All imports MUST use proper package structure via `pyproject.toml`. |
| **TDD — Zero LLM calls in tests** | V | Embedding API calls MUST be mocked via `respx`. 80%+ coverage on search endpoints. |
| **API envelope** | VI.2 | Semantic search responses MUST follow `{ success, data, meta }` format with pagination. |
| **Rate limiting** | VIII.3 | Semantic search endpoint: 60 req/min (Public API). Embedding generation: internal only. |
| **Input validation** | VIII.4 | Search query, location, budget MUST be validated via Zod (backend) or Pydantic (AI service). |
| **Prisma schema standards** | X (Prisma) | Embedding models MUST use `@@map()`, `@map()`, UUIDv4 IDs, `@db.Timestamptz()`, indexes on foreign keys. |
| **YAGNI** | IX.1 | Start with pgvector cosine similarity. Do not add hybrid search, re-ranking, or fine-tuned models until needed. |
| **Minimal dependencies** | IX.6 | Justify every new RAG dependency. Prefer pgvector's built-in operators over external retrieval libraries. |
