# Feature Specification: Notification System

**Feature Branch**: `feature/notification-system`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: "Notification System — Email/SMS for booking confirmations, status changes"

---

## User Scenarios & Testing

### User Story 1 — Booking Lifecycle Email Notifications (Priority: P1)

When a booking transitions through its lifecycle (`pending → confirmed → in_progress → completed → cancelled/rejected`), both the user and the vendor receive an email notification with the details.

**Why this priority**: Email notifications are the primary communication channel for booking status. Without them, users and vendors have no way to know when a booking changes state.

**Independent Test**: Create a booking, confirm it via the status endpoint, and verify an email is sent (or logged in dev mode) with correct status, vendor name, service name, and event date.

**Acceptance Scenarios**:

1. **Given** a booking is created, **When** the `booking.created` event fires, **Then** the client receives a "Booking Submitted" email and the vendor receives a "New Booking Request" email.
2. **Given** a vendor confirms a booking, **When** the `booking.confirmed` event fires, **Then** the client receives a "Booking Confirmed" email with vendor contact details and event date.
3. **Given** a booking is cancelled, **When** the `booking.cancelled` event fires, **Then** both the client and vendor receive a "Booking Cancelled" email with the cancellation reason.
4. **Given** a booking is completed, **When** the `booking.completed` event fires, **Then** the client receives a "Your Event is Complete — Leave a Review!" email with a review link.
5. **Given** SMTP is not configured (dev mode), **When** any notification fires, **Then** the email content is logged to Pino without sending, and the booking flow is not blocked.

---

### User Story 2 — Event-Driven Notification Dispatch (Priority: P1)

Notifications are triggered exclusively by domain events (not inline in route handlers). A `NotificationService` subscribes to domain events and dispatches to the correct channels (email, in-app, SMS).

**Why this priority**: The constitution mandates event-driven architecture — coupling email sends directly in route handlers (current pattern in `bookings.routes.ts`) violates EDA principles and makes the system fragile.

**Independent Test**: Emit a `booking.confirmed` mock event and verify the NotificationService dispatches an email and an in-app notification without the booking route being involved.

**Acceptance Scenarios**:

1. **Given** any domain event in the notification taxonomy, **When** it is emitted, **Then** the `NotificationService` receives it and dispatches to the configured channels.
2. **Given** the email channel fails, **Then** the error is logged but the domain event is not re-raised — other channels (in-app) still succeed independently.
3. **Given** multiple channels are configured for one event type, **Then** all channels are dispatched concurrently (Promise.allSettled), not sequentially.

---

### User Story 3 — In-App Notifications with Persistence (Priority: P1)

Users see real-time notifications in the portal via the existing notification bell. Notifications are persisted in the database (not just client-side React state) so they survive page refresh.

**Why this priority**: Current notifications are entirely client-side (`notification-provider.tsx` uses `useState`) — they vanish on refresh. Users lose track of important booking updates.

**Independent Test**: Trigger a `booking.confirmed` event, verify a row is created in the `notifications` table, then refresh the page and confirm the notification reappears in the bell dropdown.

**Acceptance Scenarios**:

1. **Given** a domain event that triggers a notification, **When** the NotificationService dispatches to the in-app channel, **Then** a row is created in the `notifications` table with `userId`, `title`, `message`, `type`, `read: false`, and `createdAt`.
2. **Given** the user opens the notification bell, **When** the portal loads, **Then** it fetches `GET /api/v1/notifications?unread=true` and displays persisted notifications (not just socket events).
3. **Given** the user marks a notification as read, **When** `PATCH /api/v1/notifications/:id/read` is called, **Then** the `read` flag is set to `true` in the database.
4. **Given** the user is online, **When** a notification is created, **Then** it is also pushed in real-time via WebSocket/SSE (coexists with persistence).

---

### User Story 4 — Email Templates with Consistent Branding (Priority: P2)

