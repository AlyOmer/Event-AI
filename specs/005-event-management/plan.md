# Implementation Plan: Event Management

**Branch**: `feature/event-management` | **Date**: 2026-04-07 | **Spec**: [spec.md](file:///home/ali/Desktop/Event-AI-Latest/specs/005-event-management/spec.md)
**Input**: Feature specification from `/specs/005-event-management/spec.md`

## Summary

Implements full event CRUD lifecycle (draft → planned → active → completed → canceled), event type admin management, vendor booking associations, and attachment support. All mutations emit domain events to the EventBus for downstream consumer processing (notifications, AI plans). Strict Zod validation, JWT auth + ownership checks, and pagination on list endpoints.

## Technical Context

**Language/Version**: Node.js ≥ 20 (Backend), React / Next.js 15 (Frontend)
**Primary Dependencies**: Fastify, Prisma, Zod, React Query
**Storage**: Neon DB (PostgreSQL) via Prisma
**Testing**: Jest + Supertest (Backend), React Testing Library (Frontend)
**Performance Goals**: Event list < 200ms for 100 events; edits < 1s round-trip
**Constraints**: EDA — all state transitions emit domain events; dates stored UTC
**Scale/Scope**: Central aggregate — events are the primary organizing concept for the platform.

## Constitution Check

- [x] **EDA (§III)**: All event state transitions emit domain events (`event.created`, `event.status_changed`, `event.cancelled`).
- [x] **API Contracts (§VI)**: Zod schemas, standardized envelope, `/api/v1/events/` prefix, pagination with `?page=&limit=`.
- [x] **Security (§VIII)**: JWT auth on all endpoints, ownership enforcement, rate limiting.
- [x] **Prisma Standards (§X)**: `@@map()` snake_case tables, UUIDv4 IDs, `@db.Timestamptz()` datetimes, indexes on FKs.

## Project Structure

### Source Code Context

```text
packages/backend/
├── src/
│   ├── routes/
│   │   └── events.routes.ts           # CRUD + status transitions + search/filter
│   ├── services/
│   │   └── event-bus.service.ts       # Existing EventEmitter
│   └── __tests__/
│       └── events.test.ts             # [NEW] Route integration tests

packages/user/
├── src/
│   ├── app/events/
│   │   ├── page.tsx                   # Event list with filters
│   │   ├── [id]/page.tsx              # Event detail view
│   │   └── new/page.tsx               # Create event form
│   └── lib/api/events.ts             # React Query hooks
```

## Phase 1: Database Schema & Validation

**Tasks**:
1. Verify `Event` model fields: `id`, `userId`, `name`, `eventTypeId`, `startDate`, `endDate`, `location` (JSONB), `guestCount`, `description`, `budget`, `status`, `timezone`, `specialRequirements`, `cancellationReason`.
2. Verify `EventType` model: `id`, `name` (unique), `description`, `icon`, `displayOrder`, `isActive`.
3. Add Zod schemas for event create/update/cancel payloads with proper date validation (future dates only for draft/planned).
4. Ensure indexes on `userId`, `eventTypeId`, `status`, `startDate`.

## Phase 2: Event CRUD Routes

**Tasks**:
1. `POST /api/v1/events` — create event with Zod validation, emit `event.created`.
2. `GET /api/v1/events` — paginated list with filters (status, type, date range), ownership scoped.
3. `GET /api/v1/events/:id` — detail view with ownership check (or vendor if booked).
4. `PATCH /api/v1/events/:id` — edit with status guards (only draft/planned editable), emit `event.updated`.
5. `PATCH /api/v1/events/:id/status` — lifecycle transitions with state machine validation, emit `event.status_changed`.
6. `DELETE /api/v1/events/:id/cancel` — soft cancel, record reason, emit `event.cancelled`.
7. `POST /api/v1/events/:id/duplicate` — clone core fields (not bookings) into new draft event.

## Phase 3: Event Type Admin Routes

**Tasks**:
1. `GET /api/v1/event-types` — list all active types (public).
2. `POST /api/v1/event-types` — admin-only, create type.
3. `PATCH /api/v1/event-types/:id` — admin-only, edit type.
4. `DELETE /api/v1/event-types/:id` — admin-only, deactivate (soft delete, prevent if referenced by active events).

## Phase 4: Frontend Integration

**Tasks**:
1. Build React Query hooks: `useEvents`, `useEvent`, `useCreateEvent`, `useUpdateEvent`.
2. Event list page with status filter tabs and search.
3. Event detail page showing status badge, vendor bookings, and planning info.
4. Create/edit form with `react-hook-form` + Zod resolver, event type dropdown.

## Phase 5: Testing

**Tasks**:
1. Backend integration tests: CRUD happy paths, ownership enforcement (403 for other user's events), state machine transitions (reject invalid transitions).
2. Rate limit verification: 10 creates/day per user.
3. Frontend component tests: form validation, filter interactions.
