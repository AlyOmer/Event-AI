<!--
SYNC IMPACT REPORT (Constitution Update)
========================================
Version change: 2.1.0 → 2.2.0 (MINOR bump: terminology — RAG → Agentic RAG throughout)
Date: 2026-05-01

Modified sections:
- Section VII title: "Augmented Memory & RAG Architecture" → "Augmented Memory & Agentic RAG Architecture"
- Section VII body: all "RAG" references updated to "Agentic RAG"
- AI Layer stack table: "RAG Framework" row updated to "Agentic RAG Framework"
- Anti-Patterns: Updated LangChain anti-pattern description to reference "Agentic RAG"
- CLAUDE.md and AGENTS.md updated in sync (3 occurrences each)

Rationale: "Agentic RAG" is more precise — it signals that an agent orchestrates the
retrieval process (query planning, multi-step retrieval, synthesis), not just a passive
vector lookup pipeline. This distinction is architecturally significant and prevents
misuse of LangChain for orchestration.

Previous update history:
- 2.1.0 (2026-04-27): MINOR — MCP Protocol Integration + Monetization Framework
- 2.0.0 (2026-04-08): MAJOR — switched backend from Node.js to Python
- 1.3.1 → 2.0.0: Node.js/Fastify/Prisma/Zod → Python/FastAPI/SQLModel/Pydantic

TODOs:
- Create spec: admin-dashboard (009) — packages/admin is currently a stub
- Create spec: payment-integration (005) — no spec or code exists
- Create spec: vendor-portal-completion (012) — only login is implemented
- Create spec: event-driven-architecture — domain_events table + at-least-once delivery
- Create spec: analytics (010) — no spec exists
- Complete spec: user-portal-api-audit — design.md and tasks.md are missing

Next steps:
- Write ADR: "MCP Protocol Integration" documenting tool server selection rationale
- Write ADR: "Monetization Framework" documenting billing provider selection
- Update packages/agentic_event_orchestrator to register MCP tool servers in lifespan
-->

## Project Identity

**Name:** Event-AI — Agentic Event Orchestrator  
**Domain:** AI-powered event planning marketplace for Pakistan (weddings, mehndi, baraat, walima, corporate events, conferences, birthdays, parties)  
**Architecture:** Event-driven monorepo (uv + pnpm + Turborepo) — Python AI service + Python backend API + Next.js portals  

---

## Core Principles

### I. Monorepo-First Architecture

All code MUST live inside the `packages/` workspace. Each package is an isolated, independently deployable unit with its own dependencies, build, and test pipeline.

**Package boundaries are:**
| Package | Responsibility | Runtime |
|---|---|---|
| `packages/backend` | REST API, business logic, database | Python (FastAPI) |
| `packages/agentic_event_orchestrator` | AI agent service | Python (FastAPI) |
| `packages/user` | End-user portal | Next.js (App Router) |
| `packages/admin` | Admin portal | Next.js (App Router) |
| `packages/frontend` | Vendor portal | Next.js (App Router) |
| `packages/ui` | Shared UI component library | React |

**Rules:**
- Cross-package imports MUST go through defined API contracts (REST endpoints, shared types from `packages/ui`). Never import from one package's `src/` into another.
- Shared UI components belong in `packages/ui`. No duplication across portals.
- Infrastructure-level configs (Turborepo, pnpm workspace, Docker Compose, CI/CD) live at the repository root.

---

### II. Technology Stack Mandate (NON-NEGOTIABLE)

The following stack is the canonical choice. Deviations require an ADR with documented justification.

#### Backend API (`packages/backend`)
| Layer | Technology | Version |
|---|---|---|
| Runtime | Python | ≥ 3.12 |
| Framework | FastAPI | Latest |
| ORM | SQLModel (SQLAlchemy + Pydantic) | Latest |
| Database | **Neon DB (PostgreSQL)** | ≥ 15 with `pgvector` extension |
| DB Driver | `asyncpg` (async) | Latest |
| Validation | Pydantic | Latest |
| Auth | JWT (access + refresh tokens), bcrypt | — |
| Logging | Structlog (structured JSON) | — |
| Event Bus | FastAPI background tasks + in-process EventEmitter (or NATS JetStream when scaling) | — |
| Package Manager | **uv** | Latest |

