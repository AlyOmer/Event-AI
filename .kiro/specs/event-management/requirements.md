# Requirements Document

## Introduction

Module 005 — Event Management closes the gap between the existing Event CRUD skeleton and a
production-ready, constitution-compliant event management system for the Event-AI platform.

The platform is an AI-powered event planning marketplace for Pakistan. Events (weddings, mehndi,
baraat, walima, corporate events, etc.) are the central planning unit. Vendors are booked against
events, the AI planner monitors event progress, and platform admins oversee all events for
compliance and support.

The existing implementation has working models, migrations, and basic CRUD routes. This spec
covers ten specific gaps that must be closed before the module is considered complete:

1. Response envelope non-compliance
2. Missing domain event emission
3. Missing EventService layer
4. Missing status-transition state machine
5. Missing event-to-bookings link endpoint
6. Missing duplicate-event endpoint
7. Missing admin event list endpoint
8. Missing rate limiting
9. Missing test suite
10. Date validation gaps in EventUpdate

All requirements in this document reference the platform constitution (v2.0.1) as the authoritative
source of rules.

---

## Glossary

- **Event_Management_System**: The FastAPI backend module responsible for creating, reading,
  updating, and cancelling events. Implemented in `packages/backend`.
- **EventService**: A dedicated Python class in `src/services/event_service.py` that encapsulates
  all event business logic, following the same pattern as `BookingService`.
- **Event**: A SQLModel ORM entity representing a planned occasion (wedding, corporate event, etc.)
  owned by a single authenticated user.
- **EventType**: A reference entity (wedding, mehndi, corporate, etc.) managed by admins.
- **EventStatus**: The lifecycle enum — `draft`, `planned`, `active`, `completed`, `canceled`.
- **State_Machine**: The enforced set of valid `EventStatus` transitions.
- **Response_Envelope**: The standardised JSON wrapper `{"success": bool, "data": ..., "meta": {}}`
  mandated by constitution §VI.2.
- **Domain_Event**: A persisted, immutable fact emitted via `event_bus.emit()` and stored in the
  `domain_events` table. Consumed by the AI service and notification consumers.
- **Event_Bus**: The `EventBusService` singleton (`src/services/event_bus_service.py`) that
  persists domain events and dispatches them to registered async listeners.
- **Rate_Limiter**: The `rate_limit_dependency` helper in `src/middleware/rate_limit.py` that
  enforces per-IP sliding-window request limits.
- **Admin**: An authenticated user whose account has the `is_admin` flag set to `True`.
- **Authenticated_User**: Any user who presents a valid JWT Bearer token via the
  `get_current_user` dependency.
- **Booking**: A SQLModel entity linking a vendor service to an event date; has an `event_id`
  foreign key referencing `events.id`.
- **Duplicate**: A new `Event` record cloned from an existing one, with status reset to `draft`
  and a `"Copy of "` name prefix, containing no bookings.
- **Pagination_Meta**: The `meta` object `{"total": int, "page": int, "limit": int, "pages": int}`
  returned on all list endpoints per constitution §VI.5.

---

## Requirements

---

### Requirement 1: Response Envelope Compliance

**User Story:** As a frontend developer, I want every event API response to follow the standard
`{"success": true, "data": ..., "meta": {}}` envelope, so that my client code can handle all
responses uniformly without special-casing individual endpoints.

**Constitution reference:** §VI.2 — All responses follow the standardised envelope.

#### Acceptance Criteria

1. THE Event_Management_System SHALL wrap every successful single-resource response in
   `{"success": true, "data": <EventRead>, "meta": {}}`.
2. THE Event_Management_System SHALL wrap every successful list response in
   `{"success": true, "data": [<EventRead>, ...], "meta": {"total": int, "page": int, "limit": int, "pages": int}}`.
3. THE Event_Management_System SHALL wrap every successful `EventType` list response in
   `{"success": true, "data": [<EventTypeRead>, ...], "meta": {}}`.
4. WHEN an error occurs, THE Event_Management_System SHALL return
   `{"success": false, "error": {"code": "<ERROR_CODE>", "message": "<human-readable message>"}}`.
