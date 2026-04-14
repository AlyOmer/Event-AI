# Requirements Document

## Introduction

Module 010 — Notification System gaps for the Event-AI platform. The existing implementation handles booking domain events and delivers real-time notifications via SSE. This spec covers the ten missing capabilities: event and vendor domain event notifications, delete endpoints, rate limiting, response envelope consistency, event bus subscriptions, test coverage, SSE queue overflow handling, and per-user notification preferences.

All requirements target the `packages/backend` FastAPI service. The existing `Notification` SQLModel, `NotificationService`, `SSEConnectionManager`, and REST routes are already in production and are NOT re-specified here.

---

## Glossary

- **Notification_Service**: The `NotificationService` class in `notification_service.py` that handles domain events and persists `Notification` rows.
- **SSE_Manager**: The `SSEConnectionManager` singleton stored on `app.state` that manages per-user asyncio queues and pushes real-time events.
- **Event_Bus**: The in-process `EventEmitter` (`event_bus_service.py`) used for domain event fan-out.
- **Notification_Router**: The FastAPI `APIRouter` mounted at `/api/v1/notifications`.
- **NotificationType**: The `NotificationType` Python enum in `models/notification.py`.
- **Preference_Service**: The new service responsible for reading and writing per-user `NotificationPreference` rows.
- **Rate_Limiter**: The slowapi/fastapi-limiter middleware applied per-endpoint.
- **Response_Envelope**: The standard JSON shape `{"success": true, "data": ..., "meta": {}}` mandated by constitution §VI.
- **Dead_Letter_Store**: A persistent record of SSE push failures for audit and replay, as required by constitution §III.8.

---

## Requirements

### Requirement 1: Event Domain Event Notifications

**User Story:** As a platform user, I want to receive notifications when events I am associated with are created, change status, or are cancelled, so that I stay informed about my event lifecycle without polling.

#### Acceptance Criteria

1. THE `NotificationType` SHALL include the values `event_created`, `event_status_changed`, and `event_cancelled`.
2. WHEN the `Event_Bus` emits an `event.created` domain event, THE `Notification_Service` SHALL create a `Notification` row of type `event_created` for the event owner's `user_id`.
3. WHEN the `Event_Bus` emits an `event.status_changed` domain event, THE `Notification_Service` SHALL create a `Notification` row of type `event_status_changed` for the event owner's `user_id`.
4. WHEN the `Event_Bus` emits an `event.cancelled` domain event, THE `Notification_Service` SHALL create a `Notification` row of type `event_cancelled` for the event owner's `user_id`.
5. WHEN a notification is created for an event domain event, THE `Notification_Service` SHALL push the notification payload to the `SSE_Manager` for the recipient's open connections.
6. IF the `event.created`, `event.status_changed`, or `event.cancelled` payload does not contain a resolvable `user_id`, THEN THE `Notification_Service` SHALL log a structured warning via structlog and return without creating a `Notification` row.

---

### Requirement 2: Vendor Domain Event Notifications

**User Story:** As a vendor, I want to receive notifications when my vendor account is approved or rejected by an admin, so that I know when I can start accepting bookings.

#### Acceptance Criteria

1. THE `NotificationType` SHALL include the values `vendor_approved` and `vendor_rejected`.
2. WHEN the `Event_Bus` emits a `vendor.approved` domain event, THE `Notification_Service` SHALL create a `Notification` row of type `vendor_approved` for the vendor's `user_id`.
3. WHEN the `Event_Bus` emits a `vendor.rejected` domain event, THE `Notification_Service` SHALL create a `Notification` row of type `vendor_rejected` for the vendor's `user_id`.
4. WHEN a vendor notification is created, THE `Notification_Service` SHALL push the notification payload to the `SSE_Manager` for the vendor's open connections.
5. IF the `vendor.approved` or `vendor.rejected` payload does not contain a resolvable `user_id`, THEN THE `Notification_Service` SHALL log a structured warning via structlog and return without creating a `Notification` row.

---

### Requirement 3: Delete Single Notification Endpoint

**User Story:** As a user, I want to delete a specific notification, so that I can keep my notification list clean.

#### Acceptance Criteria

