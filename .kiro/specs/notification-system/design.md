# Design Document — Notification System (Module 010 Gaps)

## Overview

This document describes the technical design for the ten gap areas identified in the notification-system requirements. All changes are confined to `packages/backend`. The existing `Notification` model, `NotificationService`, `SSEConnectionManager`, and REST routes are extended — not replaced.

---

## Architecture

### Component Map

```
packages/backend/src/
├── models/
│   ├── notification.py          ← extend NotificationType enum (Req 1, 2)
│   └── notification_preference.py  ← new NotificationPreference model (Req 10)
├── services/
│   ├── notification_service.py  ← extend _EVENT_MAP, add preference check (Req 1, 2, 10)
│   ├── sse_manager.py           ← overflow eviction + dropped counter (Req 9)
│   └── preference_service.py   ← new PreferenceService (Req 10)
├── api/v1/
│   └── notifications.py        ← add DELETE endpoints, fix envelope, add rate limits (Req 3–6)
├── config/
│   └── database.py             ← add event.* and vendor.* subscriptions in lifespan (Req 7)
└── tests/
    └── test_notifications.py   ← new test suite (Req 8)
```

---

## Detailed Design

### 1. NotificationType Enum Extension (Req 1, 2)

Add five new values to the existing `NotificationType` enum in `models/notification.py`:

```python
class NotificationType(str, Enum):
    # existing values ...
    event_created         = "event_created"
    event_status_changed  = "event_status_changed"
    event_cancelled       = "event_cancelled"
    vendor_approved       = "vendor_approved"
    vendor_rejected       = "vendor_rejected"
```

An Alembic migration must update the `notifications.type` column's CHECK constraint (or Postgres ENUM type) to include the five new values.

---

### 2. _EVENT_MAP Extension (Req 1, 2)

Extend the `_EVENT_MAP` dict in `notification_service.py` with five new entries:

```python
"event.created":        (NotificationType.event_created,        "Event Created",         "Your event '{event_name}' has been created."),
"event.status_changed": (NotificationType.event_status_changed, "Event Status Updated",  "Your event '{event_name}' status changed to {new_status}."),
"event.cancelled":      (NotificationType.event_cancelled,      "Event Cancelled",       "Your event '{event_name}' has been cancelled."),
"vendor.approved":      (NotificationType.vendor_approved,      "Vendor Account Approved", "Your vendor account has been approved. You can now accept bookings."),
"vendor.rejected":      (NotificationType.vendor_rejected,      "Vendor Account Rejected", "Your vendor account application was not approved."),
```

The `handle()` method resolves `user_id` from the payload key `user_id` for event/vendor events (unlike booking events which resolve via the `Booking` ORM object). If `user_id` is absent or unresolvable, log a structlog warning and return early.

---

### 3. Delete Single Notification (Req 3)

Add to `notifications.py` router:

```python
@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    notif = await session.get(Notification, notification_id)
    if not notif:
        raise HTTPException(404, detail={"code": "NOT_FOUND_NOTIFICATION", ...})
    if notif.user_id != current_user.id:
        raise HTTPException(403, detail={"code": "AUTH_FORBIDDEN", ...})
    await session.delete(notif)
    await session.commit()
    return {"success": True, "data": None, "meta": {}}
```

Route ordering: `DELETE /read` must be registered **before** `DELETE /{notification_id}` to avoid FastAPI treating `read` as a UUID path parameter.

---

### 4. Bulk Delete Read Notifications (Req 4)

```python
@router.delete("/read")
async def delete_read_notifications(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        delete(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == True,
        )
    )
    await session.commit()
    return {"success": True, "data": {"deleted": result.rowcount}, "meta": {}}
```

---

### 5. Rate Limiting (Req 5)

Use `slowapi` (already a common FastAPI rate-limiting library). Apply via decorator on each endpoint. Key function uses `current_user.id` (not IP) to scope limits per authenticated user.

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

def _user_key(request: Request) -> str:
    # Extract user_id from JWT — resolved after auth dependency runs
    user: User = request.state.current_user
    return str(user.id)

limiter = Limiter(key_func=_user_key)

# Read endpoints: 60/minute
@router.get("/")
@limiter.limit("60/minute")
async def list_notifications(...): ...

# Write endpoints: 10/minute
@router.delete("/{notification_id}")
@limiter.limit("10/minute")
async def delete_notification(...): ...
```

The `Limiter` instance is registered on `app.state` in lifespan and the `SlowAPIMiddleware` is added to the FastAPI app.

---

### 6. Response Envelope on mark_read (Req 6)

Change the existing `mark_read` endpoint to remove `response_model=NotificationRead` and return the envelope manually:

```python
@router.patch("/{notification_id}/read")
async def mark_read(...):
    notif = await notification_service.mark_read(session, notification_id, current_user.id)
    return {"success": True, "data": NotificationRead.model_validate(notif), "meta": {}}
```

---

### 7. Lifespan Subscriptions (Req 7)

Extend the subscription loop in `config/database.py` lifespan:

```python
for _et in (
    "booking.created", "booking.confirmed", "booking.cancelled",
    "booking.completed", "booking.rejected", "booking.status_changed",
    # new:
    "event.created", "event.status_changed", "event.cancelled",
    "vendor.approved", "vendor.rejected",
):
    event_bus.subscribe(_et, notification_service.handle)
```

---

### 8. Test Suite (Req 8)

File: `packages/backend/tests/test_notifications.py`

Test structure:

```
Fixtures:
  - async_client: httpx.AsyncClient with ASGITransport, SQLite in-memory DB
  - auth_headers: JWT token for test user
  - other_auth_headers: JWT token for a second user (for 403 tests)
  - sample_notification: pre-inserted Notification row

