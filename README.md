# Event-AI — Agentic Event Orchestrator

> AI-powered event planning marketplace for Pakistan — weddings, mehndi, baraat, walima, corporate events, conferences, birthdays, and parties.

---

## Overview

Event-AI connects clients with verified vendors through an intelligent marketplace. The platform uses AI agents to auto-plan events, recommend vendors, and manage bookings — all backed by a production-grade FastAPI backend with real-time notifications, semantic search, and a multi-layer prompt injection firewall.

---

## Architecture

```
packages/
├── backend/                     # FastAPI REST API (Python + uv)
├── frontend/                    # Vendor portal (Next.js 15)
├── user/                        # Customer portal (Next.js 15) — SSE chat UI
├── admin/                       # Admin portal (Next.js 15)
├── agentic_event_orchestrator/  # AI agent service (FastAPI + OpenAI Agents SDK)
└── ui/                          # Shared component library
```

**Stack:**
- **Backend:** Python 3.12+ · FastAPI · SQLModel · asyncpg · Alembic · Structlog · uv
- **Database:** Neon Serverless PostgreSQL · pgvector (semantic search)
- **Auth:** Custom JWT (HS256) · Google OAuth2 · bcrypt · httpOnly cookies
- **Frontend:** Next.js 15 · TypeScript (strict) · Tailwind CSS · shadcn/ui · React Query
- **AI:** OpenAI Agents SDK · Gemini via LiteLLM · Mem0 · SSE streaming · 7-layer injection firewall · pgvector RAG

### Port Map

| Service | Port |
|---------|------|
| Backend API | 5000 (dev) / 5000 (Docker) |
| User portal | 3003 (dev) / 3000 (Docker) |
| Vendor portal | 3002 (dev) / 3001 (Docker) |
| Admin portal | 3004 |
| AI orchestrator | 8000 |

---

## Project Status

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Database Setup | ✅ Complete |
| 1 | FastAPI JWT Auth | ✅ Complete |
| 1 | User Auth + Google OAuth | ✅ Complete |
| 2 | Vendor Marketplace | ✅ Complete |
| 2 | Event Management | ✅ Complete |
| 3 | Booking System | ✅ Complete |
| 3 | Notification System | ✅ Complete |
| 3 | Real-Time SSE | ✅ Complete |
| 4 | **RAG & Semantic Search** | ✅ **Complete** |
| 4 | **AI Agent Chat** | ✅ **Complete** (core + security) |
| 4 | Admin Dashboard | ✅ Complete |
| 5 | AI Agent Security Hardening | 🔄 In Progress (tasks 5e–5g + tests) |
| 5 | Notification System Polish | 🔄 In Progress (tasks 4–10) |

### What's Remaining

**AI Agent Security Hardening** (`ai-agent-chat` spec, tasks 5e–5g + 13–17):
- Agent instruction hardening + LlamaFirewall AlignmentCheck per-handoff validator
- TruLens RAG faithfulness evaluation
- CI security testing with Promptfoo + Garak
- Comprehensive unit + integration test suites for tools, guardrails, and chat endpoints

**Notification System Polish** (`notification-system` spec, tasks 4–10):
- Parent task status sync (all sub-tasks are implemented)
- Rate limiting decorator verification
- SSE evict-oldest overflow strategy

