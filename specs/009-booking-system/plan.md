# Implementation Plan: Booking System

**Branch**: `feature/booking-system` | **Date**: 2026-04-07 | **Spec**: [specs/booking-system/spec.md](file:///home/ali/Desktop/Event-AI-Latest/specs/booking-system/spec.md)
**Input**: Feature specification from `/specs/booking-system/spec.md`

## Summary

The Booking System orchestrates the lifecycle of event bookings between users and vendors. It resolves existing critical gaps: integration of the optimistic locking service to prevent double-booking, adding JWT auth to all endpoints, exposing availability APIs, and implementing the full status lifecycle. Crucially, it must refactor the backend to emit `booking.*` domain events and align the AI `booking_tools.py` with constitution mandates (TDD, async SQLModel, `create_async_engine`).

## Technical Context

**Language/Version**: Node.js ≥ 20 (Backend), Python ≥ 3.12 (AI Service)
**Primary Dependencies**: Fastify, Prisma, Zod, FastAPI, SqlModel, OpenAI Agents SDK
**Storage**: Neon DB (PostgreSQL) via Prisma and `asyncpg`
**Testing**: `vitest`/`jest` (Backend), `pytest-asyncio` + `respx` (AI Service)
**Target Platform**: Linux server containerized via Node/Python
**Project Type**: Monorepo with web backend and python AI service
**Performance Goals**: Lock acquisition and booking insert < 3 seconds
**Constraints**: Zero LLM calls in test suite; Strict adherence to Event-Driven Architecture (EDA)
**Scale/Scope**: Moderate; directly touches core business path.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **EDA Driven**: No inline emails in route handlers.
- [x] **Zero N+1 Queries**: Eager loading (`selectinload`/`include`) mandated for reads.
- [x] **No Banned Hacks**: Python AI tools stripped of `sys.path.insert`, `os.environ.get`.
- [x] **Security**: JWT Auth + Zod/Pydantic validation explicitly required.

## Project Structure

### Documentation (this feature)

```text
specs/booking-system/
├── plan.md              # This file
├── spec.md              # Feature specification
└── verification.md      # Testing and verification sign-off
```

### Source Code Context

```text
packages/backend/
├── src/
│   ├── routes/
│   │   └── bookings.routes.ts        # Target for auth, locks, status transitions
│   ├── services/
│   │   ├── booking-lock.service.ts   # Existing service, needs integrating
│   │   └── event-bus.service.ts      # [NEW] Simple EventEmitter wrapper
│   └── __tests__/
│       └── bookings.test.ts          # [NEW] Tests for backend logic

packages/agentic_event_orchestrator/
└── tools/
    ├── booking_tools.py              # Target for dependency cleanup & lifespan
    └── __tests__/
        └── test_booking_tools.py     # [NEW] TDD tests mocking LLMs
```

## Phase 1: Database & Event Bus Foundation

**Context**: The constitution mandates all domain events be persisted in a `domain_events` table for audit traits, but this table doesn't exist yet. The existing booking models are solid, but we need an internal event bus.

**Tasks**:
1. Add `DomainEvent` model to `schema.prisma`.
2. Generate migration (`pnpm prisma migrate dev --name add_domain_events`).
3. Create `packages/backend/src/services/event-bus.service.ts` using Node's `EventEmitter` to dispatch and save events to the DB asynchronously.

## Phase 2: Refactor Booking Routes

**Context**: `bookings.routes.ts` lacks JWT authentication, bypasses the pessimistic availability lock, handles invalid/incomplete status transitions, and fires inline logic.

**Tasks**:
1. Add `authMiddleware` to all endpoints in `bookings.routes.ts`.
2. Update the `POST /api/v1/bookings` creation route:
    - Call `acquireAvailabilityLock` before proceeding.
    - Write the `Booking` into Prisma.
    - Call `confirmBookingAvailability` to seal the lock.
    - Emit `booking.created` using `EventBusService`.
    - Catch failures and call `releaseAvailabilityLock`.
3. Add `GET /api/v1/bookings/availability` route that exposes `bookingLockService.checkAvailability()`.
4. Update `PATCH /api/v1/bookings/:id/status` to:
    - Support missing transitions (`in_progress`, `completed`, `no_show`).
    - Validate lifecycle state machine logic.
    - Emit corresponding events (`booking.confirmed`, `booking.completed`, etc.).
5. Add `PATCH /api/v1/bookings/:id/cancel` that handles cancellations and availability release, emitting `booking.cancelled`.

## Phase 3: AI Service Tool Refactoring

**Context**: `booking_tools.py` violates constitution rules with `sys.path.insert`, bare `os.environ.get`, and missing `Depends()` injection.

**Tasks**:
1. Remove all `sys.path.insert` logic. Ensure the `pyproject.toml` paths are used.
2. Refactor `booking_tools.py` dependency injections. DB sessions and HTTP clients must be passed via function parameters or `Depends()` context from the app lifespan.
3. Validate explicit inputs via `Pydantic` models without raw dict conversions.
4. Assure the confirm booking gate utilizes the updated AI-agent memory layer.

## Phase 4: Testing & Verification

**Context**: TDD is non-negotiable. Backend needs route tests, AI needs tool tests.

**Tasks**:
1. Create `packages/backend/src/__tests__/bookings.test.ts`. Test concurrent bookings to `POST /api/v1/bookings` to ensure the lock prevents double-booking (HTTP 409).
2. Create `packages/agentic_event_orchestrator/tools/__tests__/test_booking_tools.py`.
3. Test tool `create_booking` using `respx` to mock the backend HTTP endpoints — assert zero LLM calls during this execution.
4. Execute End-to-End checks manually simulating the UI flow.
