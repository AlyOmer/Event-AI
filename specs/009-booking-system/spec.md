# Feature Specification: Booking System

**Feature Branch**: `feature/booking-system`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: "Booking System — Book vendors for events, conflict detection, status lifecycle"

---

## User Scenarios & Testing

### User Story 1 — Create a Booking (Priority: P1)

A user selects a vendor service for their event date and submits a booking request. The system validates availability, calculates pricing, prevents double-booking via optimistic locking, and creates the booking in `pending` status.

**Why this priority**: This is the core booking write path — without it, the entire platform has no transactional value. Every other feature depends on bookings existing.

**Independent Test**: Test by calling `POST /api/v1/bookings` with a valid vendor, service, and future date. Verify a booking record is created with `pending` status, correct pricing, and an availability lock is confirmed.

**Acceptance Scenarios**:

1. **Given** a vendor with an active service and available date, **When** a user submits `POST /api/v1/bookings` with `vendorId`, `serviceId`, `eventDate`, `clientEmail`, **Then** the system acquires an availability lock, creates a booking with `pending` status, confirms the lock as `booked`, and returns HTTP 201 with the booking object.
2. **Given** a vendor whose date is already booked, **When** a user submits a booking for that same vendor+service+date, **Then** the system returns HTTP 409 with error code `CONFLICT_DATE_UNAVAILABLE`.
3. **Given** a vendor with an active lock on the requested date, **When** a user tries to book, **Then** the system returns HTTP 409 with `CONFLICT_DATE_BEING_PROCESSED`.
4. **Given** a service with no active pricing, **When** a user submits a booking, **Then** the system returns HTTP 400 with `VALIDATION_NO_ACTIVE_PRICING`.
5. **Given** a valid booking is created, **Then** a `booking.created` domain event is emitted asynchronously and a confirmation email is sent (fire-and-forget).

---

### User Story 2 — Check Vendor Availability (Priority: P1)

A user or the AI agent checks if a vendor's service is available on a specific date before attempting a booking.

**Why this priority**: Availability checking is the prerequisite to booking. It eliminates wasted booking attempts and enables the AI agent to suggest alternative dates.

**Independent Test**: Call `GET /api/v1/bookings/availability?vendorId=...&serviceId=...&date=...` and verify the response indicates available/unavailable with a reason.

**Acceptance Scenarios**:

1. **Given** no existing booking or block for vendor+service+date, **When** availability is checked, **Then** return `{ available: true }`.
2. **Given** the date is already booked, **When** availability is checked, **Then** return `{ available: false, reason: "Date already booked" }`.
3. **Given** the vendor has manually blocked the date, **When** availability is checked, **Then** return `{ available: false, reason: "Vendor not available on this date" }`.

---

### User Story 3 — Vendor Confirms or Rejects a Booking (Priority: P1)

A vendor reviews a pending booking and either confirms or rejects it. On confirmation, the system records `confirmedAt` and `confirmedBy`. On rejection, it records the reason and releases the availability slot.

**Why this priority**: Without vendor acceptance, bookings cannot progress. This closes the two-party handshake.

**Independent Test**: Create a booking in `pending` status, then call `PATCH /api/v1/bookings/:id/status` with `{ status: "confirmed" }`. Verify the status transitions and a `booking.confirmed` event is emitted.

**Acceptance Scenarios**:

1. **Given** a booking in `pending` status, **When** the vendor sends `{ status: "confirmed" }`, **Then** the booking transitions to `confirmed`, `confirmedAt` is set, and `booking.confirmed` event is emitted.
2. **Given** a booking in `pending` status, **When** the vendor sends `{ status: "rejected", reason: "..." }`, **Then** the booking transitions to `rejected`, the availability slot is released back to `available`, and a `booking.cancelled` event is emitted.
3. **Given** a booking in `confirmed` status, **When** the vendor tries to confirm again, **Then** return HTTP 400 with `CONFLICT_ALREADY_CONFIRMED`.
4. **Given** a booking status change, **Then** the client receives a notification email with the new status.