Service tests (pytest-asyncio):
  - test_handle_booking_created / confirmed / cancelled / completed / rejected / status_changed
  - test_handle_event_created / status_changed / cancelled
  - test_handle_vendor_approved / rejected
  - test_handle_unknown_event_type_is_noop
  - test_handle_missing_user_id_logs_warning
  - test_list_notifications_pagination
  - test_list_notifications_unread_only
  - test_unread_count
  - test_mark_read_success
  - test_mark_read_not_found
  - test_mark_read_forbidden
  - test_mark_all_read

Route tests (httpx):
  - test_get_notifications_list
  - test_get_unread_count
  - test_patch_mark_read_returns_envelope
  - test_patch_mark_all_read
  - test_delete_notification_success
  - test_delete_notification_not_found
  - test_delete_notification_forbidden
  - test_delete_read_notifications
  - test_get_preferences
  - test_put_preference
  - test_put_preference_invalid_type_returns_422

Property test:
  - FOR ALL valid event_type values in _EVENT_MAP, handle() with a valid session
    creates exactly one Notification row (idempotency of single-call row creation)
```

Run command: `uv run pytest packages/backend/tests/test_notifications.py -v`

---

### 9. SSE Queue Overflow Handling (Req 9)

Modify `SSEConnectionManager.push()` in `sse_manager.py`:

```python
class SSEConnectionManager:
    def __init__(self, queue_maxsize: int = 50):
        self._connections: Dict[uuid.UUID, List[asyncio.Queue]] = {}
        self._dropped: Dict[uuid.UUID, int] = {}
        self._queue_maxsize = queue_maxsize

    def connect(self, user_id: uuid.UUID) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._queue_maxsize)
        ...

    def dropped_count(self, user_id: uuid.UUID) -> int:
        return self._dropped.get(user_id, 0)

    async def push(self, user_id: uuid.UUID, event_type: str, data: Dict[str, Any]) -> None:
        for q in list(self._connections.get(user_id, [])):
            try:
                q.put_nowait({"event": event_type, "data": data})
            except asyncio.QueueFull:
                # Evict oldest, insert newest
                try:
                    q.get_nowait()  # discard oldest
                    q.put_nowait({"event": event_type, "data": data})
                    self._dropped[user_id] = self._dropped.get(user_id, 0) + 1
                    logger.warning("sse.queue_overflow_evicted",
                                   user_id=str(user_id),
                                   event_type=event_type,
                                   queue_size=q.qsize())
                except Exception as e:
                    logger.error("sse.push_failed_after_eviction",
                                 user_id=str(user_id), error=str(e))
```

The `queue_maxsize` is read from `Settings.sse_queue_maxsize: int = Field(default=50)`.

---

### 10. Notification Preferences (Req 10)

#### Model — `models/notification_preference.py`

```python
class NotificationPreference(SQLModel, table=True):
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "notification_type"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    notification_type: NotificationType
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, ...)
    updated_at: datetime = Field(default_factory=datetime.utcnow, ...)
```

#### Service — `services/preference_service.py`

```python
class PreferenceService:
    async def get_preferences(self, session, user_id) -> list[NotificationPreference]: ...
    async def upsert_preference(self, session, user_id, notification_type, enabled) -> NotificationPreference: ...
    async def is_enabled(self, session, user_id, notification_type) -> bool:
        # Returns True if no row exists (opt-in default) or row.enabled is True
```

#### Integration in handle()

Before creating a `Notification` row, `NotificationService.handle()` calls `preference_service.is_enabled()`. If `False`, return early without creating the row or pushing to SSE.

#### Routes

```
GET  /api/v1/notifications/preferences          → list all preferences for current user
PUT  /api/v1/notifications/preferences/{type}   → upsert {"enabled": bool}
```

Both routes are protected by JWT auth and return the `Response_Envelope`.

#### Alembic Migration

A new migration creates the `notification_preferences` table with a unique constraint on `(user_id, notification_type)`.

---

## Database Migrations

| Migration | Description |
|---|---|
| `add_notification_types_event_vendor` | Adds `event_created`, `event_status_changed`, `event_cancelled`, `vendor_approved`, `vendor_rejected` to the `notificationtype` enum |
| `create_notification_preferences` | Creates `notification_preferences` table |

---

## Error Code Reference

| Code | HTTP Status | Usage |
|---|---|---|
| `NOT_FOUND_NOTIFICATION` | 404 | Notification ID not found |
| `AUTH_FORBIDDEN` | 403 | Notification belongs to another user |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit hit on any notification endpoint |
| `VALIDATION_INVALID_TYPE` | 422 | Invalid `notification_type` in preference PUT |

---

## Correctness Properties

### P1 — handle() creates exactly one row per valid event (Req 8, AC 8)
For all `event_type` values in `_EVENT_MAP`, a single call to `handle()` with a valid `AsyncSession` and a payload containing a resolvable `user_id` creates exactly one `Notification` row. Verified by querying the count before and after.

### P2 — Preference opt-out suppresses notification creation (Req 10, AC 5)
For all `NotificationType` values, when a `NotificationPreference` row exists with `enabled=False` for a user, `handle()` creates zero `Notification` rows for that user and type.

### P3 — delete_read_notifications count matches pre-existing read rows (Req 4, AC 2–3)
For any set of N read notifications belonging to a user, `DELETE /notifications/read` returns `{"deleted": N}` and a subsequent `GET /notifications/` returns zero read notifications for that user.

### P4 — mark_read response always matches envelope schema (Req 6, AC 1)
For any valid notification owned by the authenticated user, `PATCH /notifications/{id}/read` always returns a JSON object with keys `success`, `data`, and `meta` at the top level.
