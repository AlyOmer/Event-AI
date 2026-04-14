# Requirements Document

## Introduction

This feature completes the Booking System (Spec 009) module of the Event-AI platform — an AI-powered event planning marketplace for Pakistan. The core booking models, service, and basic routes already exist. This spec covers the 10 identified gaps that must be closed to make the booking system production-ready: API prefix alignment, VendorAvailability locking model, availability check endpoint, cancel endpoint, booking messages CRUD, pricing lookup, paginated listing, JSON-body status updates, structured error envelopes, and the Alembic migration with lock cleanup.

All implementation MUST comply with the project constitution: `/api/v1/` prefix on all routes, JWT auth on every endpoint, Pydantic validation at the boundary, Structlog structured logging, `{"success": false, "error": {"code": "...", "message": "..."}}` error envelopes, domain event emission via `event_bus`, rate limiting (10 req/min creation, 60 req/min reads), and no `sys.path.insert` or scattered `os.environ.get` calls.

---

## Glossary

- **Booking_System**: The FastAPI router and service layer in `packages/backend/src/api/v1/bookings.py` and `packages/backend/src/services/booking_service.py` responsible for all booking lifecycle operations.
- **BookingService**: The Python class `BookingService` in `booking_service.py` that encapsulates all booking business logic.
- **VendorAvailability**: The SQLModel table `vendor_availability` that tracks per-vendor-per-service-per-date slot state using a status enum and optimistic locking fields.
- **AvailabilityStatus**: An enum with values `available`, `locked`, `booked`, `blocked` representing the state of a `VendorAvailability` slot.
- **Booking**: The SQLModel table `bookings` representing a confirmed or pending engagement between a client and a vendor for a specific event date.
- **BookingMessage**: The SQLModel table `booking_messages` representing a message exchanged between a client and vendor on a specific booking.
- **BookingStatus**: An enum with values `pending`, `confirmed`, `in_progress`, `completed`, `cancelled`, `rejected`, `no_show`.
- **Service**: The SQLModel table `services` with `price_min` and `price_max` fields used for pricing lookup at booking creation time.
- **JWT_Auth**: The `get_current_user` FastAPI dependency that validates the Bearer token and returns the authenticated `User`.
- **Event_Bus**: The `event_bus` service in `src/services/event_bus_service.py` used to emit domain events within a database transaction.
- **Structured_Error**: A JSON object `{"code": "ERROR_CODE", "message": "human-readable description"}` used as the `detail` of every `HTTPException`.
- **Alembic**: The database migration tool used to apply incremental, reversible schema changes to the Neon PostgreSQL database.
- **Expired_Lock**: A `VendorAvailability` row with `status = locked` and `locked_until < now()`, indicating the lock was never confirmed and must be released.

---

## Requirements

### Requirement 1: API Prefix Alignment

**User Story:** As a frontend developer, I want all booking endpoints to be reachable under `/api/v1/bookings/`, so that the booking API is consistent with every other route in the system.

#### Acceptance Criteria

1. THE Booking_System SHALL register the bookings router in `main.py` with `prefix="/api/v1"` so that all booking routes are accessible under `/api/v1/bookings/`.
2. WHEN a client sends a request to any booking endpoint without the `/api/v1/` prefix, THE Booking_System SHALL return HTTP 404.
3. THE Booking_System SHALL preserve all existing route paths (`/`, `/{booking_id}`, `/{booking_id}/status`) relative to the `/api/v1/bookings` base.

---

### Requirement 2: VendorAvailability Locking Model

**User Story:** As a backend engineer, I want the `VendorAvailability` model to use a status enum with locking fields, so that the system can implement the acquire-lock → create-booking → confirm-lock pattern without race conditions.

#### Acceptance Criteria

1. THE VendorAvailability model SHALL include a `status` field of type `AvailabilityStatus` enum with values `available`, `locked`, `booked`, `blocked`, defaulting to `available`.
2. THE VendorAvailability model SHALL include a `locked_by` field of type `Optional[uuid.UUID]` that stores the ID of the user or process that acquired the lock.
3. THE VendorAvailability model SHALL include a `locked_until` field of type `Optional[datetime]` that stores the UTC expiry time of the lock (set to `now + 30 seconds` when a lock is acquired).
4. THE VendorAvailability model SHALL include a `locked_reason` field of type `Optional[str]` that stores a human-readable reason for the lock or block.
5. THE VendorAvailability model SHALL retain the existing `booking_id` foreign key field.
6. WHEN a booking is being created, THE BookingService SHALL set `status = locked`, `locked_by = user_id`, `locked_until = now() + 30s` on the target `VendorAvailability` row before inserting the `Booking` record.
7. WHEN a booking is successfully created, THE BookingService SHALL set `status = booked`, `locked_by = NULL`, `locked_until = NULL` on the `VendorAvailability` row.
8. IF the booking creation fails after the lock is acquired, THEN THE BookingService SHALL set `status = available`, `locked_by = NULL`, `locked_until = NULL` on the `VendorAvailability` row within the same transaction rollback.

