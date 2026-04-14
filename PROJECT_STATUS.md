# Event-AI — Project Status
**Last Updated:** April 10, 2026  
**Platform:** AI-powered event planning marketplace for Pakistan  
**Stack:** FastAPI (Python/uv) + Next.js + Neon PostgreSQL + pgvector

---

## Build Order & Status

| Phase | Module | Name | Status | Spec |
|---|---|---|---|---|
| 1 | 003 | Database Setup | ✅ Done | phase1-completion |
| 1 | 013 | FastAPI JWT Auth | ✅ Done | phase1-completion |
| 1 | 002 | User Auth + Google OAuth | ✅ Done | phase1-completion |
| 2 | 004 | Vendor Marketplace | ✅ Done | phase2-vendor-marketplace |
| 2 | 005 | Event Management | ✅ Done | event-management |
| 3 | 009 | Booking System | ✅ Done | phase3-booking-system |
| 3 | 010 | Notification System | 📋 Spec Ready | notification-system |
| 3 | 008 | Real-Time Updates (SSE) | ⚠️ Partial | (SSE infra exists, gaps in 010) |
| 4 | 011 | RAG & Semantic Search | 📋 Spec Ready | rag-semantic-search |
| 4 | 006 | AI Agent Chat | ❌ Not Started | — |
| 4 | 007 | AI Event Planner | ❌ Not Started | — |
| 5 | 012 | Vendor Portal (Frontend) | ⚠️ Partial | — |
| 5 | 001 | Spec Generator (Tooling) | ❌ Not Started | — |

---

## What Is Done ✅

### Backend — `packages/backend`

#### Auth & Users (Phase 1)
- JWT access + refresh token pair (HS256, 15min/7day TTL)
- `POST /api/v1/auth/register` — email/password registration
- `POST /api/v1/auth/login` — OAuth2 form-encoded (Swagger-compatible)
- `POST /api/v1/users/login` — JSON login for frontend portal
- `GET /api/v1/auth/me` — authenticated user profile
- `POST /api/v1/auth/refresh` — token rotation
- `POST /api/v1/auth/logout` — refresh token revocation
- `POST /api/v1/auth/password-reset-request` + `/confirm`
- Google OAuth2 (`GET /api/v1/auth/google` + `/callback`) — full flow with CSRF state JWT
- Account locking after 5 failed attempts (15min lockout)
- Standardised error envelope `{"success", "data/error", "meta"}` on all routes
- Global `HTTPException` + `RequestValidationError` handlers in `main.py`
- Admin seed script (`uv run python -m src.scripts.seed`)
- `GET /api/v1/health/db` — DB health with pool stats + pgvector check

#### Vendor Marketplace (Phase 2)
- `POST /api/v1/vendors/register` — vendor registration with approval workflow
- `GET/PUT /api/v1/vendors/profile/me` — vendor self-service profile
- `DELETE /api/v1/vendors/profile/me` — soft-delete (SUSPENDED)
- `GET /api/v1/vendors/me/bookings` — vendor booking list
- `PATCH /api/v1/vendors/me/bookings/{id}/status` — vendor confirms/rejects
- Category assignment on registration + update (M2M via `vendor_categories`)
- `VendorRead` includes `categories: List[CategoryRead]`
- Admin approval workflow (`GET/POST /api/v1/admin/approvals/`)
- Vendor search with trigram + ILIKE (`GET /api/v1/public_vendors/`)
- Autocomplete suggestions (`GET /api/v1/public_vendors/suggestions`)
- `max_price` filter via `services.price_min` subquery
- Correct `count_stmt` for pagination total
- `GET /api/v1/categories/` — seeded with 8 Pakistani event categories

#### Event Management (Phase 2 / Module 005)
- `Event` + `EventType` models with Alembic migration
- `EventStatus` state machine: `draft → planned → active → completed`, any → `canceled`
- `EventService` with all business logic (create, get, list, update, cancel, duplicate, list_bookings, admin_list)
- `POST /api/v1/events/` — create (status=PLANNED, validates event_type)
- `GET /api/v1/events/` — paginated list with status filter
- `GET /api/v1/events/{id}` — single event
- `PUT /api/v1/events/{id}` — update (blocked on terminal status)
- `DELETE /api/v1/events/{id}` — cancel via state machine
- `PATCH /api/v1/events/{id}/status` — explicit status transition
- `POST /api/v1/events/{id}/duplicate` — clone with `status=DRAFT`
- `GET /api/v1/events/{id}/bookings` — paginated bookings for event
- `GET /api/v1/events/admin/all` — admin list with filters (status, user_id, city, date range)
- Domain events: `event.created`, `event.status_changed`, `event.cancelled` via event bus
- Rate limiting: 10/min create, 60/min reads
- Full test suite: 42 tests (20 unit + 22 integration), all passing with `uv run pytest`

#### Booking System (Phase 3 / Module 009)
- `VendorAvailability` model with locking fields (status, locked_by, locked_until, locked_reason)
- Acquire-lock → create-booking → confirm-lock pattern (30s TTL)
- `POST /api/v1/bookings/` — create with pricing lookup + availability lock
- `GET /api/v1/bookings/` — paginated list with status filter
- `GET /api/v1/bookings/{id}` — single booking
- `PATCH /api/v1/bookings/{id}/status` — JSON body status update with state machine
- `PATCH /api/v1/bookings/{id}/cancel` — cancel + release slot
- `GET /api/v1/bookings/availability` — check vendor/service/date availability
- `POST /api/v1/bookings/{id}/messages` + `GET` — booking messages CRUD
- Domain events: `booking.created`, `booking.confirmed`, `booking.cancelled`, `booking.completed`
- Background task: expired lock cleanup every 60 seconds
- Alembic migration for `vendor_availability` table