5. THE Event_Management_System SHALL use only the following error codes for event-related errors:
   `NOT_FOUND_EVENT`, `NOT_FOUND_EVENT_TYPE`, `CONFLICT_EVENT_TYPE_EXISTS`,
   `CONFLICT_EVENT_TYPE_IN_USE`, `VALIDATION_INVALID_EVENT_TYPE`,
   `VALIDATION_INVALID_STATUS_TRANSITION`, `VALIDATION_END_DATE_BEFORE_START`,
   `AUTH_FORBIDDEN`.
6. THE Event_Management_System SHALL return HTTP 201 for resource-creation responses and HTTP 200
   for all other successful responses.

---

### Requirement 2: EventService Layer

**User Story:** As a backend developer, I want all event business logic encapsulated in a
dedicated `EventService` class, so that route handlers remain thin, logic is testable in
isolation, and the codebase follows the established `BookingService` / `VendorService` pattern.

**Constitution reference:** §IX.2 — Framework trust; §X — Code quality; constitution pattern
established by `BookingService`.

#### Acceptance Criteria

1. THE Event_Management_System SHALL provide an `EventService` class in
   `src/services/event_service.py`.
2. THE EventService SHALL expose at minimum the following async methods:
   `create_event`, `get_event`, `list_events`, `update_event`, `cancel_event`,
   `duplicate_event`, `transition_status`, `list_event_bookings`, `list_all_events_admin`.
3. WHEN a route handler calls an EventService method, THE route handler SHALL contain no
   business logic beyond calling the service method and returning the envelope response.
4. THE EventService SHALL accept an `AsyncSession` as its first parameter on every method,
   following the dependency-injection pattern used by `BookingService`.
5. THE EventService SHALL use `structlog.get_logger()` for all log statements, with structured
   key-value fields (e.g. `event_id`, `user_id`, `old_status`, `new_status`).

---

### Requirement 3: Status Transition State Machine

**User Story:** As a platform operator, I want event status changes to follow a strict state
machine, so that events cannot jump to invalid states (e.g. a completed event cannot be
re-activated) and the AI planner always sees a consistent lifecycle.

**Constitution reference:** §III — Event-driven architecture; §VI.6 — Error codes.

#### Acceptance Criteria

1. THE EventService SHALL enforce the following and only the following valid status transitions:
   - `draft` → `planned`
   - `planned` → `active`
   - `active` → `completed`
   - `planned` → `canceled`
   - `active` → `canceled`
   - `draft` → `canceled`
2. WHEN a caller requests a transition not listed in criterion 1, THE EventService SHALL raise
   an HTTP 409 error with code `VALIDATION_INVALID_STATUS_TRANSITION` and a message that
   includes both the current status and the requested status.
3. WHEN a caller requests a transition to `canceled` on an event whose status is already
   `completed`, THE EventService SHALL raise an HTTP 409 error with code
   `VALIDATION_INVALID_STATUS_TRANSITION`.
4. WHEN a caller requests a transition to `canceled` on an event whose status is already
   `canceled`, THE EventService SHALL raise an HTTP 409 error with code
   `VALIDATION_INVALID_STATUS_TRANSITION`.
5. THE EventService SHALL expose a `transition_status` method that accepts the current event,
   the target `EventStatus`, and the acting `user_id`, applies the transition, persists the
   change, and emits the appropriate domain event.
6. WHILE an event status is `completed` or `canceled`, THE EventService SHALL reject any
   attempt to update the event's fields with HTTP 409 and code
   `VALIDATION_INVALID_STATUS_TRANSITION`.

---

### Requirement 4: Domain Event Emission

**User Story:** As an AI service consumer, I want domain events emitted whenever an event is
created, its status changes, or it is cancelled, so that the AI planner and notification
consumers can react in real time without polling the database.

**Constitution reference:** §III — Event-driven architecture; §III.6 — Event store for
`event.*` events.

#### Acceptance Criteria

1. WHEN `EventService.create_event` successfully persists a new `Event`, THE EventService SHALL
   call `event_bus.emit(session, "event.created", payload, user_id=user_id)` before committing
   the transaction.