---

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [pnpm](https://pnpm.io/) — Node package manager
- Neon DB account (or local PostgreSQL with pgvector)
- Google Cloud Console project (for OAuth)

### 1. Install dependencies

```bash
pnpm install
cd packages/backend && uv sync
cd packages/agentic_event_orchestrator && uv sync
```

### 2. Configure environment

```bash
cp packages/backend/.env.example packages/backend/.env
cp packages/agentic_event_orchestrator/.env.example packages/agentic_event_orchestrator/.env
# Fill in DATABASE_URL, JWT_SECRET_KEY, GEMINI_API_KEY, etc.
```

### 3. Start database and run migrations

```bash
pnpm db:up          # start Postgres (Docker)
pnpm db:migrate     # apply all migrations
```

### 4. Start all services

```bash
pnpm dev            # starts all packages concurrently
```

Or start individually:

```bash
pnpm dev:backend    # FastAPI backend → http://localhost:5000
pnpm dev:user       # Customer portal → http://localhost:3003
pnpm dev:frontend   # Vendor portal   → http://localhost:3002
pnpm dev:admin      # Admin portal    → http://localhost:3004
```

Start the AI service separately:

```bash
cd packages/agentic_event_orchestrator
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Running Tests

```bash
cd packages/backend
uv run pytest                          # all tests (241 currently passing)
uv run pytest tests/test_event_routes.py -v  # specific file
uv run pytest -k "test_semantic" -v    # by name pattern
uv run pytest --cov=src --cov-report=term    # with coverage
```

---

## API Reference

All endpoints follow the standard response envelope:

```json
{ "success": true,  "data": { ... }, "meta": {} }
{ "success": false, "error": { "code": "ERROR_CODE", "message": "..." } }
```

Base URL: `http://localhost:5000/api/v1`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register with email/password → JWT pair |
| `POST` | `/auth/login` | OAuth2 form-encoded login |
| `POST` | `/users/login` | JSON login (frontend portal) |
| `GET`  | `/auth/me` | Authenticated user profile |
| `POST` | `/auth/refresh` | Rotate refresh token |
| `POST` | `/auth/logout` | Revoke refresh token |
| `POST` | `/auth/password-reset-request` | Request reset token |
| `POST` | `/auth/password-reset-confirm` | Confirm new password |
| `GET`  | `/auth/google` | Initiate Google OAuth2 flow |
| `GET`  | `/auth/google/callback` | Google OAuth2 callback |

### Vendors

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/vendors/register` | Register as vendor (triggers approval) |
| `GET`  | `/vendors/profile/me` | Get own vendor profile |
| `PUT`  | `/vendors/profile/me` | Update vendor profile |
| `DELETE` | `/vendors/profile/me` | Soft-delete (suspend) profile |
| `GET`  | `/vendors/me/bookings` | List vendor's bookings |
| `PATCH` | `/vendors/me/bookings/{id}/status` | Confirm or reject booking |
| `GET`  | `/public_vendors/` | Public vendor search (trigram + ILIKE) |
| `GET`  | `/public_vendors/suggestions` | Autocomplete suggestions |
| `GET`  | `/public_vendors/semantic` | Semantic (vector) search via Gemini embeddings |
| `GET`  | `/public_vendors/search?mode=keyword\|semantic\|hybrid` | Unified search (default: hybrid) |
| `GET`  | `/public_vendors/{id}` | Public vendor profile |
| `GET`  | `/categories/` | List event categories |

### Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/events/` | Create event (status=PLANNED) |
| `GET`  | `/events/` | List own events (paginated, status filter) |
| `GET`  | `/events/{id}` | Get single event |
| `PUT`  | `/events/{id}` | Update event fields |
| `DELETE` | `/events/{id}` | Cancel event |
| `PATCH` | `/events/{id}/status` | Explicit status transition |
| `POST` | `/events/{id}/duplicate` | Clone event (status=DRAFT) |
| `GET`  | `/events/{id}/bookings` | List bookings for event |
| `GET`  | `/events/admin/all` | Admin: all events with filters |
| `GET`  | `/events/types` | List event types |

**Event status machine:** `draft → planned → active → completed`, any → `canceled`

### Bookings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/bookings/` | Create booking (locks availability slot) |
| `GET`  | `/bookings/` | List own bookings (paginated) |
| `GET`  | `/bookings/{id}` | Get single booking |
| `PATCH` | `/bookings/{id}/status` | Update status (state machine) |
| `PATCH` | `/bookings/{id}/cancel` | Cancel + release slot |
| `GET`  | `/bookings/availability` | Check vendor/service/date availability |
| `POST` | `/bookings/{id}/messages` | Send booking message |
| `GET`  | `/bookings/{id}/messages` | List booking messages |

**Booking status machine:** `pending → confirmed|rejected|cancelled`, `confirmed → in_progress|cancelled`, `in_progress → completed|no_show`

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/notifications/` | List notifications (paginated) |
| `GET`  | `/notifications/unread-count` | Unread count |
| `PATCH` | `/notifications/read-all` | Mark all as read |
| `DELETE` | `/notifications/read` | Delete all read notifications |
| `PATCH` | `/notifications/{id}/read` | Mark single as read |
| `DELETE` | `/notifications/{id}` | Delete single notification |
| `GET`  | `/notifications/preferences` | List notification preferences |
| `PUT`  | `/notifications/preferences/{type}` | Upsert preference |
| `GET`  | `/sse/stream` | Real-time SSE stream |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/admin/stats` | Platform stats (users, vendors, bookings, revenue) |
| `GET`  | `/admin/vendors` | Paginated vendor list with filters |
| `PATCH` | `/admin/vendors/{id}/status` | Approve / reject / suspend vendor |
| `GET`  | `/admin/users` | Paginated user list with filters |
| `POST` | `/admin/embeddings/backfill` | Trigger background embedding backfill |
| `GET`  | `/admin/chat/sessions` | Paginated AI chat session log |
| `GET`  | `/admin/chat/sessions/{id}/messages` | Messages for a session |
| `GET`  | `/admin/chat/feedback/stats` | Aggregate feedback per agent |

### AI Agent (port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ai/chat` | Non-streaming chat |
| `POST` | `/api/v1/ai/chat/stream` | SSE token-by-token streaming |
| `POST` | `/api/v1/ai/feedback` | Thumbs up/down per message |
| `DELETE` | `/api/v1/ai/memory/{user_id}` | GDPR right-to-forget |

---

## RAG & Semantic Search

Vendor profiles are embedded using Gemini `text-embedding-004` (768 dimensions) and stored in pgvector. Embeddings are automatically created/updated when vendors are approved and deleted when they are rejected or suspended.

**Search modes** (via `GET /public_vendors/search?mode=...`):

| Mode | Description |
|------|-------------|
| `keyword` | Trigram + ILIKE text search (no embedding required) |
| `semantic` | pgvector cosine similarity via Gemini embeddings |
| `hybrid` | Weighted combination: 30% trigram + 70% semantic (default) |

**Admin backfill** — trigger a background re-embedding of all active vendors:

```bash
curl -X POST http://localhost:3001/api/v1/admin/embeddings/backfill \
  -H "Authorization: Bearer <admin_token>"
```

Or for a single vendor:

```bash
curl -X POST http://localhost:3001/api/v1/admin/embeddings/backfill \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"vendor_id": "<uuid>"}'
```

---

## AI Agent Chat

The AI service (`packages/agentic_event_orchestrator`) is a production-grade FastAPI application with a multi-agent pipeline and 7-layer security stack.

### Agent Pipeline

```
User request (HTTP/SSE)
       ↓
  TriageAgent          ← sole entry point; classifies intent
       ↓
  EventPlannerAgent  ←→  VendorDiscoveryAgent
                              ↓
                        BookingAgent
                              ↓
                        OrchestratorAgent
```

Built with OpenAI Agents SDK + Gemini via LiteLLM (`gemini/gemini-3-flash-preview`).

### Security Stack

- **Layer 1:** YAML blocklist exact match
- **Layer 2:** Regex patterns (6 threat categories: DIRECT_INJECTION, SYSTEM_PROMPT_EXTRACTION, ROLE_ESCALATION, INDIRECT_INJECTION, CONTEXT_OVERFLOW, TOOL_ABUSE)
- **Layer 3:** Heuristics (char density, token repetition, homoglyphs, zero-width chars)
- **Sandwich defense:** Canary token injection + MINJA protection on history turns
- **OutputLeakDetector:** Canary token + stack trace + internal tool name detection
- **SDK-native guardrails:** `@input_guardrail` (blocking) + `@output_guardrail`
- **Mem0:** Per-user persistent memory across sessions

### Chat Features

- Token-by-token SSE streaming with agent badge updates
- Thumbs up/down feedback per message
- Session persistence via `localStorage`
- PII redaction on output (email, phone, CNIC patterns)
- Rate limiting: 30 req/min per user

---

## Environment Variables

### `packages/backend/.env`

```env
# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
DIRECT_URL=postgresql://user:pass@host/db?sslmode=require  # for migrations

# JWT
JWT_SECRET_KEY=<256-bit random — generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth2
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=http://localhost:5000/api/v1/auth/google/callback

# Frontend
FRONTEND_URL=http://localhost:3003
CORS_ORIGINS=http://localhost:3002,http://localhost:3003,http://localhost:3004,http://localhost:3000

# Gemini (for embeddings)
GEMINI_API_KEY=<from Google AI Studio>

# Seed script (optional)
SEED_ADMIN_EMAIL=admin@eventai.pk
SEED_ADMIN_PASSWORD=<min 12 chars>
```

### `packages/agentic_event_orchestrator/.env`

```env
GEMINI_API_KEY=<from Google AI Studio>
GEMINI_MODEL=gemini/gemini-3-flash-preview
AI_SERVICE_API_KEY=<32+ byte random token>
SERVICE_SECRET=<must match AGENT_SERVICE_SECRET in backend .env>
BACKEND_API_URL=http://localhost:3001/api/v1
CORS_ORIGINS=http://localhost:3003
MEM0_API_KEY=<from mem0.ai>
```

---

## Database Migrations

```bash
cd packages/backend

# Apply all pending migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Rollback one step
uv run alembic downgrade -1

# View migration history
uv run alembic history --verbose
```

**Note:** pgvector must be enabled before the first migration:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Key Commands

```bash
# Install all dependencies
pnpm install
cd packages/backend && uv sync
cd packages/agentic_event_orchestrator && uv sync

# Database lifecycle
pnpm db:up            # start Postgres (Docker)
pnpm db:down          # stop Postgres
pnpm db:migrate       # apply migrations
pnpm db:migrate:dev   # apply migrations (dev)
pnpm db:studio        # open DB GUI
pnpm db:reset         # wipe and reseed local DB

# Code quality
pnpm lint
pnpm format
pnpm typecheck
cd packages/backend && uv run pytest
```

---

## Google OAuth2 Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add Authorized redirect URI: `http://localhost:5000/api/v1/auth/google/callback`
4. Copy Client ID and Client Secret to `packages/backend/.env`

---

## Project Constitution

The platform follows a strict [constitution](.specify/memory/constitution.md) that governs all development decisions:

- **Package manager:** `uv` for Python, `pnpm` for Node — no `pip`, no `npm`
- **Response envelope:** All API responses use `{"success", "data/error", "meta"}`
- **Error codes:** `AUTH_*`, `VALIDATION_*`, `NOT_FOUND_*`, `CONFLICT_*`, `INTERNAL_*`
- **No scattered config:** All settings via Pydantic `BaseSettings` + `@lru_cache`
- **Async-first:** All DB operations use `AsyncSession` + `asyncpg`
- **Structured logging:** Structlog JSON throughout — no `print()`
- **Event-driven:** Domain events persisted to `domain_events` table via event bus
- **TDD:** Tests written alongside implementation — zero real LLM/MCP calls in tests

---

## Contributing

```bash
# Branch naming
feature/<name>    # new features
fix/<name>        # bug fixes
hotfix/<name>     # urgent production fixes

# Commit convention (Conventional Commits)
feat(backend): add semantic search endpoint
fix(auth): handle expired Google OAuth state token
test(events): add duplicate event integration tests
```

PRs target `develop`, never `main` directly. All CI checks (lint, typecheck, pytest) must pass before merge.
