# Design Document: Phase 3 — Booking System

## Overview

10 targeted fixes to `packages/backend`. One new migration, updates to existing models/service/routes.

---

## Changes by File

### 1. `src/models/availability.py`
Replace `is_booked + version` with `status` enum + locking fields:
- `status: str` — `available | locked | booked | blocked` (default `available`)
- `locked_by: Optional[UUID]`
- `locked_until: Optional[datetime]`
- `locked_reason: Optional[str]`
- `service_id: Optional[UUID]` FK → services.id
- Remove `is_booked`, `version` fields

### 2. `src/services/booking_service.py`
- `create_booking`: pricing lookup from Service, acquire lock, create booking, confirm lock
- `cancel_booking`: set cancelled, release availability, emit booking.cancelled
- `update_status`: accept JSON body, emit specific events per transition, release slot on rejection
- `list_bookings`: add pagination + status filter
- `get_messages`: paginated messages for a booking
- `add_message`: create BookingMessage with auth check

### 3. `src/api/v1/bookings.py`
- Add `GET /availability` endpoint
- Add `PATCH /{id}/cancel` endpoint
- Add `POST /{id}/messages` endpoint
- Add `GET /{id}/messages` endpoint
- Fix `PATCH /{id}/status` to accept JSON body
- Fix list endpoint to return paginated envelope
- All errors use structured dicts

### 4. `src/main.py`
- Change `app.include_router(bookings_router)` → `app.include_router(bookings_router, prefix="/api/v1")`

### 5. New Alembic migration
- Create `vendor_availability` table with all locking fields
- Unique constraint on `(vendor_id, service_id, date)`

### 6. Lock cleanup background task
- FastAPI lifespan: start asyncio background task that runs every 60s
- Releases expired locks: `status=locked AND locked_until < now()` → `status=available`

---

## State Machine

```
pending → confirmed | rejected | cancelled
confirmed → in_progress | cancelled
in_progress → completed | no_show
```

Terminal states: `completed`, `cancelled`, `rejected`, `no_show`

## Availability Lock Flow

```
1. Check: no row with status=booked/blocked for vendor+service+date
2. Upsert: create/update row with status=locked, locked_by=user_id, locked_until=now+30s
3. Create Booking record
4. Confirm: update row to status=booked, locked_by=NULL, locked_until=NULL, booking_id=booking.id
5. On failure: update row back to status=available
```

## Error Code Map

| Scenario | HTTP | Code |
|---|---|---|
| Date already booked | 409 | `CONFLICT_DATE_UNAVAILABLE` |
| Date locked by another | 409 | `CONFLICT_DATE_BEING_PROCESSED` |
| Booking not found | 404 | `NOT_FOUND_BOOKING` |
| Vendor not found | 404 | `NOT_FOUND_VENDOR` |
| Service not found/inactive | 422 | `VALIDATION_SERVICE_NOT_FOUND` |
| Past date | 422 | `VALIDATION_PAST_DATE` |
| Invalid transition | 409 | `VALIDATION_INVALID_TRANSITION` |
| Already cancelled | 409 | `CONFLICT_ALREADY_CANCELLED` |
| Already confirmed | 409 | `CONFLICT_ALREADY_CONFIRMED` |
| Completed can't cancel | 409 | `CONFLICT_COMPLETED_BOOKINGS_CANNOT_CANCEL` |
| Not authorized | 403 | `AUTH_FORBIDDEN` |