2. THE `event.created` payload SHALL contain at minimum:
   `{"event_id": str, "user_id": str, "event_type_id": str, "name": str, "start_date": str,
   "status": "planned"}`.
3. WHEN `EventService.transition_status` successfully changes an event's status, THE EventService
   SHALL call `event_bus.emit(session, "event.status_changed", payload, user_id=user_id)`.
4. THE `event.status_changed` payload SHALL contain at minimum:
   `{"event_id": str, "user_id": str, "old_status": str, "new_status": str}`.
5. WHEN `EventService.cancel_event` successfully cancels an event, THE EventService SHALL call
   `event_bus.emit(session, "event.cancelled", payload, user_id=user_id)`.
6. THE `event.cancelled` payload SHALL contain at minimum:
   `{"event_id": str, "user_id": str, "reason": str | null, "canceled_at": str}`.
7. THE EventService SHALL emit domain events within the same `AsyncSession` transaction as the
   database mutation, so that the domain event and the state change are committed atomically.
8. IF `event_bus.emit` raises an exception, THE EventService SHALL allow the exception to
   propagate, causing the enclosing transaction to roll back.

---

### Requirement 5: Date Validation in EventUpdate

**User Story:** As a user, I want the system to reject event updates where `start_date` is in
the past or `end_date` is before `start_date`, so that my event data is always logically
consistent.

**Constitution reference:** §VI.1 — Pydantic validation at boundary; §VI.6 — error codes.

#### Acceptance Criteria

1. WHEN `EventUpdate` includes a `start_date` value, THE Event_Management_System SHALL validate
   that the new `start_date` is strictly after the current UTC time; IF it is not, THE
   Event_Management_System SHALL return HTTP 422 with code `VALIDATION_INVALID_DATE` and message
   `"start_date must be in the future"`.
2. WHEN `EventCreate` or `EventUpdate` includes both `start_date` and `end_date`, THE
   Event_Management_System SHALL validate that `end_date` is strictly after `start_date`; IF it
   is not, THE Event_Management_System SHALL return HTTP 422 with code
   `VALIDATION_END_DATE_BEFORE_START` and message `"end_date must be after start_date"`.
3. WHEN `EventUpdate` includes only `end_date` (without `start_date`), THE EventService SHALL
   compare the new `end_date` against the existing event's `start_date`; IF `end_date` is not
   strictly after the existing `start_date`, THE Event_Management_System SHALL return HTTP 422
   with code `VALIDATION_END_DATE_BEFORE_START`.
4. THE `EventCreate` schema SHALL retain its existing `start_date` future-date validator.
5. THE `EventUpdate` schema SHALL add a `start_date` future-date validator equivalent to the one
   in `EventCreate`.

---

### Requirement 6: Event-to-Bookings Link Endpoint

**User Story:** As an AI planner agent, I want to retrieve all bookings associated with a
specific event via `GET /events/{id}/bookings`, so that I can assess vendor coverage and
planning progress for that event without issuing separate queries.

**Constitution reference:** §III — AI service integration; §VI.5 — Pagination; §IV.2 — No N+1
queries.

#### Acceptance Criteria

1. THE Event_Management_System SHALL expose `GET /api/v1/events/{event_id}/bookings` as an
   authenticated endpoint protected by `get_current_user`.
2. WHEN the authenticated user owns the event, THE Event_Management_System SHALL return
   `{"success": true, "data": [<BookingRead>, ...], "meta": {"total": int, "page": int,
   "limit": int, "pages": int}}`.
3. WHEN the authenticated user does not own the event, THE Event_Management_System SHALL return
   HTTP 404 with code `NOT_FOUND_EVENT`.
4. THE EventService SHALL query bookings using `selectinload` or a single JOIN query to prevent
   N+1 database queries.
5. THE endpoint SHALL support `?page=1&limit=20` query parameters following constitution §VI.5
   pagination conventions.
6. WHEN the event has no bookings, THE Event_Management_System SHALL return
   `{"success": true, "data": [], "meta": {"total": 0, "page": 1, "limit": 20, "pages": 0}}`.
7. THE endpoint SHALL support an optional `?status` query parameter to filter bookings by
   `BookingStatus` value.

---