All email notifications use a shared HTML template engine with consistent Event-AI branding (logo, colors, footer, unsubscribe link) instead of inline HTML strings.

**Why this priority**: Current emails use raw inline HTML in `email.service.ts` — it's unmaintainable and produces inconsistent branding across different email types.

**Independent Test**: Render a booking confirmation email template and verify it contains the branding header, dynamic content, and footer with unsubscribe link.

**Acceptance Scenarios**:

1. **Given** any email notification type, **When** the email is rendered, **Then** it uses a shared base template with the Event-AI header, dynamic body, and standard footer.
2. **Given** the template receives booking data, **When** the email is generated, **Then** all dynamic fields (vendor name, date, price) are properly escaped to prevent XSS.
3. **Given** a new email type is needed, **Then** developers only need to create a body template — the base layout, header, and footer are inherited.

---

### User Story 5 — Vendor Notification Preferences (Priority: P2)

Vendors can configure which notifications they receive and on which channels (email, SMS, in-app). Users can opt out of non-essential notifications.

**Why this priority**: Prevents notification fatigue and gives vendors control over their communication channels.

**Independent Test**: Set a vendor's preference to "email only for bookings, no marketing", submit a booking, and verify only email is sent (no SMS, no marketing).

**Acceptance Scenarios**:

1. **Given** a vendor's notification preferences are set to "email only", **When** a booking event fires, **Then** only the email channel dispatches — SMS and in-app are skipped.
2. **Given** a user disables booking reminder notifications, **When** a reminder would fire, **Then** it is suppressed for that user.
3. **Given** critical notifications (security alerts, payment), **Then** they ALWAYS send regardless of preferences — they cannot be disabled.

---

### User Story 6 — SMS Notifications for Pakistan Market (Priority: P3)

For critical booking events (confirmed, cancelled, day-before reminder), the system sends SMS to the client's phone number via a Pakistani SMS gateway (e.g., Twilio, or local providers like Jazz/Zong APIs).

**Why this priority**: SMS is the dominant communication channel in Pakistan. Many users check SMS before email. However, it's P3 because it requires external provider integration and per-message costs.

**Independent Test**: Mock the SMS provider API, trigger a `booking.confirmed` event for a client with a phone number, and verify the SMS API is called with the correct message.

**Acceptance Scenarios**:

1. **Given** a booking is confirmed and the client has a phone number, **When** the `booking.confirmed` event fires, **Then** an SMS is sent: "Your booking with {vendor} on {date} is confirmed! Booking ID: {id}".
2. **Given** the SMS provider API is down, **When** SMS dispatch fails, **Then** the system retries 2 times with backoff, then logs the failure — email is unaffected.
3. **Given** the client has no phone number, **When** an SMS notification would fire, **Then** it is silently skipped (only email and in-app fire).

---

### User Story 7 — Day-Before Event Reminder (Priority: P3)

The system sends an automated reminder email (and optionally SMS) to the client and vendor 24 hours before the event date.

**Why this priority**: Reduces no-shows and ensures both parties are prepared, but depends on a scheduler/cron job infrastructure.

**Independent Test**: Create a booking with `eventDate = tomorrow`, run the reminder cron, and verify both client and vendor receive reminder notifications.

**Acceptance Scenarios**:

1. **Given** a confirmed booking with `eventDate = tomorrow`, **When** the daily reminder cron runs, **Then** both the client and vendor receive a "Your event is tomorrow!" notification via email and in-app.
2. **Given** a cancelled booking with `eventDate = tomorrow`, **When** the reminder cron runs, **Then** no reminder is sent.

---

### Edge Cases