1. THE `Notification_Router` SHALL expose a `DELETE /api/v1/notifications/{notification_id}` endpoint protected by JWT authentication.
2. WHEN a `DELETE` request is received for a notification that belongs to the authenticated user, THE `Notification_Router` SHALL delete the row and return `{"success": true, "data": null, "meta": {}}` with HTTP 200.
3. IF the notification identified by `notification_id` does not exist, THEN THE `Notification_Router` SHALL return HTTP 404 with error code `NOT_FOUND_NOTIFICATION`.
4. IF the notification identified by `notification_id` belongs to a different user, THEN THE `Notification_Router` SHALL return HTTP 403 with error code `AUTH_FORBIDDEN`.

---

### Requirement 4: Bulk Delete Read Notifications Endpoint

**User Story:** As a user, I want to delete all my already-read notifications in one action, so that I can clear my notification history efficiently.

#### Acceptance Criteria

1. THE `Notification_Router` SHALL expose a `DELETE /api/v1/notifications/read` endpoint protected by JWT authentication.
2. WHEN a `DELETE /api/v1/notifications/read` request is received, THE `Notification_Router` SHALL delete all `Notification` rows where `user_id` matches the authenticated user and `is_read` is `true`.
3. WHEN the bulk delete completes, THE `Notification_Router` SHALL return `{"success": true, "data": {"deleted": <count>}, "meta": {}}` with HTTP 200.
4. WHEN no read notifications exist for the user, THE `Notification_Router` SHALL return `{"success": true, "data": {"deleted": 0}, "meta": {}}` with HTTP 200.

---

### Requirement 5: Rate Limiting on Notification Endpoints

**User Story:** As a platform operator, I want notification endpoints to enforce rate limits, so that the API is protected from abuse in accordance with the platform security constitution.

#### Acceptance Criteria

1. THE `Notification_Router` SHALL apply a rate limit of 60 requests per minute per authenticated user to all read endpoints: `GET /notifications/`, `GET /notifications/unread-count`.
2. THE `Notification_Router` SHALL apply a rate limit of 10 requests per minute per authenticated user to all write endpoints: `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all`, `DELETE /notifications/{id}`, `DELETE /notifications/read`.
3. WHEN a request exceeds the applicable rate limit, THE `Notification_Router` SHALL return HTTP 429 with a structured error response containing error code `RATE_LIMIT_EXCEEDED`.
4. THE `Rate_Limiter` SHALL use the authenticated user's `user_id` as the rate limit key, not the client IP address.

---

### Requirement 6: Response Envelope on mark_read Endpoint

**User Story:** As an API consumer, I want all notification endpoints to return the standard response envelope, so that client-side response handling is consistent.

#### Acceptance Criteria

1. WHEN `PATCH /api/v1/notifications/{notification_id}/read` succeeds, THE `Notification_Router` SHALL return `{"success": true, "data": <NotificationRead>, "meta": {}}` with HTTP 200.
2. THE `Notification_Router` SHALL NOT return a raw `NotificationRead` model directly as the response body for the `mark_read` endpoint.
3. WHEN `PATCH /api/v1/notifications/{notification_id}/read` encounters a 404 or 403 error, THE `Notification_Router` SHALL return `{"success": false, "error": {"code": "<ERROR_CODE>", "message": "<message>"}}`.

---

### Requirement 7: Event Bus Subscriptions for Event Domain Events

**User Story:** As a platform operator, I want the notification service to be subscribed to all required domain events at application startup, so that no events are silently dropped.

#### Acceptance Criteria

1. WHEN the FastAPI application starts, THE `lifespan` function SHALL subscribe `notification_service.handle` to the `event.created` domain event on the `Event_Bus`.
2. WHEN the FastAPI application starts, THE `lifespan` function SHALL subscribe `notification_service.handle` to the `event.status_changed` domain event on the `Event_Bus`.
3. WHEN the FastAPI application starts, THE `lifespan` function SHALL subscribe `notification_service.handle` to the `event.cancelled` domain event on the `Event_Bus`.
4. WHEN the FastAPI application starts, THE `lifespan` function SHALL subscribe `notification_service.handle` to the `vendor.approved` domain event on the `Event_Bus`.
5. WHEN the FastAPI application starts, THE `lifespan` function SHALL subscribe `notification_service.handle` to the `vendor.rejected` domain event on the `Event_Bus`.
6. THE `lifespan` function SHALL register all notification subscriptions before yielding control to the application.

---

### Requirement 8: Notification Module Test Suite

**User Story:** As a developer, I want a comprehensive test suite for the notification module, so that regressions are caught and the 80% service / 70% route coverage thresholds mandated by the constitution are met.

