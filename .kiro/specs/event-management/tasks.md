# Tasks: Module 005 — Event Management

**Spec**: `.kiro/specs/event-management/`

---

## Task List

- [x] 1. Update Pydantic Schemas
  - [x] 1.1 Add `end_date > start_date` cross-field `model_validator` to `EventCreate` in `src/schemas/event.py` (Req 5.2)
  - [x] 1.2 Add `start_date` future-date `field_validator` to `EventUpdate` in `src/schemas/event.py` (Req 5.1, 5.5)
  - [x] 1.3 Add `end_date > start_date` cross-field `model_validator` to `EventUpdate` in `src/schemas/event.py` (Req 5.2, 5.3)
  - [x] 1.4 Add `EventStatusUpdate` schema `{status: EventStatus, reason: Optional[str]}` to `src/schemas/event.py` (Req 3.5)

- [x] 2. Create EventService
  - [x] 2.1 Create `src/services/event_service.py` with `VALID_TRANSITIONS` dict and `TERMINAL_STATUSES` set (Req 3.1)
  - [x] 2.2 Implement `create_event(session, event_in, user_id)` — validates event_type, creates Event with status=PLANNED, emits `event.created` (Req 2, 4.1, 4.2)
  - [x] 2.3 Implement `get_event(session, event_id, user_id)` — returns event or raises 404 `NOT_FOUND_EVENT` (Req 1.4, 1.5)
  - [x] 2.4 Implement `list_events(session, user_id, page, limit, status_filter)` — paginated, returns `(list[Event], int)` (Req 1.2)
  - [x] 2.5 Implement `update_event(session, event_id, event_in, user_id)` — rejects terminal status with 409 `VALIDATION_INVALID_STATUS_TRANSITION` (Req 3.6)
  - [x] 2.6 Implement `transition_status(session, event, new_status, user_id)` — enforces state machine, emits `event.status_changed` (Req 3, 4.3, 4.4)
  - [x] 2.7 Implement `cancel_event(session, event_id, user_id, reason)` — uses `transition_status`, sets `canceled_at`, emits `event.cancelled` (Req 4.5, 4.6)
  - [x] 2.8 Implement `duplicate_event(session, event_id, user_id)` — clones with `status=DRAFT`, `name="Copy of ..."`, emits `event.created` (Req 7)
  - [x] 2.9 Implement `list_event_bookings(session, event_id, user_id, page, limit, status_filter)` — direct filtered query on `Booking.event_id`, no N+1 (Req 6)
  - [x] 2.10 Implement `list_all_events_admin(session, page, limit, status, user_id, city, date_from, date_to)` — composable filters, separate count query (Req 8)

- [x] 3. Refactor Event Routes — Envelope + EventService
  - [x] 3.1 Refactor `GET /events/types` to call EventService and return `{"success": true, "data": [...], "meta": {}}` (Req 1.3, 11.1)
  - [x] 3.2 Refactor `POST /events/types` to call EventService and return 201 envelope (Req 11.2)
  - [x] 3.3 Refactor `PUT /events/types/{id}` to call EventService and return 200 envelope (Req 11.3)
  - [x] 3.4 Refactor `POST /events/` to call `event_service.create_event`, return 201 envelope, add `rate_limit_dependency(10, 60)` (Req 1.1, 1.6, 9.1)
  - [x] 3.5 Refactor `GET /events/` to call `event_service.list_events`, return paginated envelope (Req 1.2)
  - [x] 3.6 Refactor `GET /events/{id}` to call `event_service.get_event`, return 200 envelope, add `rate_limit_dependency(60, 60)` (Req 1.1, 9.3)
  - [x] 3.7 Refactor `PUT /events/{id}` to call `event_service.update_event`, return 200 envelope (Req 1.1)
  - [x] 3.8 Refactor `DELETE /events/{id}` (cancel) to call `event_service.cancel_event`, return 200 envelope (Req 1.1)

- [x] 4. Add New Routes
  - [x] 4.1 Add `PATCH /events/{id}/status` — calls `event_service.transition_status`, returns 200 envelope, accepts `EventStatusUpdate` body (Req 3.5)
  - [x] 4.2 Add `POST /events/{id}/duplicate` — calls `event_service.duplicate_event`, returns 201 envelope, add `rate_limit_dependency(10, 60)` (Req 7, 9.2)
  - [x] 4.3 Add `GET /events/{id}/bookings` — calls `event_service.list_event_bookings`, returns paginated envelope, add `rate_limit_dependency(60, 60)` (Req 6, 9.3)
  - [x] 4.4 Add `GET /events/admin/all` — calls `event_service.list_all_events_admin`, protected by `require_admin`, returns paginated envelope, add `rate_limit_dependency(60, 60)` (Req 8, 9.6)

- [x] 5. Update Test Fixtures
  - [x] 5.1 Add `from src.models.event import Event, EventType` import to `tests/conftest.py` to register models with SQLModel metadata (Req 10.2)
  - [x] 5.2 Add `"event_types"` and `"events"` to the `TEST_TABLES` list in `tests/conftest.py` (Req 10.2)
  - [x] 5.3 Add event route rate limiter overrides to the `client` fixture in `tests/conftest.py` (Req 10.2)

- [-] 6. Write EventService Unit Tests
  - [x] 6.1 Create `tests/test_event_service.py` with fixtures for mock session and patched `event_bus.emit` (Req 10.1, 10.6)
  - [x] 6.2 Test all 6 valid status transitions succeed (Req 10.4)
  - [x] 6.3 Test all invalid status transitions raise HTTP 409 `VALIDATION_INVALID_STATUS_TRANSITION` (Req 10.4)
  - [x] 6.4 Test terminal status blocks `update_event` with 409 (Req 10.4)
  - [x] 6.5 Test `create_event` emits `event.created` with correct payload keys (Req 10.4)
  - [x] 6.6 Test `transition_status` emits `event.status_changed` with correct payload keys (Req 10.4)
  - [x] 6.7 Test `cancel_event` emits `event.cancelled` with correct payload keys (Req 10.4)
  - [x] 6.8 Test `duplicate_event` produces `status=DRAFT`, `name="Copy of ..."`, new id (Req 10.4)
  - [x] 6.9 Test `get_event` with wrong `user_id` raises 404 (Req 10.4)

- [x] 7. Write Event Route Integration Tests
  - [x] 7.1 Create `tests/test_event_routes.py` with auth fixture (register user, get token) (Req 10.1)
  - [x] 7.2 Test `POST /events/` — 201 + envelope, invalid event type (422), past start_date (422), end_date before start_date (422) (Req 10.3)
  - [x] 7.3 Test `GET /events/` — 200 + pagination meta, status filter works (Req 10.3)
  - [x] 7.4 Test `GET /events/{id}` — 200, 404 not found, 404 wrong user (Req 10.3)
  - [x] 7.5 Test `PUT /events/{id}` — 200, 409 terminal status, 422 end_date before start_date (Req 10.3)
  - [x] 7.6 Test `POST /events/{id}/cancel` — 200, 409 invalid transition (Req 10.3)
  - [x] 7.7 Test `POST /events/{id}/duplicate` — 201 + envelope, 404 source not found (Req 10.3)
  - [x] 7.8 Test `GET /events/{id}/bookings` — 200 + pagination, empty list (Req 10.3)
  - [x] 7.9 Test `GET /events/admin/all` — 200 as admin, 403 as regular user (Req 10.3)
  - [x] 7.10 Test `GET /events/types` — 200 + envelope (Req 10.3)
  - [x] 7.11 Test `POST /events/types` — 201 + envelope (admin), 409 duplicate name (Req 10.3)