- What if the user's email address is invalid or bounces? → Log the bounce, mark the notification as `failed`, retry once. After 3 bounces, flag the user for email verification.
- What if the same event triggers duplicate notifications (idempotency)? → Deduplicate by `eventId + eventType + userId` — if a notification with those fields already exists in the last 5 minutes, skip.
- What if the SMTP server is down? → Notifications are queued in-memory (Phase 1) or in a persistent queue (Phase 2). The system retries 3 times with exponential backoff.
- What if a vendor has no email configured? → Skip email channel for that vendor; in-app notification is always sent.
- What happens during bulk status changes (e.g., admin cancels all bookings for a vendor)? → Batch notifications to avoid SMTP rate limits; send one summary email instead of N individual emails.
- What if the user is offline when an in-app notification fires? → The notification is persisted in the database and shown when they next load the page.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST dispatch notifications via domain events — never inline in route handlers.
- **FR-002**: System MUST support three notification channels: **Email** (nodemailer/SMTP), **In-App** (persisted + WebSocket push), **SMS** (external API).
- **FR-003**: System MUST persist all in-app notifications in a `notifications` table with `userId`, `title`, `message`, `type`, `channel`, `read`, `readAt`, `relatedEntityType`, `relatedEntityId`, `createdAt`.
- **FR-004**: System MUST expose REST endpoints: `GET /api/v1/notifications` (list, paginated), `PATCH /api/v1/notifications/:id/read`, `POST /api/v1/notifications/mark-all-read`.
- **FR-005**: System MUST use a shared HTML email template engine (e.g., `@react-email/components` or Handlebars) for consistent branding — no more inline HTML strings.
- **FR-006**: System MUST log email content to Pino in dev mode when SMTP is not configured, without blocking the flow.
- **FR-007**: System MUST deduplicate notifications by `eventId + eventType + userId` within a 5-minute window.
- **FR-008**: System MUST support notification preferences per user/vendor: channel toggles (email on/off, SMS on/off, in-app on/off) per event type.
- **FR-009**: Critical notifications (security, payment, booking confirmation) MUST always send regardless of preference settings.
- **FR-010**: Email dispatch failures MUST NOT block booking operations — fire-and-forget with async retry (3 attempts, exponential backoff).
- **FR-011**: SMS MUST be sent for confirmed/cancelled bookings when the client has a phone number and SMS is enabled in their preferences.
- **FR-012**: System MUST send day-before reminders via a scheduled cron job for confirmed bookings.
- **FR-013**: All notification dispatches MUST be logged in `audit_logs` with the notification ID and channel for traceability.

### Notification Event Taxonomy

| Domain Event | Email (Client) | Email (Vendor) | In-App (Client) | In-App (Vendor) | SMS (Client) |
|---|---|---|---|---|---|
| `booking.created` | ✅ Booking submitted | ✅ New booking request | ✅ | ✅ | ❌ |
| `booking.confirmed` | ✅ Booking confirmed | ❌ | ✅ | ❌ | ✅ |
| `booking.rejected` | ✅ Booking rejected | ❌ | ✅ | ❌ | ❌ |
| `booking.cancelled` | ✅ Booking cancelled | ✅ Booking cancelled | ✅ | ✅ | ✅ |
| `booking.completed` | ✅ Leave a review | ❌ | ✅ | ✅ | ❌ |
| `event.created` | ✅ Event confirmed | ❌ | ✅ | ❌ | ❌ |
| `vendor.approved` | ❌ | ✅ Vendor approved | ❌ | ✅ | ❌ |
| `payment.received` | ✅ Payment receipt | ✅ Payment notification | ✅ | ✅ | ✅ |
| `reminder.day_before` | ✅ Event tomorrow | ✅ Event tomorrow | ✅ | ✅ | ✅ |

### Key Entities