#### AI Agent Service (`packages/agentic_event_orchestrator`)
| Layer | Technology |
|---|---|
| Runtime | Python ≥ 3.12 |
| Framework | FastAPI + Uvicorn |
| Agent SDK | OpenAI Agents SDK (`openai-agents`) |
| LLM Provider | Gemini via OpenAI-compatible endpoint |
| Package Manager | **uv** (NOT pip, NOT poetry) |
| Async | native `asyncio` (NO `nest_asyncio`) |
| ORM | SQLModel (SQLAlchemy + Pydantic) |
| DB Driver | `asyncpg` (async) via `create_async_engine` |
| Settings | Pydantic `BaseSettings` with `@lru_cache` |
| HTTP Client | `httpx.AsyncClient` (initialized in lifespan) |
| Streaming | `sse-starlette` (Server-Sent Events) |
| Vector Search | pgvector in Neon DB (unified storage) |
| Agentic RAG Framework | LangChain (strictly for doc processing/retrieval, NOT orchestration) |
| Agent Memory | Mem0 (for persistent cross-session augmented memory) |
| Testing | `pytest-asyncio`, `httpx`, `respx` (for LLM HTTP mocking) |
| DI | FastAPI `Depends()` for all shared resources |

#### Frontend Portals (`packages/user`, `packages/admin`, `packages/frontend`)
| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| Styling | Tailwind CSS + shadcn/ui |
| State | React Query (TanStack Query) |
| Auth | NextAuth.js |

#### Infrastructure
| Layer | Technology |
|---|---|
| Monorepo | Turborepo + pnpm workspaces |
| Database | **Neon Serverless PostgreSQL** (NOT Supabase, NOT local Postgres in prod) |
| Containerization | Docker (dev only) |
| CI/CD | GitHub Actions |

---

### III. Event-Driven Architecture (NON-NEGOTIABLE)

The platform uses an event-driven architecture (EDA) where services communicate through domain events rather than direct synchronous calls. This decouples the backend, AI service, and portals.

**Domain Events Taxonomy:**
| Event | Producer | Consumers |
|---|---|---|
| `event.created` | Backend | AI Service (auto-plan), Notification Service |
| `event.updated` | Backend | All portals (real-time update), AI Service |
| `event.status_changed` | Backend | All portals (real-time update), AI Service |
| `event.cancelled` | Backend | Vendor Portal, AI Service (re-plan), Email Service |
| `booking.created` | Backend | Vendor Portal (alert), AI Service (schedule update), Email Service |
| `booking.confirmed` | Backend | User Portal, Email Service, Scheduler |
| `booking.cancelled` | Backend | Vendor Portal, AI Service (re-plan), Email Service |
| `booking.completed` | Backend | User Portal, Email Service, Analytics Service |
| `vendor.registered` | Backend | Admin Portal (approval queue), AI Service (embedding generation) |
| `vendor.approved` | Backend | Vendor Portal, Email Service, AI Service (embed) |
| `vendor.rejected` | Backend | Vendor Portal, Email Service, AI Service (delete embed) |
| `vendor.suspended` | Backend | Vendor Portal, Email Service, AI Service (delete embed) |
| `payment.initiated` | Backend | Booking Service (status update) |
| `payment.received` | Backend | Booking Service (status update), Email Service, Analytics Service |
| `payment.failed` | Backend | User Portal (alert), Email Service |
| `payment.refunded` | Backend | User Portal (alert), Booking Service, Email Service |
| `ai.plan_generated` | AI Service | Backend (store plan), User Portal (display) |
| `ai.vendor_recommended` | AI Service | Backend (log recommendation) |
| `review.submitted` | Backend | AI Service (update vendor embeddings), Vendor Portal |
| `user.registered` | Backend | Email Service (welcome), Admin Portal |
| `user.email_verified` | Backend | Email Service (confirmation) |

**Implementation Rules:**
1. **Events are facts, not commands.** Events describe something that already happened (`booking.created`), never something that should happen (`create.booking`).
2. **Event envelope standard:**
   ```json
   {
     "eventId": "uuid",
     "eventType": "booking.created",
     "timestamp": "ISO-8601",
     "version": 1,
     "source": "backend",
     "correlationId": "request-trace-id",
     "data": { ... }
   }
   ```
3. **Phase 1 (current scale):** Use FastAPI background tasks + in-process `EventEmitter` for backend-internal events, and REST webhooks for backend → AI service communication.
4. **Phase 2 (scaling):** Migrate to **NATS JetStream** as the message broker when the platform requires multi-instance deployments. The event envelope format is broker-agnostic by design.
5. **At-least-once delivery.** All event consumers MUST be idempotent. Use `eventId` for deduplication.
6. **Event store.** Critical domain events (`booking.*`, `payment.*`, `event.*`) are persisted to an `domain_events` table for audit trail and replay capability.
7. **Real-time to frontends.** Use Server-Sent Events (SSE) or WebSockets from the backend to push events to the Next.js portals. Frontends subscribe to event streams, never poll.
8. **Dead letter handling.** Failed event processing is retried 3 times with exponential backoff, then moved to a dead-letter store for manual inspection.

