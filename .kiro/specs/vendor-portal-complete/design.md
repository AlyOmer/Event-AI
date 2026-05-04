# Design Document: Vendor Portal Complete

## Overview

This document describes the technical design for the Vendor Portal Complete feature — a fully functional vendor-facing web application within the Event-AI platform. The portal runs on Next.js 15 at port 3002 and communicates exclusively with the FastAPI backend at port 5000 via `/api/v1/`.

The work falls into two categories:

1. **Backend gaps**: Several endpoints the Vendor depends on are missing or have the wrong shape (`GET /api/v1/vendors/me/dashboard`, `GET /api/v1/vendors/me/services` with pagination/search, `GET|POST /api/v1/vendors/me/availability`, `POST /api/v1/vendors/me/availability/bulk`).
2. **Vendor gaps**: The auth store has shape mismatches with the real backend, pages use raw `useState`/`useEffect` instead of React Query, the shared sidebar layout is duplicated per-page, and key features (booking detail view, booking messages thread, SSE-driven notifications) are absent.

### Key Design Decisions

- **No new DB tables**: All required data already exists in `bookings`, `services`, `vendor_availability`, `booking_messages`, `notifications`. The dashboard endpoint is a pure aggregation query.
- **Shared layout component**: Extract the sidebar into a single `VendorLayout` component used by all authenticated pages, eliminating the current per-page duplication.
- **React Query throughout**: Replace all `useState`/`useEffect` data-fetching with `useQuery`/`useMutation` hooks. `staleTime: 30_000` on all queries; `refetchOnWindowFocus: true` for bookings and notifications.
- **SSE via a singleton hook**: A single `useSSE` hook mounted in the root layout manages the `EventSource` connection, dispatches events to React Query's cache via `queryClient.invalidateQueries`, and handles reconnection with exponential backoff.
- **Auth store alignment**: Fix the `Vendor` type and `_mapUser`/`_mapVendor` helpers to match the real backend envelope. Tokens stay in memory + `localStorage` as they already do (banned: NextAuth, Auth0, sessionStorage).

---

## Architecture

### System Topology

```
Browser (port 3002)
  └── Next.js 15 App Router
        ├── /login, /register          (public)
        └── /dashboard, /bookings,     (protected — VendorLayout)
            /services, /availability,
            /profile
              │
              │  HTTP (Axios, JWT Bearer)
              ▼
        FastAPI Backend (port 5000)
          /api/v1/
            ├── auth.*          (login, refresh, logout, Google OAuth)
            ├── vendors.*       (profile, dashboard, services, availability, bookings)
            ├── bookings.*      (detail, messages)
            ├── notifications.* (list, unread-count, mark-read, read-all)
            └── sse/stream      (SSE — JWT via ?token= query param)
              │
              ▼
        PostgreSQL (Neon)
          vendors, services, bookings, booking_messages,
          vendor_availability, notifications, domain_events
```

### Request / Response Flow

```
Vendor action (e.g. "Confirm booking")
  │
  ├─ React Query mutation fires
  │    └─ Axios POST /api/v1/vendors/me/bookings/{id}/status
  │         └─ Request interceptor injects Bearer token
  │
  ├─ FastAPI route handler
  │    └─ Depends(get_current_user) validates JWT
  │    └─ booking_service.update_status(...)
  │         ├─ State machine validation
  │         ├─ DB update (SQLModel / asyncpg)
  │         ├─ event_bus.emit("booking.confirmed", ...)
  │         │    └─ SSEConnectionManager.push(vendor_user_id, ...)
  │         └─ Returns BookingRead
  │
  └─ Response { success: true, data: BookingRead }
       ├─ React Query cache updated (optimistic → confirmed)
       └─ SSE event received by vendor's browser
            └─ Toast notification displayed
            └─ queryClient.invalidateQueries(["bookings"])
```

---

## Components and Interfaces