---

### User Story 4 — Cancel a Booking (Priority: P2)

A user or vendor cancels an existing booking. The system records the cancellation reason, releases the availability slot, and notifies affected parties.

**Why this priority**: Cancellation is a critical lifecycle event that frees up vendor capacity. Without it, blocked dates are permanently lost.

**Independent Test**: Create a confirmed booking, call `PATCH /api/v1/bookings/:id/cancel`, and verify the status changes and the availability slot is released.

**Acceptance Scenarios**:

1. **Given** a booking in `pending` or `confirmed` status, **When** `PATCH /api/v1/bookings/:id/cancel` is called with `{ reason: "..." }`, **Then** the booking transitions to `cancelled`, `cancelledAt` is set, availability is released, and `booking.cancelled` event is emitted.
2. **Given** a booking already in `cancelled` status, **When** cancel is called again, **Then** return HTTP 400 with `CONFLICT_ALREADY_CANCELLED`.
3. **Given** a booking in `completed` status, **When** cancel is called, **Then** return HTTP 400 with `CONFLICT_COMPLETED_BOOKINGS_CANNOT_CANCEL`.

---

### User Story 5 — Booking Status Lifecycle (Priority: P2)

Bookings progress through a defined lifecycle: `pending → confirmed → in_progress → completed`. Side paths: `pending → rejected`, `pending|confirmed → cancelled`, `confirmed → no_show`.

**Why this priority**: The full lifecycle enables vendors to track work completion and triggers downstream events like review prompts and payment reconciliation.

**Independent Test**: Walk a booking through each valid transition via `PATCH /api/v1/bookings/:id/status` and verify invalid transitions are rejected.

**Acceptance Scenarios**:

1. **Given** a booking in `confirmed` status, **When** the vendor marks it `in_progress`, **Then** the status transitions and a `booking.status_changed` event is emitted.
2. **Given** a booking in `in_progress` status, **When** the vendor marks it `completed`, **Then** the status transitions, the user is prompted to leave a review, and a `booking.completed` event is emitted.
3. **Given** a booking in `pending` status, **When** the vendor tries to mark it `completed`, **Then** return HTTP 400 with `VALIDATION_INVALID_TRANSITION`.

---

### User Story 6 — List & Filter My Bookings (Priority: P2)

A user views their bookings filtered by status, date range, or vendor. Results are paginated.

**Why this priority**: Users need to track their booking history and upcoming events.

**Independent Test**: Create 3 bookings for a user, call `GET /api/v1/bookings?email=...&status=confirmed&page=1&limit=2`, verify pagination and filter correctness.

**Acceptance Scenarios**:

1. **Given** 5 bookings for a user, **When** requesting with `page=1&limit=2`, **Then** return 2 bookings with `meta: { total: 5, page: 1, limit: 2, pages: 3 }`.
2. **Given** bookings in mixed statuses, **When** filtering by `status=confirmed`, **Then** only confirmed bookings are returned.
3. **Given** no bookings match the filter, **Then** return an empty list with `meta.total: 0`.

---

### User Story 7 — AI Agent Creates Booking (Priority: P3)

The AI agent (BookingAgent) creates a booking on behalf of a user through the agent chat interface. The agent MUST show a summary and require explicit user confirmation before calling the booking API.

**Why this priority**: This is the AI-powered value proposition but depends on the core booking engine (P1) being solid first.

**Independent Test**: Simulate an agent chat session, verify the agent shows a booking summary, waits for "confirm booking", then calls `create_booking` tool.

**Acceptance Scenarios**:

1. **Given** a chat session where the user has searched for vendors, **When** the agent calls `create_booking`, **Then** the tool checks the confirmation gate and vendor allowlist before proceeding.
2. **Given** the user has NOT confirmed, **When** `create_booking` is called, **Then** the tool returns `requires_confirmation: true` with a summary — no booking is created.
3. **Given** the user confirms and the booking succeeds, **Then** the confirmation gate is cleared (one-shot) and the spending is recorded.

---

### User Story 8 — Booking Messages (Priority: P3)

Users and vendors can exchange messages attached to a booking (questions about requirements, logistics, etc.).

**Why this priority**: Enhances the booking experience but is not required for the core flow.

**Independent Test**: Create a booking, post a message via `POST /api/v1/bookings/:id/messages`, then list messages and verify ordering.

**Acceptance Scenarios**:

1. **Given** a confirmed booking, **When** the user sends a message, **Then** the message is stored with `senderType: 'client'` and the vendor is notified.
2. **Given** a booking with 5 messages, **When** listing messages, **Then** they are returned in reverse chronological order with pagination.

---

### Edge Cases

- What happens when two users try to book the same vendor+service+date simultaneously? → The optimistic lock (30s TTL) ensures only one succeeds; the second gets HTTP 409.
- How does the system handle an expired lock that was never released? → The `cleanupExpiredLocks()` cron job releases locks older than 30 seconds.
- What happens if the backend crashes between lock acquisition and booking creation? → The lock auto-expires and availability returns to `available`.
- What if a booking is created but the email notification fails? → Email is fire-and-forget; the booking succeeds regardless.
- What if a vendor's pricing changes between availability check and booking creation? → The system recalculates pricing at booking creation time using the latest active pricing record.
- Can a booking be created for a past date? → No; validation rejects `eventDate` before today.
- What if the AI agent exceeds the session spending limit? → The spending limit guard rejects the booking with a clear message.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST create bookings with automatic pricing lookup from the vendor's active `Pricing` record.
- **FR-002**: System MUST prevent double-booking using optimistic locking (acquire lock → create booking → confirm lock, or release on failure).
- **FR-003**: System MUST enforce a valid booking status lifecycle: `pending → confirmed → in_progress → completed`, with side transitions to `cancelled`, `rejected`, `no_show`.
- **FR-004**: System MUST expose an availability check endpoint for vendors+services+dates.
- **FR-005**: System MUST emit domain events (`booking.created`, `booking.confirmed`, `booking.cancelled`, `booking.completed`) for all status transitions per the EDA constitution rules.
- **FR-006**: System MUST send email notifications on booking creation, confirmation, rejection, and cancellation (fire-and-forget).
- **FR-007**: System MUST require JWT authentication on ALL booking endpoints. Unauthenticated access is forbidden.
- **FR-008**: System MUST support booking creation via the AI agent with mandatory user confirmation, vendor allowlist validation, and spending limit enforcement.
- **FR-009**: System MUST validate that `eventDate` is a future date.
- **FR-010**: System MUST apply rate limiting: 10 req/min for booking creation, 60 req/min for listing/reading.
- **FR-011**: System MUST release vendor availability when a booking is cancelled or rejected.
- **FR-012**: System MUST support booking messages (CRUD) for vendor-client communication on a booking.
- **FR-013**: System MUST log all booking operations to the `audit_logs` table.
- **FR-014**: System MUST reject invalid status transitions with descriptive error codes.

### Key Entities