**Anti-pattern enforcement:**
- ❌ Frontend polling the backend for status changes → ✅ Backend pushes events via SSE/WebSocket
- ❌ AI service directly mutating backend database → ✅ AI service emits events, backend handles persistence
- ❌ Synchronous chain: booking → payment → email → notification → response → ✅ Async event fan-out: booking emits event, consumers process independently

---

### IV. Relational Databases & PostgreSQL Standards

Neon Serverless Postgres is the single source of truth for all persistent data.

**Database Design & SQLModel Rules:**
1. **Async Engines Only**: Configure async database engines (`create_async_engine`) with proper pooling (`pool_pre_ping=True`, `pool_size`).
2. **Prevent N+1 Queries**: When retrieving related entities in SQLModel/SQLAlchemy, ALWAYS use eager loading strategies like `selectinload` to prevent N+1 query performance issues.
3. **Transaction Management**: Implement async CRUD operations using `AsyncSession` with explicit commit/flush boundaries and proper rollback error handling.
4. All database access goes through SQLModel.
5. Connection strings follow the Neon format (`DATABASE_URL` for pooling, `DIRECT_URL` for migrations/direct).
6. Every migration MUST be incremental, reversible, and explicitly handle JSONB or vector column setups.
7. Schema changes MUST be managed system-wide using Alembic.
---

### V. Test-First Development (NON-NEGOTIABLE)

All implementation MUST follow Test-Driven Development. No feature code is written before tests exist.

**Workflow (TDD for Agents):**
1. Write acceptance criteria as testable statements.
2. Write failing tests (Red) — use `respx` to mock external API and LLM dependencies.
3. Implement minimally to make tests pass (Green).
4. Refactor with tests green (Refactor).

**TDD Mandates for AI Service:**
- **Zero LLM API Calls During Testing**: ALL calls to Gemini/OpenAI must be mocked using `respx` HTTP mock routers. Tests MUST NOT incur LLM API costs or rely on external network availability.
- **Async Testing**: Use `pytest-asyncio` for all agent/tool tests, and `httpx` with `ASGITransport` for testing FastAPI endpoints directly without running a server.
- **Minimum Coverage**: Agent API and tool functions require 80%+ code coverage.

**Testing requirements by package:**

| Package | Framework | Minimum Coverage |
|---|---|---|
| `packages/backend` | pytest + httpx | 80% on services, 70% on routes |
| `packages/agentic_event_orchestrator` | pytest + httpx | 70% on tools, integration tests for agent flows |
| `packages/user`, `admin`, `frontend` | Jest + React Testing Library | 60% on components |

**Mandatory test types:**
- **Unit tests** — for every service function, tool function, utility
- **Integration tests** — for every API endpoint, every agent → tool chain
- **Contract tests** — when backend and AI service APIs change, contract tests must verify compatibility
- **E2E tests** — critical user flows (booking creation, event planning, vendor search)

---

### VI. API Contract Discipline

All inter-service communication uses strictly versioned, Pydantic-validated REST APIs.

**Rules:**
1. Every endpoint MUST have a Pydantic model for request body, query params, and path params.
2. ALL responses follow the standardized envelope:
   ```json
   { "success": true, "data": {}, "meta": {} }
   { "success": false, "error": { "code": "ERROR_CODE", "message": "..." } }
   ```
3. API versioning: all routes are prefixed with `/api/v1/`. Breaking changes require a new version (`/api/v2/`).
4. The AI service exposes its own endpoints under `/api/v1/ai/` proxied through the backend. The frontend NEVER calls the Python service directly.
5. Pagination follows: `?page=1&limit=20` returning `meta: { total, page, limit, pages }`.
6. Error codes MUST use the taxonomy: `AUTH_*`, `VALIDATION_*`, `NOT_FOUND_*`, `CONFLICT_*`, `INTERNAL_*`, `AI_*`, `BILLING_*`.

---

### VII. Augmented Memory & Agentic RAG Architecture

The AI Agent relies on robust Vector Database and Augmented Memory patterns (Agent Factory Best Practices). "Agentic RAG" means an agent orchestrates the retrieval process — planning queries, executing multi-step retrieval, and synthesising results — rather than a passive single-shot vector lookup.