### Backend: New / Modified Endpoints

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| `GET` | `/api/v1/vendors/me/dashboard` | **NEW** | Aggregation query |
| `GET` | `/api/v1/vendors/me/services` | **MODIFY** | Add pagination + search (currently `/services/my-services`) |
| `GET` | `/api/v1/vendors/me/availability` | **NEW** | Date-range filtered |
| `POST` | `/api/v1/vendors/me/availability` | **NEW** | Single upsert |
| `POST` | `/api/v1/vendors/me/availability/bulk` | **NEW** | Bulk upsert |
| `GET` | `/api/v1/bookings/{id}` | **MODIFY** | Allow vendor access (currently user-only) |
| `GET` | `/api/v1/bookings/{id}/messages` | exists | No change needed |
| `POST` | `/api/v1/bookings/{id}/messages` | exists | No change needed |

### Backend: New Service Class

`VendorDashboardService` — a new singleton in `packages/backend/src/services/vendor_dashboard_service.py`:

```python
class VendorDashboardService:
    async def get_dashboard_stats(
        self, session: AsyncSession, vendor_id: uuid.UUID
    ) -> DashboardStats:
        ...

vendor_dashboard_service = VendorDashboardService()
```

`VendorAvailabilityService` — a new singleton in `packages/backend/src/services/vendor_availability_service.py`:

```python
class VendorAvailabilityService:
    async def list_availability(
        self, session: AsyncSession, vendor_id: uuid.UUID,
        start_date: date, end_date: date, service_id: Optional[uuid.UUID]
    ) -> list[VendorAvailability]: ...

    async def upsert_availability(
        self, session: AsyncSession, vendor_id: uuid.UUID,
        entry: AvailabilityUpsert
    ) -> VendorAvailability: ...

    async def bulk_upsert_availability(
        self, session: AsyncSession, vendor_id: uuid.UUID,
        entries: list[AvailabilityUpsert]
    ) -> list[VendorAvailability]: ...

vendor_availability_service = VendorAvailabilityService()
```

### Vendor: Component Hierarchy

```
app/layout.tsx                    ← QueryClientProvider, ThemeProvider
  └── VendorLayout (new)          ← sidebar + header, SSE hook mounted here
        ├── Sidebar               ← nav links, vendor name/status, logout
        ├── TopBar                ← notification bell + unread badge
        └── {children}
              ├── DashboardPage
              ├── BookingsPage
              │     └── BookingDetailPage  (/bookings/[id])
              ├── ServicesPage
              │     ├── ServiceNewPage     (/services/new)
              │     └── ServiceEditPage    (/services/[id]/edit)
              ├── AvailabilityPage
              └── ProfilePage
```

### Vendor: React Query Hooks

All hooks live in `packages/Vendor/src/lib/hooks/`:

| Hook | Query key | Endpoint |
|------|-----------|----------|
| `useDashboard` | `["dashboard"]` | `GET /vendors/me/dashboard` |
| `useVendorBookings` | `["bookings", filters]` | `GET /vendors/me/bookings` |
| `useBookingDetail` | `["booking", id]` | `GET /bookings/{id}` |
| `useBookingMessages` | `["booking-messages", id]` | `GET /bookings/{id}/messages` |
| `useVendorServices` | `["services", filters]` | `GET /vendors/me/services` |
| `useVendorAvailability` | `["availability", month, serviceId]` | `GET /vendors/me/availability` |
| `useVendorProfile` | `["vendor-profile"]` | `GET /vendors/profile/me` |
| `useNotifications` | `["notifications"]` | `GET /notifications/` |
| `useUnreadCount` | `["notifications-unread"]` | `GET /notifications/unread-count` |

Mutations:

| Hook | Endpoint |
|------|----------|
| `useConfirmBooking` | `PATCH /vendors/me/bookings/{id}/status` |
| `useRejectBooking` | `PATCH /vendors/me/bookings/{id}/status` |
| `useSendMessage` | `POST /bookings/{id}/messages` |
| `useCreateService` | `POST /services/` |
| `useUpdateService` | `PUT /services/{id}` |
| `useDeleteService` | `DELETE /services/{id}` |
| `useUpsertAvailability` | `POST /vendors/me/availability` |
| `useBulkUpsertAvailability` | `POST /vendors/me/availability/bulk` |
| `useUpdateProfile` | `PUT /vendors/profile/me` |
| `useMarkNotificationRead` | `PATCH /notifications/{id}/read` |
| `useMarkAllRead` | `PATCH /notifications/read-all` |

### Vendor: Auth Store Changes

The `Vendor` interface must be updated to match the real backend `VendorRead` schema:

```typescript
// BEFORE (mismatched)
export interface Vendor {
  name: string;           // backend: business_name
  businessType: string;   // backend: doesn't exist
  verified: boolean;      // backend: doesn't exist
  tier: 'BRONZE'|...;     // backend: doesn't exist
  status: 'PENDING'|'ACTIVE'|'SUSPENDED'|'DEACTIVATED';  // backend: no DEACTIVATED
}

// AFTER (aligned)
export interface Vendor {
  id: string;
  userId: string;
  businessName: string;   // mapped from business_name
  description: string | null;
  contactEmail: string;   // mapped from contact_email
  contactPhone: string | null;
  website: string | null;
  logoUrl: string | null;
  city: string | null;
  region: string | null;
  status: 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'REJECTED';
  rating: number;
  totalReviews: number;
  categories: CategoryRead[];
}
```

A new `_mapVendor` helper maps the backend snake_case response to this interface. The `fetchProfile` action calls `GET /api/v1/vendors/profile/me` (not `/vendors/me`).

---

## Data Models

### New Backend Schemas

**`DashboardStats`** (Pydantic response model):
```python
class RecentBookingItem(BaseModel):
    id: uuid.UUID
    service_name: str
    event_date: date
    status: BookingStatus
    total_price: float
    currency: str
    client_name: Optional[str]

class DashboardStats(BaseModel):
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    active_services: int
    total_services: int
    recent_bookings: list[RecentBookingItem]  # 5 most recent
```

**`AvailabilityUpsert`** (Pydantic request model):
```python
class AvailabilityUpsert(BaseModel):
    date: date
    status: Literal["available", "blocked", "tentative"]
    service_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
```

Note: `"booked"` is excluded from the upsert schema — that status is set only by the booking service when a booking is confirmed.

**`BulkAvailabilityUpsert`**:
```python
class BulkAvailabilityUpsert(BaseModel):
    entries: list[AvailabilityUpsert] = Field(..., min_length=1, max_length=90)
```

**`AvailabilityRead`** (Pydantic response model):
```python
class AvailabilityRead(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    service_id: Optional[uuid.UUID]
    date: date
    status: str
    notes: Optional[str]
    booking_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### Existing Models Used (No Changes)

- `Booking` — used as-is; `BookingRead` returned from all booking endpoints
- `BookingMessage` / `BookingMessageRead` — used as-is
- `VendorAvailability` — used as-is; new service layer wraps it
- `Service` — used as-is; `ServiceRead` from `schemas/service.py`
- `Notification` / `NotificationRead` — used as-is
- `Vendor` / `VendorRead` — used as-is

---

## SSE / Real-Time Design

### Backend (existing, no changes needed)

The `SSEConnectionManager` at `app.state.connection_manager` already handles per-user queues. The `booking_service` already emits `booking.created`, `booking.confirmed`, `booking.cancelled` domain events via `event_bus`. The event bus listener (in `services/event_bus_service.py`) is responsible for pushing to the SSE manager.

The SSE stream endpoint at `GET /api/v1/sse/stream?token=<jwt>` is already implemented.

### Vendor: `useSSE` Hook

A new hook `packages/Vendor/src/lib/hooks/use-sse.ts` manages the connection lifecycle:

```
useSSE()
  ├── Creates EventSource with ?token=<accessToken>
  ├── Listens for: booking.created, booking.confirmed, booking.cancelled
  │     └── Each event:
  │           ├── Shows toast notification
  │           ├── queryClient.invalidateQueries(["bookings"])
  │           └── queryClient.invalidateQueries(["notifications-unread"])
  ├── Listens for: ping (no-op, keeps connection alive)
  ├── On error:
  │     ├── Closes EventSource
  │     └── Schedules reconnect with exponential backoff
  │           (1s → 2s → 4s → 8s → 16s → 30s max)
  └── Cleanup: closes EventSource on unmount