- **Booking**: Core entity linking a User → Vendor → Service for a specific event date. Contains pricing, status lifecycle, payment tracking, and workflow timestamps.
- **VendorAvailability**: Tracks date-level availability per vendor+service with optimistic locking fields (`lockedBy`, `lockedUntil`, `lockedReason`).
- **BookingMessage**: Messages exchanged between vendor and client on a specific booking.
- **Event**: Optional parent entity that groups multiple bookings under a single event plan.
- **Pricing**: Active price record for a service, used to calculate `unitPrice` and `totalPrice` at booking time.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can create a booking in under 3 seconds (including lock acquisition, pricing lookup, and DB write).
- **SC-002**: Double-booking rate is 0% — the optimistic locking system prevents all concurrent conflicts.
- **SC-003**: All booking status transitions emit the correct domain event within 100ms.
- **SC-004**: 100% of booking endpoints require JWT authentication — zero unauthenticated access.
- **SC-005**: The AI agent's booking flow requires explicit user confirmation in 100% of cases — zero autonomous bookings.
- **SC-006**: Booking API achieves 80%+ test coverage (unit + integration) with zero LLM API calls in the test suite.
- **SC-007**: Expired availability locks are cleaned up within 60 seconds.

---

## Constitution Compliance Checklist

Every implementation decision in this feature MUST satisfy the following constitution mandates:

| Constitution Rule | Section | Requirement for Booking System |
|---|---|---|
| **Event-Driven Architecture** | III.1–III.8 | All booking transitions (`created`, `confirmed`, `cancelled`, etc.) MUST emit domain events using the standard event envelope. Notifications and side-effects are triggered by event consumers, NOT inline in route handlers. |
| **At-least-once delivery + idempotency** | III.5 | All booking event consumers MUST be idempotent. Use `eventId` for deduplication. |
| **Event store** | III.6 | All `booking.*` events MUST be persisted to the `domain_events` table for audit trail. |
| **Real-time to frontends** | III.7 | Booking status changes MUST be pushed to portals via SSE/WebSocket — no frontend polling. |
| **Dead letter handling** | III.8 | Failed booking event processing retries 3× with exponential backoff, then dead-letter store. |
| **Async DB via SQLModel** | IV.1 | AI service booking tools MUST use `create_async_engine` with `pool_pre_ping=True`. |
| **Prevent N+1 queries** | IV.2 | Booking list queries with vendor/service includes MUST use eager loading (`selectinload`). |
| **Transaction management** | IV.3 | Booking creation + availability lock MUST be wrapped in explicit `AsyncSession` transactions. |
| **TDD — Zero LLM calls in tests** | V | All booking AI tool tests MUST mock LLM calls via `respx`. 80%+ coverage on booking endpoints. |
| **API envelope** | VI.2 | All booking responses MUST follow `{ success, data, meta }` / `{ success, error }` format. |
| **API versioning** | VI.3 | All booking routes MUST be prefixed with `/api/v1/`. |
| **Error taxonomy** | VI.6 | Booking errors MUST use `CONFLICT_*`, `VALIDATION_*`, `NOT_FOUND_*` codes. |
| **JWT auth on all endpoints** | VIII.5 | ALL booking endpoints MUST be protected by `get_current_user` dependency / auth middleware. |
| **Rate limiting** | VIII.3 | Booking creation: 10 req/min. Booking reads: 60 req/min. |
| **Input validation at boundary** | VIII.4 | All booking inputs MUST be validated via Zod schemas (backend) or Pydantic models (AI service). |
| **No `sys.path.insert`** | X (Python) | AI booking tools MUST use proper package structure with `pyproject.toml` — no path hacks. |
| **No `os.environ.get`** | Anti-Patterns | All config MUST use Pydantic `BaseSettings` + `@lru_cache`. |
| **Lifespan for resources** | VII.9 | DB sessions, HTTP clients used by booking tools MUST be initialized in FastAPI `lifespan`. |
| **`Depends()` for DI** | VII.10 | Booking tool DB sessions MUST be injected via `Depends()`, never accessed directly. |
| **Tool docstrings mandatory** | Anti-Patterns | Every `@function_tool` in booking tools MUST have a docstring. |
| **YAGNI** | IX.1 | Do not build speculative booking sub-features. Only implement what the user stories require. |
| **Prisma schema standards** | X (Prisma) | All booking models use `@@map()`, `@map()`, UUIDv4 IDs, `@db.Timestamptz()`. |