1. **Strict Framework Separation:**
   - Use **LangChain** explicitly for document processing, chunking, and semantic retrieval chains (the retrieval layer of Agentic RAG).
   - Use **OpenAI Agents SDK** explicitly for agent orchestration, tool calling, and flow management. Do NOT use LangChain's agent orchestrators.
2. **Vector Stores:** Use pgvector in Neon DB for all semantic search and embedding storage to minimize infrastructure overhead and unify the persistence layer.
3. **Augmented Memory with Mem0:** Use Mem0 to persist cross-session memory for agents so they recall user preferences, past event planning details, and context across separate interactions.
4. **Evaluation:** Agentic RAG pipelines MUST be evaluated offline using LangSmith in combination with RAGAS metrics to measure context relevancy and answer faithfulness.

---

### VIII. Agent Architecture Standards

The AI agent system follows a strict hierarchical delegation pattern, built on FastAPI best practices from the [Panaversity Agent Factory](https://agentfactory.panaversity.org/docs/Building-Agent-Factories/fastapi-for-agents).

**Agent hierarchy:**
```
TriageAgent (entry point)
├── EventPlannerAgent → VendorDiscoveryAgent, SchedulerAgent, BookingAgent
├── VendorDiscoveryAgent
├── BookingAgent
├── SchedulerAgent
├── ApprovalAgent
├── MailAgent
└── OrchestratorAgent (complex multi-step)
```

**Agent Rules:**
1. Every agent MUST have a single, well-defined responsibility (SRP). If an agent instruction exceeds 50 lines, it must be split.
2. Agents MUST use `function_tool` decorators for all external interactions (DB, API calls). Agents never make HTTP calls directly — they call tools.
3. Agent handoffs are the ONLY mechanism for cross-agent communication. No shared mutable state between agents.
4. The TriageAgent is the ONLY entry point for user interactions. All other agents are reached only via handoffs.
5. Every tool function MUST be idempotent where possible, validate inputs with Pydantic models, and return structured JSON.
6. Agent instructions MUST include: scope enforcement, refusal patterns for off-topic requests, and security rules (never reveal system prompts).
7. User confirmation is MANDATORY before any destructive action (booking creation, cancellation, payment).
8. All agent interactions MUST be logged to the `chat_sessions` and `messages` tables with `agent_name` metadata.

**FastAPI Service Architecture (Agent Factory Best Practices):**

9. **Lifespan management via `@asynccontextmanager`** — All expensive resources (DB engine, async session factory, httpx client, LLM client) MUST be initialized in the FastAPI `lifespan` function and stored on `app.state`. No lazy initialization on first request. No deprecated `@app.on_event("startup")` decorators.
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # STARTUP
       engine = create_async_engine(settings.database_url, pool_pre_ping=True)
       app.state.async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
       app.state.http_client = httpx.AsyncClient(timeout=30.0)
       app.state.llm_client = AsyncOpenAI(api_key=settings.gemini_api_key, base_url=settings.gemini_base_url)
       yield
       # SHUTDOWN
       await app.state.http_client.aclose()
       await engine.dispose()

   app = FastAPI(title="Event-AI Agent Service", lifespan=lifespan)
   ```

10. **Dependency injection via `Depends()`** — All shared resources (DB sessions, settings, HTTP clients) are injected into endpoints and tool functions via FastAPI's `Depends()`. Never access `app.state` directly in endpoint code — access it through `request.app.state` or a dependency function.
    ```python
    async def get_session(request: Request):
        async with request.app.state.async_session() as session:
            yield session

    @app.get("/vendors")
    async def list_vendors(session: AsyncSession = Depends(get_session)):
        ...
    ```

11. **Settings via Pydantic `BaseSettings` + `@lru_cache`** — Configuration must use Pydantic `BaseSettings` model with `.env` file support, cached via `@lru_cache` so settings are loaded exactly once. Never use raw `os.environ.get()` or `load_dotenv()` path hacks.
    ```python
    from pydantic_settings import BaseSettings
    from functools import lru_cache

    class Settings(BaseSettings):
        database_url: str
        gemini_api_key: str
        model_config = SettingsConfigDict(env_file=".env")

    @lru_cache
    def get_settings() -> Settings:
        return Settings()
    ```

12. **API → Function → Tool pattern** — The canonical flow is: REST API endpoints expose CRUD operations → pure Python functions wrap the business logic → `@function_tool` decorators expose functions to agents. Tools are thin wrappers that call business logic functions.
    ```python
    # tools/vendor_tools.py (business logic)
    def search_vendors(category: str, city: str) -> list[dict]: ...

    # agents/tools.py (agent tool wrappers)
    @function_tool
    def tool_search_vendors(category: str, city: str) -> str:
        """Search for vendors by category and city."""
        results = search_vendors(category, city)
        return json.dumps(results)
    ```

13. **SSE streaming for agent responses** — Agent chat endpoints MUST offer a streaming variant using `sse-starlette`'s `EventSourceResponse`. Use `Runner.run_streamed()` for token-by-token delivery. Non-streaming endpoint uses `Runner.run()` for simple request/response.
    ```python
    @app.post("/agent/chat")
    async def chat(request: ChatRequest):
        result = await Runner.run(triage_agent, request.message)
        return {"response": result.final_output}

    @app.post("/agent/chat/stream")
    async def chat_stream(request: ChatRequest):
        return EventSourceResponse(agent_stream_generator(request.message))
    ```

14. **Tool function standards:**
    - Every `@function_tool` MUST have a clear docstring (it becomes the tool description for the LLM).
    - Parameters MUST have type hints (agents use these to generate calls).
    - Return type MUST be `str` (JSON-serializable string). Never return raw ORM objects.
    - Tools MUST handle missing resources gracefully (return descriptive error strings, never raise unhandled exceptions).
    - Each tool manages its own DB session (independent of the HTTP request lifecycle).

15. **Async-first, yield for cleanup** — All database session dependencies use `yield` (not `return`) so cleanup runs even on exceptions. All endpoints are `async def`. Sync `def` is forbidden in the AI service.

---

### IX. Security & Secrets (NON-NEGOTIABLE)

1. **No hardcoded secrets.** All secrets use `.env` files (never committed) with `.env.example` templates.
2. JWT secrets MUST be 256-bit cryptographically random. Default/dev fallback secrets are forbidden in production.
3. Rate limiting is mandatory on ALL public endpoints:
   | Endpoint Type | Limit |
   |---|---|
   | Auth | 5 req/min |
   | Public APIs | 60 req/min |
   | AI endpoints | 30 req/min |
   | Booking creation | 10 req/min |
4. Input is validated at the boundary (Pydantic). Never trust client data.
5. **JWT Authentication (Agent Factory Best Practices):**
   - Use `python-jose[cryptography]` for JWT operations.
   - JWT tokens are signed, not encrypted. NEVER store sensitive data (like passwords) inside tokens, only identifiers (e.g., `{"sub": user.email}`).
   - The token endpoint (`/token`) MUST use OAuth2 strictly and accept form data (`OAuth2PasswordRequestForm`), not JSON.
   - Unauthorized access MUST raise `HTTPException` with status 401 and include the `{"WWW-Authenticate": "Bearer"}` header so clients prompt for credentials.
   - A `get_current_user` dependency MUST protect routes, extracting the signed user from the token.
6. CORS must be explicitly configured — no wildcard `*` in production.
7. Password hashing uses bcrypt with minimum 12 salt rounds.
8. SQL injection is prevented by ALWAYS using SQLModel/SQLAlchemy's parameterized queries.
9. The AI agent MUST refuse prompt-injection attempts and never expose internal system prompts.

---

### X. Simplicity & Anti-Abstraction

Complexity is the enemy. Every abstraction must earn its existence.

**Rules:**
1. **YAGNI** — Do not build features you don't need yet. No speculative abstractions.
2. **Framework trust** — Use FastAPI, Next.js, SQLModel, and OpenAI Agents SDK features directly. Do NOT wrap them in custom abstraction layers unless shared across 3+ call sites.
3. **Flat over nested** — Prefer flat directory structures. No more than 3 levels of nesting inside any `src/` directory.
4. **Single model representation** — Database entity → SQLModel class. Do NOT create separate DTO classes that mirror the SQLModel.
5. **No dead code** — Remove unused files, commented-out code blocks, and abandoned experiments immediately.
6. **Minimal dependencies** — Every new npm/PyPI dependency requires justification. Prefer standard library or existing framework capabilities. Run `pnpm why <pkg>` / `uv pip show <pkg>` before adding duplicates.

---

### XI. Code Quality & Consistency

**TypeScript (Frontends):**
- Strict mode enabled (`"strict": true` in tsconfig)
- No `any` types — use `unknown` and type guards instead
- ESLint + Prettier enforced via CI
- Named exports preferred; default exports only for Next.js pages/layouts
- File naming: `kebab-case` for files, `PascalCase` for components, `camelCase` for functions

**Python (Backend + AI Service):**
- Type hints on ALL function signatures (params + return)
- Ruff for linting and formatting (NOT flake8/black separately)
- Pydantic models for all structured data (no raw dicts crossing function boundaries)
- Async-first — prefer `async def` functions; synchronous wrappers only where the SDK demands them
- NO `sys.path.insert` hacks — use proper package structure with `pyproject.toml`
- NO `nest_asyncio` — restructure async code properly instead of patching the event loop

**SQLModel Schema:**
- All models use `__tablename__` to snake_case table names
- Fields use explicit `Field()` attributes where needed
- All datetime fields use timezone-aware types with `default_factory=datetime.utcnow`

---

### XII. MCP Protocol Integration

The AI agent service uses the Model Context Protocol (MCP) to give agents structured, tool-based access to external context sources — database state, logs, file system, and IDE context — without requiring bespoke APIs for each source.

**What MCP is for in this project:**
- Giving agents read access to live database state (vendor records, booking status, event data) via MCP tool servers rather than raw SQL in agent instructions.
- Exposing structured log queries so agents can reason about recent errors or system state.
- Enabling future IDE-context tools (e.g., reading spec files, referencing code) for developer-facing agents.

**MCP Architecture Rules:**

1. **MCP servers are registered in the FastAPI lifespan** — All MCP tool servers MUST be initialized in the `lifespan` function and stored on `app.state.mcp_servers`. No lazy initialization.
2. **MCP tools follow the same `@function_tool` pattern** — MCP-backed tools are wrapped with `@function_tool` decorators and exposed to agents through the standard tool registry. Agents MUST NOT call MCP servers directly.
3. **MCP servers are read-only by default** — MCP tool servers used by agents MUST expose read-only operations. Write operations go through the backend REST API, not MCP.
4. **MCP configuration via Settings** — MCP server URLs, API keys, and transport types are managed through the `Settings` object (`Pydantic BaseSettings + @lru_cache`). No hardcoded MCP endpoints.
5. **MCP transport selection:**
   - Use `stdio` transport for local/in-process tool servers (dev and testing).
   - Use `SSE` (HTTP + Server-Sent Events) transport for remote MCP servers in production.
   - Use `streamable-http` transport when the MCP server supports it and bidirectional streaming is needed.
6. **Zero MCP calls in unit tests** — MCP server calls MUST be mocked in tests using `respx` (for HTTP transports) or mock subprocess (for stdio). Tests MUST NOT connect to real MCP servers.
7. **MCP tool naming convention** — MCP-backed tools MUST be prefixed with `mcp__` to distinguish them from direct function tools (e.g., `mcp__db__get_vendor`, `mcp__logs__query_errors`).
8. **Graceful degradation** — If an MCP server is unavailable, the agent MUST fall back to a REST API call or return a structured error string. MCP unavailability MUST NOT crash the agent.

**Approved MCP tool servers for this project:**
| Server | Transport | Purpose |
|---|---|---|
| `mcp-server-postgres` (or equivalent) | stdio / SSE | Read-only DB queries for agent context |
| Custom `event-ai-logs` server | SSE | Structured log queries for debugging agents |
| Future: `mcp-server-filesystem` | stdio | Spec/doc file reading for developer agents |

**MCP Anti-patterns (see Anti-Patterns section for full list):**
- ❌ Agents calling MCP servers directly without `@function_tool` wrapper
- ❌ MCP tools performing write operations (INSERT/UPDATE/DELETE)
- ❌ Hardcoded MCP server URLs in agent instructions
- ❌ Real MCP server connections in test suites

---

### XIII. Monetization & Usage Framework

Event-AI is a commercial platform. All AI-powered features MUST be metered and gated behind a usage framework so that costs are recoverable and the platform is sustainable.

**Monetization Principles:**

1. **Every AI call is metered.** All calls to Gemini, embedding generation, and agent executions MUST be logged to a `usage_events` table with: `user_id`, `event_type` (e.g., `ai_chat_message`, `embedding_generated`, `event_plan_created`), `tokens_used`, `cost_usd`, `timestamp`, `metadata` (JSONB).
2. **Subscription plans gate features.** The platform supports tiered plans. Feature access is checked at the API boundary via a `require_plan(min_plan)` dependency — never inside business logic.
3. **Usage limits are enforced server-side.** Client-side plan checks are for UX only. The backend MUST enforce limits independently.
4. **Billing is decoupled from business logic.** Payment processing (Stripe or equivalent) communicates via webhooks that emit `payment.*` domain events. Business logic reacts to events, never calls the billing provider directly.
5. **Free tier exists.** Unauthenticated and free-tier users can access public vendor search and browse events. AI planning, booking creation, and messaging require at minimum a free registered account.

**Subscription Plan Tiers (initial):**
| Plan | AI Chat Messages/mo | Event Plans/mo | Vendor Recommendations/mo | Price |
|---|---|---|---|---|
| Free | 10 | 1 | 20 | PKR 0 |
| Starter | 100 | 5 | 200 | PKR 999/mo |
| Pro | Unlimited | Unlimited | Unlimited | PKR 2,999/mo |
| Enterprise | Unlimited | Unlimited | Unlimited + priority | Custom |

**Usage Metering Rules:**

6. **`UsageEvent` SQLModel** — A `usage_events` table MUST exist with fields: `id` (UUID PK), `user_id` (UUID FK), `plan_id` (string), `event_type` (Enum), `tokens_used` (int, nullable), `cost_usd` (Decimal, nullable), `metadata` (JSONB), `created_at` (timezone-aware datetime).
7. **Metering is async** — Usage logging MUST be done as a FastAPI background task. It MUST NOT block the API response.
8. **Usage aggregation** — A `GET /api/v1/users/me/usage` endpoint MUST return the current period's usage summary so portals can display quota progress.
9. **Overage handling** — When a user exceeds their plan limit, the API MUST return HTTP 402 with error code `BILLING_QUOTA_EXCEEDED` and a `meta.upgrade_url` field pointing to the upgrade page.

**Billing Integration Rules:**

10. **Stripe is the canonical payment provider** (or equivalent for Pakistan — e.g., JazzCash, EasyPaisa for local payments). The provider is configured via `Settings.payment_provider`.
11. **Webhook-first** — All billing state changes (subscription created, payment received, subscription cancelled) arrive via webhooks and are processed as domain events. The backend NEVER polls the billing provider.
12. **Idempotent webhook handlers** — Webhook handlers MUST use the billing provider's event ID for deduplication before processing.
13. **No payment data in the database** — Card numbers, CVVs, and raw payment tokens MUST NEVER be stored. Store only billing provider customer IDs and subscription IDs.
14. **`.env.example` MUST include** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_STARTER`, `STRIPE_PRICE_ID_PRO` (or equivalent provider keys).

---

## Anti-Patterns (BANNED PRACTICES)

The following patterns found in the existing codebase are explicitly forbidden going forward:

| ❌ Bad Practice | ✅ Required Practice |
|---|---|
| `sys.path.insert(0, ...)` hacks | Proper Python package with `pyproject.toml` entry points |
| `nest_asyncio.apply()` | Proper async architecture; use `asyncio.run()` at entry point |
| `from dotenv import load_dotenv` at module scope with path hacks | Use `python-dotenv` or `uv run` with `.env` file; load once at entry point |
| `import sys, os` (multiple imports on one line) | One import per line per PEP 8 |
| Mixed `npm` and `pnpm` commands in scripts | Use `pnpm` exclusively |
| Dummy API keys (`sk-dummy...`) with runtime cleanup | Proper environment variable management; never set dummy keys |
| `psycopg2-binary` for production | Use `asyncpg` for async code or `psycopg[binary]` v3 |
| `chainlit` dependency in the orchestrator | Use the FastAPI server directly; Chainlit is for prototyping only |
| Docker Compose referencing Supabase URLs | Use Neon DB connection strings; no Supabase dependency |
| Agent `clone()` to update handoffs after definition | Define agents in correct order; use forward-reference pattern or builder |
| Raw string for senderType (`'vendor'`, `'client'`, `'system'`) | Use a Python `Enum` class and SQLModel `sa_column(Enum(...))` |
| `@default(now()) @updatedAt` without logic equivalent | Using SQLAlchemy's `onupdate` or equivalent ensures consistency |
| Hardcoded approval limits in agent instructions | Store config in database or `.env`; agents read at runtime |
| `Unsupported("vector(1536)")` without migration wrapper | Use a proper Alembic pgvector migration script |
| `@app.on_event("startup")` / `@app.on_event("shutdown")` | Use `@asynccontextmanager` lifespan pattern |
| Accessing `app.state` directly in endpoints | Access via `request.app.state` or a `Depends()` function |
| `os.environ.get()` / `load_dotenv()` scattered in modules | Pydantic `BaseSettings` + `@lru_cache` at a single config entry point |
| Tool functions without docstrings | Every `@function_tool` MUST have a docstring (becomes LLM tool description) |
| Returning ORM objects from tools | Return JSON-serializable `str` or `dict` from all tool functions |
| `Runner.run_sync()` in async context | Use `await Runner.run()` (async) or `Runner.run_streamed()` for streaming |
| Lazy-loading DB connections on first request | Initialize in lifespan; store on `app.state`; no cold-start penalties |
| Global mutable state outside `app.state` | All shared state goes through `app.state` set in lifespan |
| `POST /token` expecting JSON body | The OAuth2 token endpoint MUST use form data (`OAuth2PasswordRequestForm`) |
| Raising 401 without `WWW-Authenticate` header | Include `headers={"WWW-Authenticate": "Bearer"}` in the HTTP 401 response |
| Storing passwords in JWT payload | Never store sensitive data in JWT payload; anyone can decode it |
| Committing unmocked LLM tests | Zero LLM API calls allowed in tests. Use `respx` to mock LLM HTTP endpoints. |
| Making N+1 DB Queries via SQLModel | Always use eager loading (e.g. `selectinload`) when fetching hierarchical data. |
| Using LangChain for agent orchestration | LangChain is for document processing/Agentic RAG retrieval only. Use Agents SDK for orchestration. |
| Agents calling MCP servers directly | Wrap all MCP calls in `@function_tool` decorators; agents call tools, not servers |
| MCP tools performing write operations | MCP tools are read-only; writes go through the backend REST API |
| Hardcoded MCP server URLs in agent code | All MCP endpoints configured via `Settings` object |
| Real MCP server connections in tests | Mock MCP calls with `respx` (HTTP) or mock subprocess (stdio) |
| Logging AI usage synchronously in request path | Use FastAPI `BackgroundTask` for all `usage_events` inserts |
| Enforcing plan limits only on the frontend | Backend MUST enforce limits via `require_plan()` dependency on every gated endpoint |
| Storing card numbers or raw payment tokens | Store only billing provider customer/subscription IDs; never raw payment data |
| Polling the billing provider for subscription state | Use webhooks exclusively; process as domain events |
| Calling billing provider directly from business logic | Business logic reacts to `payment.*` domain events; never calls Stripe/JazzCash directly |
| Returning HTTP 200 when quota is exceeded | Return HTTP 402 with `BILLING_QUOTA_EXCEEDED` error code and `meta.upgrade_url` |

---

## Development Workflow

### Branch Strategy
- `main` — production-ready, protected
- `develop` — integration branch for all feature work
- `feature/<name>` — individual feature branches from `develop`
- `hotfix/<name>` — urgent fixes from `main`

### Commit Convention
Follow Conventional Commits: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`
- Scopes: `backend`, `ai`, `user`, `admin`, `vendor`, `ui`, `infra`, `db`, `billing`
- Example: `feat(ai): add vendor recommendation caching tool`

### Code Review Requirements
1. All PRs require at least 1 approval
2. CI must pass (lint, type-check, tests)
3. No decrease in test coverage
4. Database migration PRs require a separate reviewer

### Definition of Done
A feature is "done" when:
- [ ] Tests written and passing (unit + integration)
- [ ] Pydantic models defined for all inputs/outputs
- [ ] Error handling covers all failure paths
- [ ] Rate limiting configured for new endpoints
- [ ] API documentation updated
- [ ] No lint warnings or type errors
- [ ] Migration tested in Neon branch (if DB changes)
- [ ] Domain events emitted for all state changes (if applicable)
- [ ] Usage metering added for all AI-powered operations (if applicable)
- [ ] MCP tool wrappers added if new agent context sources are introduced
- [ ] Plan gating enforced via `require_plan()` for any feature behind a subscription tier

---

## Performance Standards

| Metric | Target |
|---|---|
| API p95 latency | < 200ms (non-AI endpoints) |
| AI agent response | < 10s for single-tool calls |
| MCP tool call latency | < 100ms (read-only DB queries via MCP) |
| Database query time | < 50ms for indexed queries |
| Frontend LCP | < 2.5s |
| Frontend FID | < 100ms |
| Bundle size (per portal) | < 250KB gzipped JS |

---

## Governance

1. This constitution supersedes all other development guidelines in the project. If CLAUDE.md, README.md, or any other document conflicts with this constitution, the constitution wins.
2. Amendments to this constitution require:
   - A written proposal with rationale
   - An ADR documenting the change and its impact
   - Review and approval before implementation
3. All code reviews MUST verify constitutional compliance. Non-compliant code is not mergeable.
4. The Anti-Patterns section is a living document — add newly discovered bad practices as they are identified.
5. See CLAUDE.md for runtime AI agent development guidance that implements these principles.

**Version**: 2.2.0 | **Ratified**: 2026-04-07 | **Last Amended**: 2026-05-01