### Requirement 7: Duplicate Event Endpoint

**User Story:** As a user planning recurring events (e.g. annual weddings, yearly corporate
galas), I want to clone an existing event via `POST /events/{id}/duplicate`, so that I can
reuse all planning details without re-entering them manually.

**Constitution reference:** §VI.2 — Response envelope; §VI.6 — Error codes.

#### Acceptance Criteria

1. THE Event_Management_System SHALL expose `POST /api/v1/events/{event_id}/duplicate` as an
   authenticated endpoint protected by `get_current_user`.
2. WHEN the authenticated user owns the source event, THE EventService SHALL create a new
   `Event` record with:
   - All scalar fields copied from the source event (`event_type_id`, `description`,
     `start_date`, `end_date`, `timezone`, `venue_name`, `address`, `city`, `country`,
     `guest_count`, `budget`, `special_requirements`)
   - `name` set to `"Copy of <source.name>"`
   - `status` set to `draft`
   - A new `id`, `created_at`, and `updated_at`
   - `user_id` set to the authenticated user's id
   - `cancellation_reason` and `canceled_at` set to `None`
3. THE Event_Management_System SHALL return HTTP 201 with the new event wrapped in the standard
   response envelope.
4. WHEN the source event does not exist or does not belong to the authenticated user, THE
   Event_Management_System SHALL return HTTP 404 with code `NOT_FOUND_EVENT`.
5. THE EventService SHALL emit an `event.created` domain event for the duplicated event,
   following the same payload structure as Requirement 4 criterion 2.
6. THE duplicate SHALL contain no bookings or vendor associations from the source event.

---

### Requirement 8: Admin Event List Endpoint

**User Story:** As a platform admin, I want to list all events across all users with filtering
by status, user ID, city, and date range, so that I can monitor platform activity and provide
support.

**Constitution reference:** §VI.2 — Response envelope; §VI.5 — Pagination; §VIII — Auth.

#### Acceptance Criteria

1. THE Event_Management_System SHALL expose `GET /api/v1/events/admin/all` as an endpoint
   protected by the `require_admin` dependency.
2. WHEN called by an admin, THE Event_Management_System SHALL return all events across all users
   wrapped in `{"success": true, "data": [...], "meta": {"total": int, "page": int, "limit": int,
   "pages": int}}`.
3. THE endpoint SHALL support the following optional query parameters:
   - `status` — filter by `EventStatus` value
   - `user_id` — filter by owning user's UUID
   - `city` — case-insensitive partial match on `Event.city`
   - `date_from` — include only events with `start_date >= date_from` (ISO-8601 datetime)
   - `date_to` — include only events with `start_date <= date_to` (ISO-8601 datetime)
4. THE endpoint SHALL support `?page=1&limit=20` pagination following constitution §VI.5.
5. WHEN a non-admin authenticated user calls this endpoint, THE Event_Management_System SHALL
   return HTTP 403 with code `AUTH_FORBIDDEN`.
6. WHEN an unauthenticated request is made to this endpoint, THE Event_Management_System SHALL
   return HTTP 401.
7. THE EventService SHALL implement `list_all_events_admin` with all filter parameters, using
   SQLAlchemy query composition to avoid N+1 queries.

---

### Requirement 9: Rate Limiting

**User Story:** As a platform operator, I want event creation and read endpoints to enforce rate
limits, so that the API is protected from abuse and denial-of-service attempts.

**Constitution reference:** §VIII.3 — Rate limiting mandatory on all public endpoints:
10 req/min for booking/creation endpoints, 60 req/min for public APIs.

#### Acceptance Criteria

1. THE Event_Management_System SHALL apply a rate limit of 10 requests per minute per IP address
   to the `POST /api/v1/events/` (create event) endpoint using `rate_limit_dependency`.
2. THE Event_Management_System SHALL apply a rate limit of 10 requests per minute per IP address
   to the `POST /api/v1/events/{event_id}/duplicate` endpoint.
3. THE Event_Management_System SHALL apply a rate limit of 60 requests per minute per IP address
   to all `GET /api/v1/events/` and `GET /api/v1/events/{event_id}` read endpoints.