#### Acceptance Criteria

1. THE test suite SHALL use `pytest-asyncio` with `httpx.AsyncClient` and `ASGITransport` for all route tests, with an in-memory SQLite database.
2. THE test suite SHALL cover `NotificationService.handle()` for all booking event types (`booking.created`, `booking.confirmed`, `booking.cancelled`, `booking.completed`, `booking.rejected`, `booking.status_changed`).
3. THE test suite SHALL cover `NotificationService.handle()` for all new event types (`event.created`, `event.status_changed`, `event.cancelled`) and vendor types (`vendor.approved`, `vendor.rejected`).
4. THE test suite SHALL cover `NotificationService.list_notifications()`, `unread_count()`, `mark_read()`, and `mark_all_read()` with both happy-path and error cases.
5. THE test suite SHALL cover all six `Notification_Router` endpoints: `GET /`, `GET /unread-count`, `PATCH /read-all`, `PATCH /{id}/read`, `DELETE /{id}`, `DELETE /read`.
6. THE test suite SHALL verify that `PATCH /{id}/read` returns the `Response_Envelope` shape.
7. THE test suite SHALL verify that `DELETE /{id}` returns HTTP 404 for a non-existent notification and HTTP 403 for a notification owned by a different user.
8. FOR ALL `NotificationService.handle()` calls with a valid session and a known event type, THE `Notification_Service` SHALL create exactly one `Notification` row per call (idempotency of row creation given unique inputs).
9. THE test suite SHALL be runnable with `uv run pytest packages/backend/tests/test_notifications.py -v`.

---

### Requirement 9: SSE Queue Overflow Handling

**User Story:** As a platform operator, I want SSE queue overflow to be handled gracefully with a configurable drop policy and structured logging, so that message loss is observable and the system remains stable under load.

#### Acceptance Criteria

1. WHEN `SSE_Manager.push()` encounters a full queue for a connection, THE `SSE_Manager` SHALL log a structured warning via structlog including `user_id`, `event_type`, and `queue_size`.
2. WHEN `SSE_Manager.push()` encounters a full queue, THE `SSE_Manager` SHALL attempt to evict the oldest message from the queue before inserting the new message, preserving the most recent event.
3. WHEN a message is evicted due to queue overflow, THE `SSE_Manager` SHALL increment a per-user dropped message counter accessible via `SSE_Manager.dropped_count(user_id)`.
4. IF `SSE_Manager.push()` fails to insert a message after eviction, THEN THE `SSE_Manager` SHALL log a structured error via structlog and return without raising an exception.
5. THE `SSE_Manager` queue `maxsize` SHALL be configurable via the `Settings` model with a default value of 50.

---

### Requirement 10: Per-User Notification Preferences

**User Story:** As a user, I want to opt out of specific notification types, so that I only receive notifications that are relevant to me.

#### Acceptance Criteria

1. THE system SHALL provide a `NotificationPreference` SQLModel table with columns: `id` (UUID PK), `user_id` (UUID, indexed), `notification_type` (`NotificationType`), `enabled` (bool, default `true`), `created_at` (datetime), `updated_at` (datetime).
2. THE `Notification_Router` SHALL expose `GET /api/v1/notifications/preferences` to return all preference rows for the authenticated user, wrapped in the `Response_Envelope`.
3. THE `Notification_Router` SHALL expose `PUT /api/v1/notifications/preferences/{notification_type}` to upsert a preference row for the authenticated user, accepting `{"enabled": bool}` in the request body.
4. WHEN `Notification_Service.handle()` is about to create a `Notification` row, THE `Notification_Service` SHALL query the `NotificationPreference` table for the recipient's preference for that `notification_type`.
5. WHILE a user's preference for a given `notification_type` has `enabled = false`, THE `Notification_Service` SHALL skip creating the `Notification` row and skip the SSE push for that type.
6. WHERE no preference row exists for a user and notification type, THE `Notification_Service` SHALL default to `enabled = true` (opt-in by default).
7. THE `Preference_Service` SHALL expose `get_preferences(session, user_id)` and `upsert_preference(session, user_id, notification_type, enabled)` methods.
8. WHEN `PUT /api/v1/notifications/preferences/{notification_type}` is called with an invalid `notification_type` value, THE `Notification_Router` SHALL return HTTP 422 with a validation error.