```

The hook is mounted once in `VendorLayout` so it persists across page navigations. It reads the access token from the auth store and re-creates the `EventSource` when the token changes.

### SSE Event → UI Mapping

| SSE event type | Toast message | Cache invalidation |
|----------------|---------------|--------------------|
| `booking.created` | "New booking request received" | `["bookings"]`, `["notifications-unread"]` |
| `booking.confirmed` | "Booking confirmed" | `["bookings"]`, `["notifications-unread"]` |
| `booking.cancelled` | "Booking cancelled" | `["bookings"]`, `["notifications-unread"]` |

---

## Data Flow Diagrams

### Dashboard Load

```
DashboardPage mounts
  └── useDashboard() → useQuery(["dashboard"])
        └── GET /api/v1/vendors/me/dashboard
              └── VendorDashboardService.get_dashboard_stats(vendor_id)
                    ├── SELECT COUNT(*) FROM bookings WHERE vendor_id=? (total)
                    ├── SELECT COUNT(*) FROM bookings WHERE vendor_id=? AND status='pending'
                    ├── SELECT COUNT(*) FROM bookings WHERE vendor_id=? AND status='confirmed'
                    ├── SELECT COUNT(*) FROM services WHERE vendor_id=? AND is_active=true
                    ├── SELECT COUNT(*) FROM services WHERE vendor_id=?
                    └── SELECT * FROM bookings JOIN services WHERE vendor_id=?
                          ORDER BY created_at DESC LIMIT 5
              └── Returns DashboardStats
        └── React renders stat cards + recent bookings table
```

### Booking Confirm Flow (with optimistic update)

```
Vendor clicks "Confirm"
  └── useConfirmBooking mutation fires
        ├── Optimistic update: set booking.status = "confirmed" in cache
        └── PATCH /api/v1/vendors/me/bookings/{id}/status { status: "confirmed" }
              └── booking_service.update_status(...)
                    ├── Validates pending → confirmed transition
                    ├── Sets booking.confirmed_at, confirmed_by
                    ├── event_bus.emit("booking.confirmed", ...)
                    │     └── SSEConnectionManager.push(vendor_user_id, ...)
                    └── Returns BookingRead
              └── On success: cache updated with server response
              └── On error: optimistic update reverted, toast error shown
```

### Availability Upsert Flow

```
Vendor clicks calendar day → selects "Blocked"
  └── useUpsertAvailability mutation fires
        ├── Optimistic update: update calendar cell color
        └── POST /api/v1/vendors/me/availability { date, status: "blocked" }
              └── VendorAvailabilityService.upsert_availability(...)
                    └── INSERT ... ON CONFLICT (vendor_id, service_id, date)
                          DO UPDATE SET status=excluded.status, ...
              └── On success: queryClient.invalidateQueries(["availability"])
              └── On error: optimistic update reverted, toast error shown
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: User field mapping is a total function

*For any* backend user object containing snake_case fields (`first_name`, `last_name`, `email_verified`), the `_mapUser` function SHALL produce a camelCase object where `firstName === first_name`, `lastName === last_name`, and `emailVerified === email_verified`, regardless of the values of those fields.

**Validates: Requirements 1.2**

### Property 2: Vendor field mapping is a total function