---

### Requirement 3: Availability Check Endpoint

**User Story:** As a client or AI agent, I want to check whether a vendor's service is available on a specific date before attempting a booking, so that I can avoid wasted booking attempts and suggest alternatives.

#### Acceptance Criteria

1. THE Booking_System SHALL expose `GET /api/v1/bookings/availability` accepting query parameters `vendor_id` (UUID, required), `service_id` (UUID, required), and `date` (ISO-8601 date string, required).
2. WHEN no `VendorAvailability` row exists with `status` in `[booked, blocked]` for the given `vendor_id`, `service_id`, and `date`, THE Booking_System SHALL return HTTP 200 with `{"success": true, "data": {"available": true}, "meta": {}}`.
3. WHEN a `VendorAvailability` row exists with `status = booked` for the given `vendor_id`, `service_id`, and `date`, THE Booking_System SHALL return HTTP 200 with `{"success": true, "data": {"available": false, "reason": "Date already booked"}, "meta": {}}`.
4. WHEN a `VendorAvailability` row exists with `status = blocked` for the given `vendor_id`, `service_id`, and `date`, THE Booking_System SHALL return HTTP 200 with `{"success": true, "data": {"available": false, "reason": "Vendor not available on this date"}, "meta": {}}`.
5. WHEN a `VendorAvailability` row exists with `status = locked` and `locked_until > now()` for the given `vendor_id`, `service_id`, and `date`, THE Booking_System SHALL return HTTP 200 with `{"success": true, "data": {"available": false, "reason": "Date is temporarily held"}, "meta": {}}`.
6. THE Booking_System SHALL require JWT authentication on `GET /api/v1/bookings/availability`.

---

### Requirement 4: Cancel Booking Endpoint

**User Story:** As a client or vendor, I want to cancel a pending or confirmed booking, so that the vendor's availability slot is freed and both parties are notified.

#### Acceptance Criteria

1. THE Booking_System SHALL expose `PATCH /api/v1/bookings/{booking_id}/cancel` accepting an optional JSON body `{"reason": "string"}`.
2. WHEN the booking `status` is `pending` or `confirmed`, THE BookingService SHALL set `status = cancelled`, `cancelled_at = now()`, `cancelled_by = current_user.id`, and `cancellation_reason = reason` on the `Booking` record.
3. WHEN a booking is cancelled, THE BookingService SHALL set `status = available`, `locked_by = NULL`, `locked_until = NULL`, `booking_id = NULL` on the associated `VendorAvailability` row.
4. WHEN a booking is cancelled, THE BookingService SHALL emit a `booking.cancelled` domain event via `Event_Bus` containing `booking_id`, `cancelled_by`, and `cancellation_reason`.
5. IF the booking `status` is already `cancelled`, THEN THE Booking_System SHALL return HTTP 409 with `Structured_Error` code `CONFLICT_ALREADY_CANCELLED`.
6. IF the booking `status` is `completed`, THEN THE Booking_System SHALL return HTTP 409 with `Structured_Error` code `CONFLICT_COMPLETED_BOOKINGS_CANNOT_CANCEL`.
7. IF the booking `status` is `in_progress`, `rejected`, or `no_show`, THEN THE Booking_System SHALL return HTTP 409 with `Structured_Error` code `CONFLICT_ALREADY_CANCELLED`.
8. THE Booking_System SHALL require JWT authentication on `PATCH /api/v1/bookings/{booking_id}/cancel`.

---

### Requirement 5: Booking Messages CRUD

**User Story:** As a client or vendor, I want to send and read messages attached to a booking, so that we can coordinate event requirements and logistics without leaving the platform.

#### Acceptance Criteria