- **Notification**: Persisted record of an in-app notification (`userId`, `title`, `message`, `type`, `read`, `relatedEntityType`, `relatedEntityId`).
- **NotificationPreference**: Per-user/vendor channel toggles per event type category (booking, payment, marketing, security).
- **EmailTemplate**: Named template key → rendered HTML with base layout inheritance.
- **NotificationService**: Central dispatcher that subscribes to domain events and fans out to configured channels.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of booking lifecycle events trigger the corresponding notifications within 2 seconds of the domain event being emitted.
- **SC-002**: In-app notifications persist across page refresh — zero notifications lost on reload.
- **SC-003**: Email delivery failure rate < 5% (measured by SMTP acknowledgment, excluding invalid addresses).
- **SC-004**: All email notifications use the shared template engine — zero inline HTML in `email.service.ts`.
- **SC-005**: Notification deduplication prevents 100% of duplicate notifications within the 5-minute window.
- **SC-006**: Day-before reminders are sent for 100% of confirmed bookings with valid event dates.
- **SC-007**: Notification endpoints achieve 80%+ test coverage.

---

## Constitution Compliance Checklist

Every implementation decision in this feature MUST satisfy the following constitution mandates:

| Constitution Rule | Section | Requirement for Notification System |
|---|---|---|
| **Event-Driven Architecture** | III.1–III.8 | Notifications MUST be triggered by domain events — NEVER inline in route handlers. The `NotificationService` subscribes to events and dispatches to channels. |
| **Events are facts, not commands** | III.1 | Events like `booking.created` trigger notifications. The notification system does NOT emit "send email" commands. |
| **Event envelope standard** | III.2 | All domain events consumed by the notification system MUST use the standard envelope (`eventId`, `eventType`, `timestamp`, `version`, `source`, `correlationId`, `data`). |
| **At-least-once delivery + idempotency** | III.5 | Notification consumers MUST be idempotent. Deduplicate by `eventId + eventType + userId` to prevent duplicate emails. |
| **Event store for audit** | III.6 | All `booking.*`, `payment.*`, `event.*` events that trigger notifications MUST be persisted in the `domain_events` table. |
| **Real-time to frontends** | III.7 | In-app notifications MUST be pushed to portals via SSE or WebSocket — frontend MUST NOT poll. |
| **Dead letter handling** | III.8 | Failed notification dispatch retries 3× with exponential backoff, then moves to dead-letter store. |
| **Async event fan-out** | III (Anti-patterns) | Booking → email → notification MUST NOT be a synchronous chain. All channels dispatch concurrently via `Promise.allSettled`. |
| **Pino structured logging** | II (Backend) | All notification dispatches (success/failure) MUST be logged via Pino with structured JSON including `notificationId`, `channel`, `recipient`. |
| **Zod validation** | VIII.4 | All notification API inputs (mark-as-read, preferences) MUST be validated via Zod schemas. |
| **JWT auth on all endpoints** | VIII.5 | Notification list/read endpoints MUST be protected by auth middleware. Users can only access their own notifications. |
| **Rate limiting** | VIII.3 | Notification endpoints: 60 req/min (Public API). |
| **No hardcoded secrets** | VIII.1 | SMTP credentials, SMS API keys MUST use `.env` files with `.env.example` templates. |
| **API envelope** | VI.2 | All notification API responses MUST follow `{ success, data, meta }` / `{ success, error }` format. |
| **Pagination** | VI.5 | `GET /api/v1/notifications` MUST support `?page=1&limit=20` with standard `meta` pagination. |
| **Prisma schema standards** | X (Prisma) | `Notification` model MUST use `@@map()`, `@map()`, UUIDv4 IDs, `@db.Timestamptz()`, indexes on `userId` and `read`. |
| **Minimal dependencies** | IX.6 | Justify any new email templating library. Prefer Fastify/Node built-in capabilities where possible. |
| **YAGNI** | IX.1 | Phase 1: Email + In-App only. SMS is Phase 2. Do not build SMS infrastructure until email + in-app are stable. |
| **No `process.env` directly** | Anti-Patterns | All config (SMTP host, from address, frontend URL) MUST come from validated config objects, not raw `process.env`. |
| **TDD** | V | Notification service MUST have 80%+ test coverage. Email sends MUST be mocked in tests (no real SMTP calls). |
