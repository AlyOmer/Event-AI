# Event-AI — Agentic Event Orchestrator

> AI-powered event planning marketplace for Pakistan — weddings, mehndi, baraat, walima, corporate events, conferences, birthdays, and parties.

---

## Overview

Event-AI connects clients with verified vendors through an intelligent marketplace. The platform uses AI agents to auto-plan events, recommend vendors, and manage bookings — all backed by a production-grade FastAPI backend with real-time notifications and semantic search.

---

## Architecture

```
packages/
├── backend/                     # FastAPI REST API (Python + uv)
├── frontend/                    # Vendor portal (Next.js)
├── user/                        # Customer portal (Next.js) — SSE chat UI
├── admin/                       # Admin portal (Next.js — planned)
├── agentic_event_orchestrator/  # AI agent service (FastAPI + OpenAI Agents SDK)
└── ui/                          # Shared component library (planned)
```

**Stack:**
- **Backend:** Python 3.13 · FastAPI · SQLModel · asyncpg · Alembic · Structlog · uv (port 5000)
- **Database:** Neon Serverless PostgreSQL (pgvector enabled)
- **Auth:** JWT (HS256) · Google OAuth2 · bcrypt
- **Frontend:** Next.js 14 · Tailwind CSS · Zustand · Axios
- **AI:** OpenAI Agents SDK · Gemini 2.5 Flash · Mem0 · sklearn · SSE streaming · 7-layer injection firewall

---

## Docker

```bash
# Production — build and start both services
docker compose up --build

# Development — hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Backend only
docker compose up backend --build

# Run migrations inside container
docker compose exec backend alembic upgrade head

# Seed database
docker compose exec backend \
  sh -c "SEED_ADMIN_EMAIL=admin@eventai.pk SEED_ADMIN_PASSWORD=AdminPass123! \
         python -m src.scripts.seed"
```

**Services:**
- Backend → `http://localhost:5000`
- Frontend → `http://localhost:3001`

**Image sizes (approximate):**
- Backend: ~120MB (`python:3.13-slim` + venv, no build tools)
- Frontend: ~80MB (`node:20-alpine` + Next.js standalone output)

