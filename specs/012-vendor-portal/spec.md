# Feature Specification: Vendor Portal

**Feature Branch**: `feature/vendor-portal`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: "Vendor Portal — Vendor profile management, booking calendar, earnings"

---

## User Scenarios & Testing

### User Story 1 — Vendor Profile Management (Priority: P1)

A vendor logs in and manages their business profile: name, description, contact details, service areas, logo, keywords, and category. Changes are validated and persisted, triggering embedding regeneration for semantic search.

**Why this priority**: The vendor profile is the foundation — without it, vendors cannot be discovered, receive bookings, or operate on the platform.

**Independent Test**: Log in as a vendor, update the business description and keywords via the profile page, verify the changes persist on refresh and a `vendor.updated` domain event is emitted.

**Acceptance Scenarios**:

1. **Given** a logged-in vendor, **When** they update their profile fields, **Then** changes are saved to the database and a `vendor.updated` event is emitted (which triggers embedding regeneration per RAG spec).
2. **Given** a vendor uploads a new logo, **When** the upload completes, **Then** the image is stored and `logoUrl` is updated.
3. **Given** invalid profile data (empty name, invalid email), **When** submitted, **Then** the system returns validation errors with descriptive messages.
4. **Given** a vendor's status is `SUSPENDED`, **When** they try to update their profile, **Then** the system returns HTTP 403 — suspended vendors cannot modify their profile.

---

### User Story 2 — Service & Pricing Management (Priority: P1)

A vendor creates, edits, and deactivates services (e.g., "Wedding Photography Package", "250-Person Catering") with category, description, capacity, unit type, and active pricing tiers.

**Why this priority**: Services are what users book — without them, the booking system has nothing to offer.

**Independent Test**: Create a service with a pricing tier, verify it appears in the vendor's service list and is bookable by users.

**Acceptance Scenarios**:

1. **Given** a logged-in vendor, **When** they create a service with category, description, and pricing, **Then** both the `Service` and `Pricing` records are created in a single transaction.
2. **Given** a vendor updates a service's price, **When** the update is saved, **Then** a `PriceHistory` record is created tracking the old/new price and change reason.
3. **Given** a vendor deactivates a service, **When** `isActive` is set to `false`, **Then** the service no longer appears in user search results but existing bookings remain intact.
4. **Given** a vendor does a bulk price upload via CSV, **When** the file is processed, **Then** a `PriceUpload` record tracks total/processed/failed records with an error log.

---

### User Story 3 — Booking Calendar & Management (Priority: P1)

A vendor views all their bookings in a calendar view, filtered by status. They can confirm, reject, or mark bookings as in-progress/completed directly from the calendar.

**Why this priority**: Vendors need to manage their booking pipeline. Without a calendar, they cannot see conflicts, confirm requests, or track upcoming events.

**Independent Test**: Navigate to the bookings page, verify pending bookings appear, confirm one, and verify the calendar updates to show it as confirmed.

**Acceptance Scenarios**:

1. **Given** a vendor with 5 pending bookings, **When** they open the booking calendar, **Then** all bookings are displayed on their respective event dates with status indicators.
2. **Given** a pending booking, **When** the vendor clicks "Confirm", **Then** the booking transitions to `confirmed`, `confirmedAt` and `confirmedBy` are set, and a `booking.confirmed` event is emitted.
3. **Given** a pending booking, **When** the vendor clicks "Reject" with a reason, **Then** the booking transitions to `rejected`, the availability slot is released, and the client is notified.
4. **Given** a booking on a date with another confirmed booking for the same service, **Then** the calendar shows a conflict indicator.
5. **Given** the vendor is viewing the calendar, **When** a new booking is created by a user, **Then** the calendar updates in real-time via SSE/WebSocket push — no page refresh needed.

---

### User Story 4 — Availability Management (Priority: P1)

A vendor blocks or unblocks specific dates on their calendar (holidays, vacations, maintenance), preventing users from booking those dates.

**Why this priority**: Without vendor-controlled availability, the system cannot prevent bookings on dates the vendor is unavailable — leading to rejections and poor user experience.

**Independent Test**: Block a date via the availability page, then attempt to book that vendor on that date and verify the system rejects it.

**Acceptance Scenarios**:

1. **Given** a vendor, **When** they block a date range, **Then** `VendorAvailability` records are created with `status: 'blocked'` for each date in the range.
2. **Given** a blocked date, **When** a user tries to book, **Then** the availability check returns `{ available: false, reason: "Vendor not available on this date" }`.
3. **Given** a vendor unblocks a date, **When** the availability record is updated to `available`, **Then** users can book that date again.