#### Notification System (Module 010 — Partial)
- `Notification` model + `notifications` table (Alembic migration applied)
- `NotificationService.handle()` — event bus listener for all `booking.*` events
- Real-time SSE push on notification creation
- `GET /api/v1/notifications/` — paginated list
- `GET /api/v1/notifications/unread-count`
- `PATCH /api/v1/notifications/read-all`
- `PATCH /api/v1/notifications/{id}/read`
- `SSEConnectionManager` — per-user asyncio queues
- `GET /api/v1/sse/stream?token=<jwt>` — SSE stream endpoint

#### Infrastructure
- Neon PostgreSQL (serverless) with pgvector extension enabled
- Alembic migrations for all tables
- Structlog structured JSON logging throughout
- `rate_limit_dependency` middleware (in-memory sliding window)
- Event bus (`EventBusService`) with outbox pattern (persists to `domain_events` table)
- CORS configured from `Settings.cors_origins`
- Backend running on port 5000 (`uv run uvicorn src.main:app --port 5000`)

### Frontend — `packages/frontend` (Vendor Portal)

- Next.js 14 App Router
- Login page with email/password + Google OAuth button
- Google OAuth callback page (`/auth/callback`) — reads `?token=` from redirect
- Auth store (Zustand) with `loginWithTokens()` for OAuth flow
- Token refresh interceptor in `api.ts`
- Error envelope parsing (`{"success": false, "error": {"code", "message"}}`)
- Middleware protecting all routes except public ones
- Running on port 3001

---

## What Is Spec-Ready (Next to Implement) 📋

### Module 010 — Notification System Gaps
**Spec:** `.kiro/specs/notification-system/`  
**10 tasks, ~46 sub-tasks**

Gaps to close:
- Add `event_created`, `event_status_changed`, `event_cancelled`, `vendor_approved`, `vendor_rejected` to `NotificationType`
- Subscribe `notification_service.handle` to `event.*` and `vendor.*` in lifespan
- `DELETE /notifications/{id}` + `DELETE /notifications/read` endpoints
- Rate limiting on all notification endpoints
- Fix `mark_read` response envelope
- SSE queue overflow: evict-oldest strategy + `dropped_count()` observable
- Per-user notification preferences (`NotificationPreference` table + 2 endpoints)
- Full test suite

### Module 011 — RAG & Semantic Search
**Spec:** `.kiro/specs/rag-semantic-search/`  
**16 tasks, ~55 sub-tasks**

To build:
- `VendorEmbedding` table with `vector(768)` + HNSW index (Alembic migration)
- `EmbeddingService` — `generate_vendor_text()`, `embed_text()` via Gemini, `upsert_vendor_embedding()` with SHA-256 staleness, `embed_batch()`
- Auto-embed on `vendor.approved`, delete on `vendor.rejected/suspended`
- `SearchService.semantic_search()` — pgvector cosine similarity
- `SearchService.hybrid_search()` — 0.4 trigram + 0.6 semantic weighted blend
- `GET /api/v1/public_vendors/semantic` — natural language search
- `GET /api/v1/public_vendors/search?mode=hybrid|semantic|keyword`
- `POST /api/v1/admin/embeddings/backfill` — admin bulk regeneration
- Tests with `respx` mocking Gemini (zero real API calls)

---

## What Is Not Started ❌

### Module 008 — Real-Time Updates (Full)
SSE infrastructure exists but needs:
- Frontend EventSource integration
- Reconnection logic with exponential backoff
- Event type routing on the frontend

### Module 006 — AI Agent Chat
Depends on: 002 ✅, 004 ✅, 005 ✅, 009 ✅, 011 📋  
Requires: `packages/agentic_event_orchestrator` FastAPI service  
Stack: OpenAI Agents SDK + Gemini LLM + Mem0 memory + LangChain RAG

### Module 007 — AI Event Planner
Depends on: 005 ✅, 004 ✅, 006 ❌  
Auto-generates event plans, recommends vendors, schedules bookings

### Module 012 — Vendor Portal (Complete)
Frontend surface over all backend APIs. Currently has login page only.  
Needs: Dashboard, vendor profile management, booking management, notifications UI, real-time updates

### Module 001 — Spec Generator (Tooling)
Developer tooling — can be built anytime

---

## Dependency Chain Summary

```
✅ 003 Database
✅ 013 JWT Auth
✅ 002 User Auth + Google OAuth
✅ 004 Vendor Marketplace
✅ 005 Event Management
✅ 009 Booking System
📋 010 Notifications (gaps)     ← implement next
📋 011 RAG Search               ← implement next (parallel with 010)
❌ 008 Real-Time (full)         ← after 010
❌ 006 AI Agent Chat            ← after 011
❌ 007 AI Event Planner         ← after 006
❌ 012 Vendor Portal            ← after 003–010
❌ 001 Spec Generator           ← anytime
```

---

## Quick Commands

```bash
# Backend (port 5000)
cd packages/backend
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

# Frontend (port 3001)
cd packages/frontend
pnpm dev

# Run all tests
cd packages/backend
uv run pytest -v

# Run specific test file
uv run pytest tests/test_event_routes.py -v

# Seed database
SEED_ADMIN_EMAIL=admin@eventai.pk SEED_ADMIN_PASSWORD=AdminPass123! uv run python -m src.scripts.seed

# Run migrations
uv run alembic upgrade head
```

---

## Environment Variables Required

```env
# packages/backend/.env
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=<256-bit random>
GOOGLE_CLIENT_ID=776909946833-...
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=http://localhost:5000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:3001
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]
GEMINI_API_KEY=AIzaSy...

# packages/frontend/.env
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
```