*For any* backend vendor profile object, the `_mapVendor` function SHALL produce a Vendor `Vendor` object where `businessName === business_name`, `contactEmail === contact_email`, and `status` is one of `PENDING | ACTIVE | SUSPENDED | REJECTED`.

**Validates: Requirements 1.3**

### Property 3: Dashboard recent bookings are the N most recent

*For any* vendor with K bookings (K ≥ 5), the `recent_bookings` array returned by `GET /api/v1/vendors/me/dashboard` SHALL contain exactly 5 items, and for any two items i and j where i appears before j in the array, `i.event_date >= j.event_date`.

**Validates: Requirements 2.5**

### Property 4: Status badge color mapping is exhaustive

*For any* booking status value in `{ pending, confirmed, in_progress, completed, cancelled, rejected, no_show }`, the status badge component SHALL render with a non-empty CSS class string, and the class for `pending` SHALL include a yellow/warning token, `confirmed` a blue token, `completed` a green token, and `cancelled`/`rejected` a red/grey token.

**Validates: Requirements 2.6**

### Property 5: Service pagination invariants

*For any* vendor with N active services and any valid `page` and `limit` parameters, the response from `GET /api/v1/vendors/me/services` SHALL satisfy: `meta.total == N`, `len(data) <= limit`, and `len(data) == min(limit, max(0, N - (page-1)*limit))`.

**Validates: Requirements 3.1**

### Property 6: Service soft-delete sets is_active = false

*For any* service belonging to the authenticated vendor, after calling `DELETE /api/v1/services/{id}`, a subsequent `GET /api/v1/vendors/me/services` SHALL not include that service in its results, and a direct DB lookup SHALL show `is_active == false`.

**Validates: Requirements 3.4**

### Property 7: Booking list is sorted by event_date descending

*For any* vendor with bookings, the `data` array returned by `GET /api/v1/vendors/me/bookings` SHALL be ordered such that for any two adjacent items i and j (i before j), `i.event_date >= j.event_date`.

**Validates: Requirements 4.1**

### Property 8: Status filter returns only matching bookings

*For any* status value S and any vendor, the `data` array returned by `GET /api/v1/vendors/me/bookings?status=S` SHALL contain only bookings where `booking.status == S`.

**Validates: Requirements 4.2**

### Property 9: Availability date-range filter is inclusive

*For any* `start_date` and `end_date`, the records returned by `GET /api/v1/vendors/me/availability?start_date=X&end_date=Y` SHALL satisfy: for every record r, `start_date <= r.date <= end_date`.

**Validates: Requirements 5.1**

### Property 10: Availability upsert is idempotent

*For any* availability entry `{ vendor_id, service_id, date, status }`, calling `POST /api/v1/vendors/me/availability` twice with the same payload SHALL result in exactly one record in the database with the latest `status`, and the second call SHALL return HTTP 200 (not 409).

**Validates: Requirements 5.2**

### Property 11: URL validation rejects non-http(s) strings

*For any* string that does not start with `http://` or `https://`, the profile form's URL validator SHALL return a validation error and SHALL NOT call the backend update endpoint.

**Validates: Requirements 6.5**

### Property 12: SSE event types each produce a toast

*For any* SSE event type in `{ booking.created, booking.confirmed, booking.cancelled }`, when the `useSSE` hook receives that event, a toast notification SHALL be displayed with a non-empty message string.

**Validates: Requirements 7.2, 7.3**

### Property 13: API error envelope extraction

*For any* Axios error response whose body matches `{ success: false, error: { code: string, message: string } }`, the `getApiError` function SHALL return the value of `error.message` from that body.

**Validates: Requirements 9.2**

---

## Error Handling

### Backend Error Codes

All new endpoints follow the existing error taxonomy:

| Scenario | HTTP | Code |
|----------|------|------|
| Vendor profile not found | 404 | `NOT_FOUND_VENDOR_PROFILE` |
| Availability date in the past | 422 | `VALIDATION_PAST_DATE` |
| Availability status is `booked` (vendor cannot set) | 422 | `VALIDATION_INVALID_STATUS` |
| Bulk entries exceed limit (90) | 422 | `VALIDATION_ERROR` |
| Booking not found or not owned by vendor | 404/403 | `NOT_FOUND_BOOKING` / `AUTH_FORBIDDEN` |

### Vendor Error Handling

All React Query hooks use a shared `onError` handler that:
1. Extracts the message via `getApiError(error)` from the backend envelope
2. Displays a `toast.error(message)` via the shadcn/ui `Sonner` component
3. For mutations with optimistic updates, the `onError` callback receives the previous cache snapshot and calls `queryClient.setQueryData(key, previousData)` to revert

Network errors (no response) are detected by `axios.isAxiosError(error) && !error.response` and display the fixed message: "Unable to connect to server. Please check your connection."

HTTP 422 responses include field-level errors in `error.details[]`. Form components read these and display them next to the relevant inputs using React Hook Form's `setError` API.

---

## Testing Strategy

### Backend Tests

Location: `packages/backend/tests/`

**Unit tests** (pytest + pytest-asyncio, SQLite in-memory):
- `test_vendor_dashboard_service.py` — test `get_dashboard_stats` with known fixture data
- `test_vendor_availability_service.py` — test upsert idempotency, bulk atomicity, date-range filtering
- `test_vendors_api.py` (extend existing) — test new dashboard, availability endpoints

**Property-based tests** (pytest + Hypothesis):
- Property 3: `@given(st.lists(booking_strategy(), min_size=5))` — verify recent_bookings length and sort order
- Property 5: `@given(st.integers(min_value=1), st.integers(min_value=1, max_value=100))` — verify pagination invariants
- Property 7: `@given(st.lists(booking_strategy(), min_size=1))` — verify sort order
- Property 8: `@given(st.sampled_from(BookingStatus))` — verify filter correctness
- Property 9: `@given(date_range_strategy())` — verify date-range filter inclusivity
- Property 10: `@given(availability_entry_strategy())` — verify upsert idempotency

Each property test runs minimum 100 iterations (Hypothesis default). Tag format in test docstring:
`Feature: vendor-portal-complete, Property {N}: {property_text}`

### Vendor Tests

Location: `packages/Vendor/src/__tests__/` (Jest + React Testing Library)

**Unit tests**:
- `auth-store.test.ts` — test `_mapUser`, `_mapVendor` field mapping (Properties 1, 2)
- `api.test.ts` — test `getApiError` envelope extraction (Property 13)
- `status-badge.test.tsx` — test badge color mapping (Property 4)
- `url-validator.test.ts` — test URL validation (Property 11)

**Property-based tests** (Jest + `fast-check`):
- `auth-store.property.test.ts` — Properties 1, 2: generate random user/vendor objects, verify mapping
- `api.property.test.ts` — Property 13: generate random error envelopes, verify extraction
- `status-badge.property.test.tsx` — Property 4: for each status, verify badge renders with correct color
- `sse-hook.property.test.ts` — Property 12: for each SSE event type, verify toast is shown

**Integration tests** (React Testing Library + MSW):
- `dashboard.test.tsx` — loading states, error states, stat card rendering
- `bookings.test.tsx` — filter tabs, confirm/reject flow, optimistic update revert
- `booking-detail.test.tsx` — message thread rendering, send message
- `services.test.tsx` — CRUD flows, delete confirmation dialog
- `availability.test.tsx` — calendar rendering, date click modal, optimistic update
- `profile.test.tsx` — form validation, save/cancel flow
- `notifications.test.tsx` — unread count badge, dropdown, mark-read

**PBT library**: `fast-check` (already a common Jest companion; install via `pnpm add -D fast-check`)
**Minimum iterations**: 100 per property test (`fc.assert(fc.property(...), { numRuns: 100 })`)