---

### User Story 5 — Earnings Dashboard (Priority: P2)

A vendor views their earnings overview: total revenue, monthly breakdown, pending payments, and per-booking earnings. Earnings are calculated from completed bookings.

**Why this priority**: Vendors need financial visibility to manage their business. However, this depends on the booking lifecycle being fully implemented (P1).

**Independent Test**: Complete 3 bookings with different prices, navigate to the earnings dashboard, and verify the total matches the sum of completed booking prices.

**Acceptance Scenarios**:

1. **Given** a vendor with completed bookings, **When** they open the earnings dashboard, **Then** they see: total revenue (sum of `totalPrice` where `status = 'completed'`), monthly breakdown (grouped by `eventDate` month), and count of completed bookings.
2. **Given** a vendor with pending and completed bookings, **When** viewing earnings, **Then** only `completed` bookings contribute to the revenue total — `pending`, `confirmed`, and `cancelled` bookings are excluded.
3. **Given** a time period filter (this month, last 3 months, this year), **When** applied, **Then** earnings are filtered to the selected date range.

---

### User Story 6 — Vendor Dashboard Overview (Priority: P2)

A vendor sees a quick summary on their dashboard: total services, active services, total bookings, pending bookings, and recent activity log.

**Why this priority**: Provides a quick operational snapshot but most data is already available through other pages. It's a convenience view.

**Independent Test**: Log in as a vendor, verify the dashboard displays correct counts for services, bookings, and recent audit log entries.

**Acceptance Scenarios**:

1. **Given** a vendor with 10 services (7 active) and 25 bookings (3 pending), **When** they open the dashboard, **Then** it displays `totalServices: 10`, `activeServices: 7`, `totalBookings: 25`, `pendingBookings: 3`.
2. **Given** recent activity, **When** the dashboard loads, **Then** the last 10 audit log entries are shown with action, timestamp, and entity type.

---

### User Story 7 — Vendor Booking Messages (Priority: P3)

A vendor views and sends messages on individual bookings to coordinate with clients (logistics, special requirements, confirmations).

**Why this priority**: Enhances vendor-client communication but not required for the core booking flow.

**Independent Test**: Open a confirmed booking, send a message, verify it appears in the message thread for both the vendor and the client.

**Acceptance Scenarios**:

1. **Given** a booking with messages, **When** the vendor opens the booking detail, **Then** messages are listed in chronological order with sender type (`vendor`/`client`/`system`).
2. **Given** a vendor sends a message, **When** submitted, **Then** a `BookingMessage` record is created with `senderType: 'vendor'` and the client receives an in-app notification.

---

### Edge Cases

- What if a vendor tries to confirm a booking for a date they've blocked? → The system warns them of the conflict but allows the override (vendor explicitly chose to confirm).
- What if a vendor's `ACTIVE` status is revoked while they have pending bookings? → Pending bookings remain but no new bookings are accepted. Existing confirmed bookings continue.
- What if two vendor users (owner + staff) update availability simultaneously? → Prisma's `upsert` on the composite unique key (`vendor_date_service`) handles this — last write wins.
- What if the CSV bulk price upload contains duplicate service names? → Each row is processed independently; duplicates create new pricing records for the same service.
- What if a vendor has zero completed bookings? → Earnings dashboard shows `PKR 0` with an empty state message.

---

## Requirements

### Functional Requirements

- **FR-001**: Vendor MUST be able to CRUD their business profile (name, description, contact, logo, service areas, keywords, category).
- **FR-002**: Vendor MUST be able to CRUD services with category, description, capacity, unit type, and active pricing.
- **FR-003**: Vendor MUST be able to view all bookings in a calendar view with status indicators and date-level conflict detection.
- **FR-004**: Vendor MUST be able to confirm, reject, and progress bookings (`pending → confirmed → in_progress → completed`) from the calendar/booking detail page.
- **FR-005**: Vendor MUST be able to block/unblock specific dates, preventing new bookings on blocked dates.
- **FR-006**: Vendor MUST be able to view earnings: total revenue from completed bookings, monthly breakdown, and per-booking detail.
- **FR-007**: Vendor MUST be able to send/receive messages on individual bookings.
- **FR-008**: Vendor MUST be able to bulk upload pricing via CSV with a processing report (total/processed/failed).
- **FR-009**: All vendor portal pages MUST be protected by JWT authentication and RBAC (`vendor:read`, `vendor:write`, `pricing:read`, `pricing:write`).
- **FR-010**: Vendor profile updates MUST emit a `vendor.updated` domain event (which triggers embedding regeneration).
- **FR-011**: Booking status changes made by vendors MUST emit the corresponding domain events (`booking.confirmed`, `booking.cancelled`, etc.).
- **FR-012**: The dashboard MUST display real-time updates via SSE/WebSocket — no polling.
- **FR-013**: All vendor data displayed in the portal MUST be fetched via React Query (TanStack Query) with proper cache invalidation on mutations.