1. THE Booking_System SHALL expose `POST /api/v1/bookings/{booking_id}/messages` accepting a JSON body `{"message": "string", "sender_type": "client|vendor|system", "attachments": []}`.
2. WHEN a message is created, THE BookingService SHALL verify that `current_user.id` matches either `booking.user_id` (client) or the vendor's owner user ID; IF neither matches, THEN THE Booking_System SHALL return HTTP 403 with `Structured_Error` code `AUTH_FORBIDDEN`.
3. WHEN a message is created, THE BookingService SHALL insert a `BookingMessage` row with `booking_id`, `sender_id = current_user.id`, `sender_type`, `message`, and `attachments`.
4. WHEN a message is created, THE Booking_System SHALL return HTTP 201 with `{"success": true, "data": <BookingMessageRead>, "meta": {}}`.
5. THE Booking_System SHALL expose `GET /api/v1/bookings/{booking_id}/messages` accepting query parameters `page` (default 1) and `limit` (default 20, max 100).
6. WHEN messages are listed, THE BookingService SHALL verify that `current_user.id` matches either `booking.user_id` or the vendor's owner user ID; IF neither matches, THEN THE Booking_System SHALL return HTTP 403 with `Structured_Error` code `AUTH_FORBIDDEN`.
7. WHEN messages are listed, THE Booking_System SHALL return messages in reverse chronological order (newest first) with `{"success": true, "data": [...], "meta": {"total": N, "page": P, "limit": L, "pages": X}}`.
8. IF the `booking_id` does not exist, THEN THE Booking_System SHALL return HTTP 404 with `Structured_Error` code `NOT_FOUND_BOOKING`.
9. THE Booking_System SHALL require JWT authentication on both `POST` and `GET` messages endpoints.

---

### Requirement 6: Pricing Lookup on Booking Creation

**User Story:** As a client, I want the system to automatically populate the booking price from the service's pricing data, so that I don't have to manually enter a price and the price is always accurate.

#### Acceptance Criteria

1. WHEN a booking is created, THE BookingService SHALL look up the `Service` record by `booking_in.service_id`.
2. IF the `Service` record does not exist or `service.is_active = False`, THEN THE BookingService SHALL raise HTTP 422 with `Structured_Error` code `VALIDATION_SERVICE_NOT_FOUND`.
3. WHEN the `Service` record exists and `unit_price` is not provided in the request body, THE BookingService SHALL set `unit_price = service.price_min`.
4. WHEN the `Service` record exists and `unit_price` is provided in the request body, THE BookingService SHALL use the provided `unit_price` value.
5. THE BookingService SHALL calculate `total_price = unit_price * quantity` before inserting the `Booking` record.
6. THE BookingService SHALL verify that the `Service.vendor_id` matches `booking_in.vendor_id`; IF they do not match, THEN THE BookingService SHALL raise HTTP 422 with `Structured_Error` code `VALIDATION_SERVICE_NOT_FOUND`.

---

### Requirement 7: Paginated and Filtered Booking List

**User Story:** As a client, I want to list my bookings with pagination and status filtering, so that I can efficiently browse my booking history without loading all records at once.

#### Acceptance Criteria

1. THE Booking_System SHALL accept query parameters `page` (integer ≥ 1, default 1), `limit` (integer 1–100, default 20), and `status` (optional `BookingStatus` enum value) on `GET /api/v1/bookings/`.
2. WHEN `status` is provided, THE BookingService SHALL filter results to only bookings where `booking.status = status`.
3. THE Booking_System SHALL return `{"success": true, "data": [...], "meta": {"total": N, "page": P, "limit": L, "pages": X}}` where `pages = ceil(total / limit)`.
4. WHEN no bookings match the query, THE Booking_System SHALL return `{"success": true, "data": [], "meta": {"total": 0, "page": 1, "limit": L, "pages": 0}}`.
5. THE BookingService SHALL apply `OFFSET = (page - 1) * limit` and `LIMIT = limit` to the database query.
6. THE BookingService SHALL order results by `created_at DESC`.

---

### Requirement 8: JSON Body Status Update

**User Story:** As a vendor, I want to update a booking's status by sending a JSON body, so that I can include a reason for rejection or other context alongside the status change.

#### Acceptance Criteria

