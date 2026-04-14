# Tasks — Notification System (Module 010 Gaps)

## Task List

- [x] 1. Extend NotificationType enum and Alembic migration
  - [x] 1.1 Add `event_created`, `event_status_changed`, `event_cancelled`, `vendor_approved`, `vendor_rejected` to `NotificationType` in `packages/backend/src/models/notification.py`
  - [x] 1.2 Generate Alembic migration `add_notification_types_event_vendor` that adds the five new values to the Postgres ENUM type used by the `notifications.type` column
  - [x] 1.3 Verify migration applies cleanly with `uv run alembic upgrade head` against a local/test DB

- [x] 2. Extend _EVENT_MAP and handle() for event and vendor domain events
  - [x] 2.1 Add five new entries to `_EVENT_MAP` in `packages/backend/src/services/notification_service.py` for `event.created`, `event.status_changed`, `event.cancelled`, `vendor.approved`, `vendor.rejected`
  - [x] 2.2 Update `handle()` to resolve `user_id` from the payload directly for event/vendor events (not via ORM lookup)
  - [x] 2.3 Add early-return guard in `handle()` that logs a structlog warning when `user_id` cannot be resolved from the payload

- [-] 3. Add DELETE /notifications/{id} endpoint
  - [x] 3.1 Add `delete_notification` route to `packages/backend/src/api/v1/notifications.py` returning the standard `Response_Envelope`
  - [x] 3.2 Raise HTTP 404 with `NOT_FOUND_NOTIFICATION` when the notification does not exist
  - [x] 3.3 Raise HTTP 403 with `AUTH_FORBIDDEN` when the notification belongs to a different user

- [ ] 4. Add DELETE /notifications/read endpoint
  - [x] 4.1 Add `delete_read_notifications` route to `notifications.py` using a bulk `DELETE` statement scoped to `current_user.id` and `is_read == True`
  - [x] 4.2 Register the `/read` route before `/{notification_id}` in the router to prevent path parameter collision
  - [x] 4.3 Return `{"success": true, "data": {"deleted": <count>}, "meta": {}}` including when count is 0

- [ ] 5. Apply rate limiting to notification endpoints
  - [x] 5.1 Add `slowapi` to `packages/backend/pyproject.toml` dependencies if not already present
  - [x] 5.2 Create a `_user_key` function that extracts `user_id` from the authenticated request for use as the rate limit key
  - [x] 5.3 Apply `@limiter.limit("60/minute")` to `GET /notifications/` and `GET /notifications/unread-count`
  - [x] 5.4 Apply `@limiter.limit("10/minute")` to `PATCH /{id}/read`, `PATCH /read-all`, `DELETE /{id}`, `DELETE /read`
  - [x] 5.5 Register `SlowAPIMiddleware` on the FastAPI app and handle `RateLimitExceeded` to return HTTP 429 with `RATE_LIMIT_EXCEEDED` error code

- [ ] 6. Fix mark_read response envelope
  - [x] 6.1 Remove `response_model=NotificationRead` from the `mark_read` route decorator in `notifications.py`
  - [x] 6.2 Return `{"success": True, "data": NotificationRead.model_validate(notif), "meta": {}}` from `mark_read`

- [ ] 7. Add event.* and vendor.* subscriptions in lifespan
  - [x] 7.1 Extend the subscription loop in `packages/backend/src/config/database.py` lifespan to include `event.created`, `event.status_changed`, `event.cancelled`, `vendor.approved`, `vendor.rejected`

- [ ] 8. Write notification module test suite
  - [x] 8.1 Create `packages/backend/tests/test_notifications.py` with async fixtures: `async_client` (SQLite in-memory), `auth_headers`, `other_auth_headers`, `sample_notification`
  - [x] 8.2 Write service unit tests for `handle()` covering all booking event types (6 tests)
  - [x] 8.3 Write service unit tests for `handle()` covering all new event and vendor event types (5 tests)
  - [x] 8.4 Write service unit tests for `list_notifications()`, `unread_count()`, `mark_read()` (happy path + 404 + 403), `mark_all_read()`
  - [x] 8.5 Write route integration tests for `GET /`, `GET /unread-count`, `PATCH /read-all`, `PATCH /{id}/read` (verify envelope shape)
  - [x] 8.6 Write route integration tests for `DELETE /{id}` (success, 404, 403) and `DELETE /read` (success, zero-count case)
  - [x] 8.7 Write route integration tests for `GET /preferences` and `PUT /preferences/{type}` (success and 422 for invalid type)
  - [x] 8.8 Write property test: for all keys in `_EVENT_MAP`, `handle()` with a valid session and resolvable `user_id` creates exactly one `Notification` row
  - [x] 8.9 Verify test suite passes with `uv run pytest packages/backend/tests/test_notifications.py -v`

- [ ] 9. Improve SSE queue overflow handling
  - [x] 9.1 Add `sse_queue_maxsize: int = Field(default=50)` to `Settings` in `config/database.py`
  - [x] 9.2 Update `SSEConnectionManager.__init__` to accept `queue_maxsize` parameter read from `Settings`
  - [x] 9.3 Replace the silent drop in `push()` with an evict-oldest strategy: call `q.get_nowait()` then `q.put_nowait()`
  - [x] 9.4 Add `_dropped: Dict[uuid.UUID, int]` counter to `SSEConnectionManager` and expose `dropped_count(user_id)` method
  - [x] 9.5 Update structlog warning to include `user_id`, `event_type`, and `queue_size` fields; add structlog error log for post-eviction failure

- [ ] 10. Implement per-user notification preferences
  - [x] 10.1 Create `packages/backend/src/models/notification_preference.py` with `NotificationPreference` SQLModel including `UniqueConstraint("user_id", "notification_type")`
  - [x] 10.2 Create `packages/backend/src/services/preference_service.py` with `PreferenceService` implementing `get_preferences()`, `upsert_preference()`, and `is_enabled()` methods
  - [x] 10.3 Generate Alembic migration `create_notification_preferences` for the new table
  - [x] 10.4 Add `GET /api/v1/notifications/preferences` and `PUT /api/v1/notifications/preferences/{notification_type}` routes to `notifications.py` with JWT auth and `Response_Envelope`
  - [x] 10.5 Integrate `preference_service.is_enabled()` check into `NotificationService.handle()` before creating a `Notification` row; skip row creation and SSE push when `enabled=False`
  - [x] 10.6 Register the `/preferences` and `/preferences/{type}` routes before `/{notification_id}` to avoid path parameter collision