### Key Entities

- **Vendor**: Business profile with status, tier, service areas, keywords, and rating.
- **VendorUser**: Individual user account within a vendor organization with role-based permissions (owner, admin, staff, readonly).
- **Service**: A bookable offering with category, pricing, capacity, and availability.
- **Pricing**: Active price tier for a service with effective/expiry dates, surcharges, and discounts.
- **VendorAvailability**: Date-level availability per vendor+service with blocking and lock support.
- **Booking**: Bookings assigned to this vendor, with lifecycle status and messaging.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Vendor can create a complete profile and first service within 5 minutes of registration.
- **SC-002**: Booking calendar loads within 2 seconds with up to 100 bookings in the visible date range.
- **SC-003**: All booking status transitions from the vendor portal emit the correct domain event within 1 second.
- **SC-004**: Availability blocking prevents 100% of booking attempts on blocked dates.
- **SC-005**: Earnings dashboard totals are 100% accurate against the sum of completed booking `totalPrice` values.
- **SC-006**: 100% of vendor portal pages require authentication — zero unauthenticated access.
- **SC-007**: Vendor portal achieves 60%+ component test coverage (React Testing Library).

---

## Constitution Compliance Checklist

Every implementation decision in this feature MUST satisfy the following constitution mandates:

| Constitution Rule | Section | Requirement for Vendor Portal |
|---|---|---|
| **Next.js 15 App Router** | II (Frontend) | All vendor portal pages MUST use Next.js 15 App Router with server components where appropriate. |
| **Tailwind CSS + shadcn/ui** | II (Frontend) | All UI components MUST use Tailwind CSS + shadcn/ui. No custom CSS frameworks. |
| **React Query (TanStack)** | II (Frontend) | All server state MUST be managed via React Query with proper cache keys and invalidation. |
| **NextAuth.js** | II (Frontend) | Vendor authentication MUST use NextAuth.js with JWT strategy. |
| **Event-Driven Architecture** | III.1–III.8 | Profile updates, booking status changes, and availability modifications MUST emit domain events using the standard envelope. |
| **Real-time to frontends** | III.7 | Dashboard and booking calendar MUST receive real-time updates via SSE/WebSocket — no polling. |
| **Async event fan-out** | III (Anti-patterns) | Vendor actions (confirm booking) MUST NOT synchronously chain notifications. Events fan out to consumers independently. |
| **API envelope** | VI.2 | All vendor API responses MUST follow `{ success, data, meta }` / `{ success, error }` format. |
| **Pagination** | VI.5 | Booking list, service list, and earnings MUST support `?page=1&limit=20` with standard `meta`. |
| **Error taxonomy** | VI.6 | Vendor errors MUST use `AUTH_*`, `VALIDATION_*`, `NOT_FOUND_*`, `CONFLICT_*` codes. |
| **JWT auth on all endpoints** | VIII.5 | ALL vendor API endpoints MUST be protected by auth middleware with RBAC permissions. |
| **Rate limiting** | VIII.3 | Vendor endpoints: 60 req/min. Price upload: 10 req/min. |
| **Input validation** | VIII.4 | All inputs MUST be validated via Zod schemas. Never trust client data. |
| **No hardcoded secrets** | VIII.1 | All vendor portal env vars MUST use `.env` files with `.env.example` templates. |
| **CORS explicit** | VIII.6 | Vendor portal origin MUST be explicitly listed in CORS config — no wildcard `*`. |
| **Strict TypeScript** | X (TS) | `"strict": true`. No `any` types. ESLint + Prettier enforced. |
| **Named exports** | X (TS) | Named exports preferred; default exports only for pages/layouts. |
| **File naming** | X (TS) | `kebab-case` for files, `PascalCase` for components, `camelCase` for functions. |
| **Prisma schema standards** | X (Prisma) | All vendor models use `@@map()`, `@map()`, UUIDv4 IDs, `@db.Timestamptz()`. |
| **Shared UI components** | I (Rules) | Common UI components (buttons, forms, tables, modals) belong in `packages/ui` — no duplication across portals. |
| **YAGNI** | IX.1 | Build only the pages and features specified in user stories. No speculative vendor analytics or CRM features. |
| **TDD** | V | 60%+ component test coverage. All API integration tests use mocked backend responses. |