1. THE Booking_System SHALL change `PATCH /api/v1/bookings/{booking_id}/status` to accept a JSON body `{"status": "BookingStatus", "reason": "optional string"}` instead of a query parameter.
2. WHEN the new status is `rejected`, THE BookingService SHALL release the `VendorAvailability` slot by setting `status = available`, `locked_by = NULL`, `locked_until = NULL`, `booking_id = NULL`.
3. WHEN the new status is `rejected`, THE BookingService SHALL emit a `booking.cancelled` domain event via `Event_Bus`.
4. WHEN the new status is `confirmed`, THE BookingService SHALL emit a `booking.confirmed` domain event via `Event_Bus` containing `booking_id` and `confirmed_by`.
5. WHEN the new status is `completed`, THE BookingService SHALL emit a `booking.completed` domain event via `Event_Bus` containing `booking_id`.
6. WHEN the new status is any other valid transition, THE BookingService SHALL emit a `booking.status_changed` domain event via `Event_Bus` containing `booking_id`, `old_status`, and `new_status`.
7. IF the requested transition is not in the valid state machine (`pending → confirmed|rejected|cancelled`, `confirmed → in_progress|cancelled`, `in_progress → completed|no_show`), THEN THE Booking_System SHALL return HTTP 409 with `Structured_Error` code `VALIDATION_INVALID_TRANSITION`.
8. IF the booking is already in `confirmed` status and the request is to confirm again, THEN THE Booking_System SHALL return HTTP 409 with `Structured_Error` code `CONFLICT_ALREADY_CONFIRMED`.

---

### Requirement 9: Structured Error Envelopes

**User Story:** As a frontend developer, I want all booking API errors to return a consistent `{"code": "...", "message": "..."}` structure, so that the UI can display meaningful error messages and handle specific error codes programmatically.

#### Acceptance Criteria

1. THE Booking_System SHALL raise all `HTTPException` instances with `detail` set to a `Structured_Error` dict `{"code": "ERROR_CODE", "message": "human-readable description"}` on every booking route and service method.
2. THE Booking_System SHALL use error code `CONFLICT_DATE_UNAVAILABLE` when a booking attempt is made for a date that is already `booked`.
3. THE Booking_System SHALL use error code `CONFLICT_DATE_BEING_PROCESSED` when a booking attempt is made for a date that is currently `locked` by another process.
4. THE Booking_System SHALL use error code `NOT_FOUND_BOOKING` when a booking ID does not exist.
5. THE Booking_System SHALL use error code `NOT_FOUND_VENDOR` when a vendor ID does not exist.
6. THE Booking_System SHALL use error code `NOT_FOUND_SERVICE` when a service ID does not exist or is inactive.
7. THE Booking_System SHALL use error code `VALIDATION_PAST_DATE` when `event_date` is before today's date.
8. THE Booking_System SHALL use error code `VALIDATION_INVALID_TRANSITION` when a status transition is not permitted by the state machine.
9. THE Booking_System SHALL use error code `CONFLICT_ALREADY_CANCELLED` when a cancel or status-update is attempted on an already-cancelled booking.
10. THE Booking_System SHALL use error code `AUTH_FORBIDDEN` when the authenticated user does not have permission to access or modify the requested booking or message.
11. THE Booking_System SHALL use error code `VALIDATION_SERVICE_NOT_FOUND` when the service referenced in a booking creation request does not exist or is inactive.

---

### Requirement 10: Alembic Migration and Expired Lock Cleanup

**User Story:** As a database administrator, I want an Alembic migration that creates the `vendor_availability` table with all locking fields, and a background task that releases expired locks, so that the schema is version-controlled and stale locks never permanently block availability.

#### Acceptance Criteria

1. THE Alembic migration SHALL create the `vendor_availability` table with columns: `id` (UUID primary key), `vendor_id` (UUID FK → `vendors.id`), `service_id` (UUID FK → `services.id`, nullable), `date` (DATE, indexed), `status` (VARCHAR enum: `available`, `locked`, `booked`, `blocked`, default `available`), `locked_by` (UUID, nullable), `locked_until` (TIMESTAMPTZ, nullable), `locked_reason` (TEXT, nullable), `booking_id` (UUID FK → `bookings.id`, nullable), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ).
2. THE Alembic migration SHALL be reversible: the `downgrade()` function SHALL drop the `vendor_availability` table.
3. THE Alembic migration SHALL include a unique constraint on `(vendor_id, service_id, date)` to prevent duplicate availability rows for the same vendor+service+date combination.
4. THE Booking_System SHALL include a background task or APScheduler job that runs every 60 seconds and sets `status = available`, `locked_by = NULL`, `locked_until = NULL` on all `VendorAvailability` rows where `status = locked` AND `locked_until < now()`.
5. WHEN the expired lock cleanup task runs, THE Booking_System SHALL log the number of locks released using Structlog at `INFO` level.
6. THE Alembic migration SHALL NOT use `sys.path.insert` or `os.environ.get`; it SHALL use the project's `get_settings()` function to obtain the `DIRECT_URL` database connection string.
