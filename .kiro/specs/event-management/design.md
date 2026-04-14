# Design Document — Module 005: Event Management

## Overview

This document describes the technical design for closing the ten gaps identified in the Event
Management requirements. The existing skeleton (models, migrations, basic CRUD routes) is
retained and extended — no existing database schema changes are required.

The design introduces a dedicated `EventService` class following the established `BookingService`
pattern, a strict status-transition state machine, domain event emission via the existing
`EventBusService`, three new API endpoints, schema validation improvements, and a comprehensive
test suite.

**Target files:**

| File | Action |
|---|---|
| `src/services/event_service.py` | CREATE |
| `src/api/v1/events.py` | REFACTOR |
| `src/schemas/event.py` | UPDATE |
| `tests/test_event_service.py` | CREATE |
| `tests/test_event_routes.py` | CREATE |
| `tests/conftest.py` | UPDATE |

---

## Architecture

The module follows the layered architecture mandated by the platform constitution:

```
HTTP Request
    │
    ▼
┌─────────────────────────────────┐
│  src/api/v1/events.py           │  ← Thin route handlers only
│  (FastAPI Router)               │    Auth deps, rate limit deps,
│                                 │    envelope wrapping
└────────────────┬────────────────┘
                 │ calls
                 ▼
┌─────────────────────────────────┐
│  src/services/event_service.py  │  ← All business logic
│  (EventService)                 │    State machine, validation,
│                                 │    domain event emission
└────────────────┬────────────────┘
                 │ uses
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐  ┌───────────────────┐
│ SQLAlchemy   │  │ EventBusService   │
│ AsyncSession │  │ (event_bus.emit)  │
└──────────────┘  └───────────────────┘
        │
        ▼
┌──────────────┐
│  PostgreSQL  │
│  events      │
│  event_types │
│  bookings    │
│  domain_     │
│  events      │
└──────────────┘
```

**Key architectural decisions:**

- `EventService` is instantiated as a module-level singleton (`event_service = EventService()`)
  matching the `booking_service` pattern, so route handlers import and call it directly.
- Domain events are emitted inside the same `AsyncSession` transaction as the DB mutation
  (outbox pattern lite), ensuring atomicity.
- Rate limiting is applied per-route via `Depends(rate_limit_dependency(...))`, not as
  middleware, so individual endpoints can have different limits.

---

## Components and Interfaces

### EventService (`src/services/event_service.py`)

```python
class EventService:

    async def create_event(
        self, session: AsyncSession, event_in: EventCreate, user_id: uuid.UUID
    ) -> Event:
        """Validate event_type, create Event with status=PLANNED, emit event.created."""

    async def get_event(
        self, session: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> Event:
        """Return event if it exists and belongs to user_id, else raise 404."""

    async def list_events(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[EventStatus] = None,
    ) -> tuple[list[Event], int]:
        """Paginated list of events owned by user_id."""

    async def update_event(
        self, session: AsyncSession, event_id: uuid.UUID,
        event_in: EventUpdate, user_id: uuid.UUID
    ) -> Event:
        """Update mutable fields. Rejects if status is terminal. Validates dates."""

    async def cancel_event(
        self, session: AsyncSession, event_id: uuid.UUID,
        user_id: uuid.UUID, reason: Optional[str] = None
    ) -> Event:
        """Cancel event via state machine. Emits event.cancelled."""

    async def transition_status(
        self, session: AsyncSession, event: Event,
        new_status: EventStatus, user_id: uuid.UUID
    ) -> Event:
        """Apply validated status transition. Emits event.status_changed."""

    async def duplicate_event(
        self, session: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> Event:
        """Clone event with status=DRAFT, name='Copy of ...'. Emits event.created."""

    async def list_event_bookings(
        self,
        session: AsyncSession,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        status_filter: Optional[BookingStatus] = None,
    ) -> tuple[list[Booking], int]:
        """Paginated bookings for an event owned by user_id."""

    async def list_all_events_admin(
        self,
        session: AsyncSession,
        page: int = 1,
        limit: int = 20,
        status: Optional[EventStatus] = None,
        user_id: Optional[uuid.UUID] = None,
        city: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> tuple[list[Event], int]:
        """Admin: all events across all users with optional filters."""
```