---

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [pnpm](https://pnpm.io/) — Node package manager
- Neon DB account (or local PostgreSQL)
- Google Cloud Console project (for OAuth)

### Backend

```bash
cd packages/backend

# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, JWT_SECRET_KEY, GOOGLE_CLIENT_ID, etc.

# Run database migrations
uv run alembic upgrade head

# Seed initial data (admin user + event categories)
SEED_ADMIN_EMAIL=admin@eventai.pk SEED_ADMIN_PASSWORD=AdminPass123! \
  uv run python -m src.scripts.seed

# Start the server (port 5000)
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
```

### AI Agent Service

```bash
cd packages/agentic_event_orchestrator

# Install dependencies
uv sync

# Configure environment (copy from .env.example)
# Required: GEMINI_API_KEY, DATABASE_URL, APP_DATABASE_URL

# Run database migrations (creates ai schema + 4 tables)
uv run alembic upgrade head

# Start the AI service (port 8000)
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Customer Portal)

```bash
cd packages/user
pnpm install
# Set AI_SERVICE_URL=http://localhost:8000 in .env
pnpm dev
# → http://localhost:3000
# Chat at http://localhost:3000/chat
```

### Frontend (Vendor Portal)

```bash
cd packages/frontend

# Install dependencies
pnpm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1" > .env

# Start dev server
pnpm dev
# → http://localhost:3001
```

### Running Tests

```bash
cd packages/backend
uv run pytest -v                              # all tests
uv run pytest tests/test_event_routes.py -v  # specific file
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
| `POST` | `/auth/login` | OAuth2 form-encoded login (Swagger UI) |
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
| `GET`  | `/sse/stream?token=<jwt>` | Real-time SSE stream |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health/db` | DB health (pool stats, pgvector, latency) |

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
FRONTEND_URL=http://localhost:3001
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","http://localhost:3002"]

# AI
GEMINI_API_KEY=<from Google AI Studio>

# Seed script (optional)
SEED_ADMIN_EMAIL=admin@eventai.pk
SEED_ADMIN_PASSWORD=<min 12 chars>
```

### `packages/frontend/.env`

```env
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
```

---

## Google OAuth2 Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add Authorized redirect URI: `http://localhost:5000/api/v1/auth/google/callback`
4. Copy Client ID and Client Secret to `packages/backend/.env`

---

## Project Status

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Database Setup (003) | ✅ Complete |
| 1 | FastAPI JWT Auth (013) | ✅ Complete |
| 1 | User Auth + Google OAuth (002) | ✅ Complete |
| 2 | Vendor Marketplace (004) | ✅ Complete |
| 2 | Event Management (005) | ✅ Complete |
| 3 | Booking System (009) | ✅ Complete |
| 3 | Notification System (010) | ✅ Complete |
| 3 | Real-Time SSE (008) | ✅ Complete |
| 4 | RAG & Semantic Search (011) | 📋 Spec ready |
| 4 | **AI Agent Chat (006)** | ✅ **Complete** |
| 4 | AI Event Planner (007) | ⚠️ Covered by AI Agent Chat |
| 5 | Vendor Portal — full (012) | ⚠️ Login only |

### AI Agent Chat — What's Built

The AI service (`packages/agentic_event_orchestrator`) is now a production-grade FastAPI application:

**Agent Pipeline**
- `TriageAgent` → `EventPlannerAgent` → `VendorDiscoveryAgent` → `BookingAgent` → `OrchestratorAgent`
- Built with OpenAI Agents SDK + Gemini 2.5 Flash via OpenAI-compatible endpoint
- `RunConfig(tracing_disabled=True)` — no OpenAI tracing calls, works with Gemini key

**Security — 7-Layer Prompt Injection Firewall**
- Layer 1: YAML blocklist exact match
- Layer 2: Regex patterns (6 threat categories: DIRECT_INJECTION, SYSTEM_PROMPT_EXTRACTION, ROLE_ESCALATION, INDIRECT_INJECTION, CONTEXT_OVERFLOW, TOOL_ABUSE)
- Layer 3: Heuristics (char density, token repetition, homoglyphs, zero-width chars)
- Layer 4: sklearn TF-IDF + LogisticRegression classifier (no torch/CUDA)
- Layer 5: Semantic similarity via sentence-transformers (optional)
- Layer 6: N-gram perplexity scoring
- Layer 7: Context coherence check
- SDK-native `@input_guardrail` (blocking — zero tokens on blocked input) + `@output_guardrail`
- Sandwich defense context builder (MINJA protection)
- Canary token + `OutputLeakDetector`
- Tool-level `@tool_input_guardrail` + `@tool_output_guardrail` on booking tools

**Endpoints**
- `POST /api/v1/ai/chat` — non-streaming
- `POST /api/v1/ai/chat/stream` — SSE token-by-token streaming
- `POST /api/v1/ai/feedback` — thumbs up/down per message
- `DELETE /api/v1/ai/memory/{user_id}` — GDPR right-to-forget
- `GET /api/v1/admin/chat/sessions` — paginated session log viewer
- `GET /api/v1/admin/chat/sessions/{id}/messages` — message history
- `GET /api/v1/admin/chat/feedback/stats` — aggregate feedback
- `POST /api/v1/admin/guardrails/test` — live injection probe battery

**Database** — 4 new tables in `ai` schema: `chat_sessions`, `messages`, `agent_executions`, `message_feedback`

**Frontend** — `packages/user` updated with SSE streaming, token-by-token rendering, agent badges, thumbs up/down feedback, session persistence

**To start the AI service:**
```bash
cd packages/agentic_event_orchestrator
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

See [`.kiro/specs/ai-agent-chat/`](.kiro/specs/ai-agent-chat/) for full spec.

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
uv run alembic history
```

---

## Project Constitution

The platform follows a strict [constitution](.specify/memory/constitution.md) that governs all development decisions:

- **Package manager:** `uv` for Python, `pnpm` for Node — no `pip`, no `npm`
- **Response envelope:** All API responses use `{"success", "data/error", "meta"}`
- **Error codes:** `AUTH_*`, `VALIDATION_*`, `NOT_FOUND_*`, `CONFLICT_*`, `INTERNAL_*`
- **No scattered config:** All settings via Pydantic `BaseSettings` + `@lru_cache`
- **Async-first:** All DB operations use `AsyncSession` + `asyncpg`
- **Structured logging:** Structlog JSON throughout — no `print()`
- **Test coverage:** ≥80% on services, ≥70% on routes — `uv run pytest`
- **Event-driven:** Domain events persisted to `domain_events` table via event bus

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

All PRs require passing CI (lint + type-check + tests) and at least 1 approval.