4. WHEN a client exceeds the applicable rate limit, THE Event_Management_System SHALL return
   HTTP 429 with a `Retry-After` header indicating the window duration in seconds.
5. THE rate limiting SHALL be applied via the existing `rate_limit_dependency` from
   `src/middleware/rate_limit.py` as a FastAPI `Depends()` on the relevant route handlers.
6. THE Event_Management_System SHALL apply a rate limit of 60 requests per minute per IP address
   to the `GET /api/v1/events/admin/all` admin list endpoint.

---

### Requirement 10: Test Suite

**User Story:** As a developer, I want a comprehensive test suite for the event management
module, so that regressions are caught automatically and the module meets the 80% service /
70% route coverage mandated by the constitution.

**Constitution reference:** §V — Test-first development; 80% coverage on services, 70% on
routes; pytest-asyncio + httpx ASGITransport; SQLite in-memory; zero real DB calls.

#### Acceptance Criteria

1. THE Event_Management_System SHALL provide a test file at
   `packages/backend/src/__tests__/test_events.py` using `pytest-asyncio` and
   `httpx.AsyncClient` with `ASGITransport`.
2. THE test suite SHALL use SQLite in-memory (`sqlite+aiosqlite:///:memory:`) via the existing
   `conftest.py` fixtures and SHALL make zero calls to a real PostgreSQL database.
3. THE test suite SHALL cover the following route-level scenarios:
   - `POST /events/` — success (201 + envelope), invalid event type (422), past start_date (422),
     end_date before start_date (422), rate limit exceeded (429)
   - `GET /events/` — success with pagination meta, status filter
   - `GET /events/{id}` — success, not found (404), wrong user (404)
   - `PUT /events/{id}` — success, invalid status transition (409), end_date before start_date (422)
   - `POST /events/{id}/cancel` — success, invalid transition (409)
   - `POST /events/{id}/duplicate` — success (201), source not found (404)
   - `GET /events/{id}/bookings` — success with pagination, empty list
   - `GET /events/admin/all` — admin success, non-admin 403
4. THE test suite SHALL cover the following EventService unit-level scenarios:
   - All valid status transitions succeed
   - All invalid status transitions raise HTTP 409 with `VALIDATION_INVALID_STATUS_TRANSITION`
   - `event.created` domain event is emitted on create
   - `event.status_changed` domain event is emitted on transition
   - `event.cancelled` domain event is emitted on cancel
   - Duplicate creates a new record with `status=draft` and `name="Copy of ..."`
5. THE test suite SHALL achieve at minimum 80% line coverage on `src/services/event_service.py`
   and 70% line coverage on `src/api/v1/events.py`.
6. THE test suite SHALL mock `event_bus.emit` to assert it is called with the correct
   `event_type` and payload keys, without requiring a real database `domain_events` table write.
7. WHEN running `pytest packages/backend/src/__tests__/test_events.py`, THE test suite SHALL
   pass with zero failures and zero errors.

---

### Requirement 11: EventType Response Envelope Compliance

**User Story:** As a frontend developer, I want the event type management endpoints to also
return the standard response envelope, so that my API client layer is consistent across all
endpoints.

**Constitution reference:** §VI.2 — All responses follow the standardised envelope.

#### Acceptance Criteria

1. THE Event_Management_System SHALL wrap the `GET /api/v1/events/types` response in
   `{"success": true, "data": [<EventTypeRead>, ...], "meta": {}}`.
2. THE Event_Management_System SHALL wrap the `POST /api/v1/events/types` response in
   `{"success": true, "data": <EventTypeRead>, "meta": {}}` with HTTP 201.
3. THE Event_Management_System SHALL wrap the `PUT /api/v1/events/types/{id}` response in
   `{"success": true, "data": <EventTypeRead>, "meta": {}}` with HTTP 200.
4. THE `DELETE /api/v1/events/types/{id}` endpoint SHALL return HTTP 204 with no body on
   success (no envelope required for 204 responses).
5. WHEN an event type is not found, THE Event_Management_System SHALL return HTTP 404 with
   `{"success": false, "error": {"code": "NOT_FOUND_EVENT_TYPE", "message": "Event type not found."}}`.