### Route Handlers (`src/api/v1/events.py`)

All handlers follow this pattern — no business logic, only:
1. Resolve dependencies (auth, session, rate limiter)
2. Call the appropriate `EventService` method
3. Wrap result in the response envelope

New routes added:

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| `POST` | `/events/{id}/duplicate` | `get_current_user` | 10/min |
| `GET` | `/events/{id}/bookings` | `get_current_user` | 60/min |
| `GET` | `/events/admin/all` | `require_admin` | 60/min |
| `PATCH` | `/events/{id}/status` | `get_current_user` | 60/min |

Existing routes refactored to use `EventService` and return envelopes.

### Schema Updates (`src/schemas/event.py`)

**`EventCreate`** — add cross-field validator:
```python
@model_validator(mode="after")
def end_date_after_start(self) -> "EventCreate":
    if self.end_date and self.end_date <= self.start_date:
        raise ValueError("end_date must be after start_date")
    return self
```

**`EventUpdate`** — add two validators:
```python
@field_validator("start_date")
@classmethod
def start_date_must_be_future(cls, v):
    if v and v <= datetime.now(timezone.utc):
        raise ValueError("start_date must be in the future")
    return v

@model_validator(mode="after")
def end_date_after_start(self) -> "EventUpdate":
    if self.start_date and self.end_date and self.end_date <= self.start_date:
        raise ValueError("end_date must be after start_date")
    return self
```

**New schema `EventStatusUpdate`**:
```python
class EventStatusUpdate(BaseModel):
    status: EventStatus
    reason: Optional[str] = Field(None, max_length=500)
```

---

## Data Models

No schema migrations required. The existing `events` and `event_types` tables are used as-is.

### State Machine

```python
VALID_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    EventStatus.DRAFT:    {EventStatus.PLANNED, EventStatus.CANCELED},
    EventStatus.PLANNED:  {EventStatus.ACTIVE,  EventStatus.CANCELED},
    EventStatus.ACTIVE:   {EventStatus.COMPLETED, EventStatus.CANCELED},
}

TERMINAL_STATUSES: set[EventStatus] = {
    EventStatus.COMPLETED,
    EventStatus.CANCELED,
}
```

Transition diagram:

```
DRAFT ──────────────────────────────────────────► CANCELED
  │                                                   ▲
  ▼                                                   │
PLANNED ──────────────────────────────────────────────┤
  │                                                   │
  ▼                                                   │
ACTIVE ────────────────────────────────────────────────┤
  │
  ▼
COMPLETED
```

`transition_status` logic:
1. Check `new_status in TERMINAL_STATUSES` — if current is terminal, raise 409
   `VALIDATION_INVALID_STATUS_TRANSITION`
2. Check `new_status in VALID_TRANSITIONS.get(current, set())` — if not, raise 409
   `VALIDATION_INVALID_STATUS_TRANSITION` with message
   `"Cannot transition from '{current}' to '{new_status}'"`
3. Set `event.status = new_status`, `event.updated_at = now()`
4. If `new_status == CANCELED`: set `event.canceled_at`, `event.cancellation_reason`
5. Emit domain event
6. `await session.commit()` + `await session.refresh(event)`

### Domain Event Payloads

**`event.created`**
```json
{
  "event_id": "<uuid>",
  "user_id": "<uuid>",
  "event_type_id": "<uuid>",
  "name": "<string>",
  "start_date": "<ISO-8601>",
  "status": "planned"
}
```

**`event.status_changed`**
```json
{
  "event_id": "<uuid>",
  "user_id": "<uuid>",
  "old_status": "<string>",
  "new_status": "<string>"
}
```

**`event.cancelled`**
```json
{
  "event_id": "<uuid>",
  "user_id": "<uuid>",
  "reason": "<string | null>",
  "canceled_at": "<ISO-8601>"
}
```

### `list_event_bookings` Query Strategy

To avoid N+1 queries, `list_event_bookings` uses a single `select(Booking)` with a
`WHERE booking.event_id = :event_id` filter. The `Booking` model already has an `event_id`
foreign key. No ORM relationship traversal is needed — this is a direct filtered query.

### `list_all_events_admin` Query Composition

Filters are applied conditionally using SQLAlchemy query composition:

```python
stmt = select(Event)
if status:
    stmt = stmt.where(Event.status == status)
if user_id:
    stmt = stmt.where(Event.user_id == user_id)
if city:
    stmt = stmt.where(Event.city.ilike(f"%{city}%"))
if date_from:
    stmt = stmt.where(Event.start_date >= date_from)
if date_to:
    stmt = stmt.where(Event.start_date <= date_to)
```

A separate `count_stmt` mirrors the same filters for the `meta.total` value.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions
of a system — essentially, a formal statement about what the system should do. Properties serve
as the bridge between human-readable specifications and machine-verifiable correctness
guarantees.*

### Property 1: State Machine Completeness

*For any* event in any non-terminal status, attempting a transition that is not listed in
`VALID_TRANSITIONS` for that status SHALL raise HTTP 409 with code
`VALIDATION_INVALID_STATUS_TRANSITION`, and attempting a listed transition SHALL succeed.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

### Property 2: Terminal Status Blocks Updates

*For any* event whose status is `completed` or `canceled`, calling `update_event` with any
field payload SHALL raise HTTP 409 with code `VALIDATION_INVALID_STATUS_TRANSITION`.

**Validates: Requirements 3.6**

### Property 3: event.created Emitted with Correct Payload

*For any* valid `EventCreate` input, after `create_event` completes successfully,
`event_bus.emit` SHALL have been called exactly once with `event_type="event.created"` and a
payload containing all of the keys: `event_id`, `user_id`, `event_type_id`, `name`,
`start_date`, `status`.

**Validates: Requirements 4.1, 4.2**

### Property 4: event.status_changed Emitted with Correct Payload

*For any* valid status transition via `transition_status`, `event_bus.emit` SHALL have been
called with `event_type="event.status_changed"` and a payload containing all of the keys:
`event_id`, `user_id`, `old_status`, `new_status`.

**Validates: Requirements 4.3, 4.4**

### Property 5: event.cancelled Emitted with Correct Payload

*For any* event in a cancelable status (`draft`, `planned`, `active`), after `cancel_event`
completes successfully, `event_bus.emit` SHALL have been called with
`event_type="event.cancelled"` and a payload containing all of the keys: `event_id`, `user_id`,
`reason`, `canceled_at`.

**Validates: Requirements 4.5, 4.6**

### Property 6: Past start_date Rejected in EventUpdate

*For any* datetime value that is at or before the current UTC time, constructing an
`EventUpdate` with that `start_date` SHALL raise a `ValidationError` with a message containing
`"start_date must be in the future"`.

**Validates: Requirements 5.1, 5.5**

### Property 7: end_date Before start_date Rejected

*For any* pair of datetimes `(start, end)` where `end <= start`, constructing an `EventCreate`
or `EventUpdate` with both values SHALL raise a `ValidationError` with a message containing
`"end_date must be after start_date"`.

**Validates: Requirements 5.2**

### Property 8: Duplicate Produces Correct Field Values

*For any* source event owned by a user, calling `duplicate_event` SHALL produce a new event
where: `name == "Copy of " + source.name`, `status == EventStatus.DRAFT`,
`id != source.id`, `user_id == source.user_id`, `cancellation_reason is None`,
`canceled_at is None`, and all other scalar fields equal the source event's values.

**Validates: Requirements 7.2, 7.5, 7.6**

---

## Error Handling

All errors follow the constitution §VI.6 envelope:
```json
{"success": false, "error": {"code": "<CODE>", "message": "<human-readable>"}}
```

| Scenario | HTTP | Code |
|---|---|---|
| Event not found or wrong user | 404 | `NOT_FOUND_EVENT` |
| EventType not found or inactive | 422 | `VALIDATION_INVALID_EVENT_TYPE` |
| EventType not found (CRUD) | 404 | `NOT_FOUND_EVENT_TYPE` |
| EventType name already exists | 409 | `CONFLICT_EVENT_TYPE_EXISTS` |
| EventType in use by active events | 409 | `CONFLICT_EVENT_TYPE_IN_USE` |
| Invalid status transition | 409 | `VALIDATION_INVALID_STATUS_TRANSITION` |
| end_date before start_date | 422 | `VALIDATION_END_DATE_BEFORE_START` |
| start_date not in future | 422 | `VALIDATION_INVALID_DATE` |
| Non-admin accessing admin endpoint | 403 | `AUTH_FORBIDDEN` |
| Rate limit exceeded | 429 | — (Retry-After header set) |

The `_err(code, message)` helper (matching `BookingService` pattern) is used throughout
`EventService` to construct consistent error detail dicts.

---

## Testing Strategy

### Test Files

| File | Scope |
|---|---|
| `tests/test_event_service.py` | Unit tests for `EventService` (mocked session + event bus) |
| `tests/test_event_routes.py` | HTTP integration tests via `AsyncClient` + `ASGITransport` |
| `tests/conftest.py` | Updated to include `event_types` and `events` tables |

### conftest.py Updates

Add `event_types` and `events` to the `AUTH_TABLES` list (renamed to `TEST_TABLES`) so
SQLite creates those tables for integration tests. Import the models to register them with
`SQLModel.metadata`:

```python
from src.models.event import Event, EventType  # noqa: F401
```

Also add a `no_rate_limit` override for the event route limiters in the `client` fixture.

### Unit Tests (`test_event_service.py`)

Use `AsyncMock` for the session and `patch("src.services.event_service.event_bus.emit")` to
intercept domain event calls. No real DB required.

Scenarios:
- All 6 valid transitions succeed (one test per transition)
- All invalid transitions raise 409 `VALIDATION_INVALID_STATUS_TRANSITION`
- Terminal status (completed, canceled) blocks further transitions
- `create_event` emits `event.created` with correct payload keys
- `transition_status` emits `event.status_changed` with correct payload keys
- `cancel_event` emits `event.cancelled` with correct payload keys
- `duplicate_event` creates record with `status=DRAFT`, `name="Copy of ..."`, no bookings
- `update_event` on terminal-status event raises 409
- `get_event` with wrong `user_id` raises 404

### Integration Tests (`test_event_routes.py`)

Use `AsyncClient` with `ASGITransport(app=app)` and the `db_session` fixture. Create a test
user and obtain a JWT token via `POST /api/v1/auth/login` in a fixture.

Route scenarios:
- `POST /events/` — 201 + envelope, invalid event type (422), past start_date (422),
  end_date before start_date (422)
- `GET /events/` — 200 + pagination meta, status filter
- `GET /events/{id}` — 200, 404 not found, 404 wrong user
- `PUT /events/{id}` — 200, 409 terminal status, 422 end_date before start_date
- `POST /events/{id}/cancel` — 200, 409 invalid transition
- `POST /events/{id}/duplicate` — 201 + envelope, 404 source not found
- `GET /events/{id}/bookings` — 200 + pagination, empty list
- `GET /events/admin/all` — 200 as admin, 403 as regular user
- `GET /events/types` — 200 + envelope
- `POST /events/types` — 201 + envelope (admin), 409 duplicate name
- Rate limit: verify 429 + `Retry-After` header when limit exceeded

### Property-Based Tests

Use **`hypothesis`** (Python PBT library) for the 8 correctness properties above.

Each property test is configured with `@settings(max_examples=100)` and tagged with a comment:
```python
# Feature: event-management, Property N: <property_text>
```

Property test strategy:
- **Properties 1–2** (state machine): Use `hypothesis.strategies.sampled_from(EventStatus)` to
  generate source and target statuses. Build a mock `Event` with the generated source status.
  Verify transition outcome matches `VALID_TRANSITIONS`.
- **Properties 3–5** (domain events): Use `hypothesis.strategies` to generate valid event field
  values (names, dates, UUIDs). Mock `event_bus.emit` with `AsyncMock`. Verify call args.
- **Properties 6–7** (date validation): Use `hypothesis.strategies.datetimes()` with
  `allow_imaginary=False` to generate past datetimes (Property 6) and date pairs where
  `end <= start` (Property 7). Verify `ValidationError` is raised.
- **Property 8** (duplicate): Use `hypothesis.strategies` to generate source event field values.
  Mock session. Verify the new event's fields match expectations.

Coverage targets:
- `src/services/event_service.py`: ≥ 80% line coverage
- `src/api/v1/events.py`: ≥ 70% line coverage
