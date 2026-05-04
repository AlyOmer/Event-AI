# Tasks: Vendor Portal Complete

## Phase 1 — Backend Core

### 1. Pydantic schemas
- [x] Create `packages/backend/src/schemas/vendor_dashboard.py` — `RecentBookingItem`, `DashboardStats`
- [x] Create `packages/backend/src/schemas/vendor_availability.py` — `AvailabilityUpsert`, `BulkAvailabilityUpsert`, `AvailabilityRead`
- [x] `BulkAvailabilityUpsert.entries`: `Field(..., min_length=1, max_length=90)`
- [x] `AvailabilityUpsert.status`: `Literal["available", "blocked", "tentative"]` — no `"booked"`
- [x] `AvailabilityRead`: `model_config = {"from_attributes": True}`

### 2. VendorDashboardService
- [x] Create `packages/backend/src/services/vendor_dashboard_service.py`
- [x] `get_dashboard_stats(session, vendor_id)` — 5 COUNT queries + 1 JOIN for recent bookings, limited to 5 ordered by `created_at DESC`
- [x] Use `selectinload` on services join
- [x] Export singleton `vendor_dashboard_service`

### 3. VendorAvailabilityService
- [x] Create `packages/backend/src/services/vendor_availability_service.py`
- [x] `list_availability` — inclusive date range filter, optional `service_id`
- [x] `upsert_availability` — SELECT + INSERT/UPDATE, handles NULL `service_id`
- [x] `bulk_upsert_availability` — single transaction, rollback all on failure
- [x] Raise 422 `VALIDATION_PAST_DATE` for past dates
- [x] Raise 422 `VALIDATION_INVALID_STATUS` for `status="booked"`
- [x] Export singleton `vendor_availability_service`

### 4. GET /api/v1/vendors/me/dashboard
- [x] Route in `packages/backend/src/api/v1/vendors.py`, vendor role required
- [x] Returns `{ success, data: DashboardStats }` HTTP 200
- [x] 404 `NOT_FOUND_VENDOR_PROFILE` if no vendor profile

### 5. GET /api/v1/vendors/me/services
- [x] Query params: `page`, `limit`, `search` (ILIKE), `category`
- [x] Returns paginated envelope with `meta.total`, `meta.pages`
- [x] Only `is_active=true` services for current vendor

### 6. Availability endpoints
- [x] `GET /api/v1/vendors/me/availability` — date range + optional `service_id`
- [x] `POST /api/v1/vendors/me/availability` — single upsert
- [x] `POST /api/v1/vendors/me/availability/bulk` — bulk upsert

### 7. Fix GET /api/v1/bookings/{id} for vendor access
- [x] Allow access if `user_id == booking.user_id` OR `vendor_id == booking.vendor_id`
- [x] 403 `AUTH_FORBIDDEN` if neither; 404 `NOT_FOUND_BOOKING` if not found

### 8. Backend checkpoint
- [x] `uv run pytest` passes with zero failures

---

## Phase 2 — Vendor Core

### 9. Auth store
- [x] Replace `Vendor` interface — camelCase fields, correct status values
- [x] `_mapUser` — `first_name → firstName`, `email_verified → emailVerified`
- [x] `_mapVendor` — `business_name → businessName`, `contact_email → contactEmail`
- [x] `fetchProfile` calls `GET /api/v1/vendors/profile/me`

### 10. Token refresh flow
- [x] Axios interceptor catches 401, calls `/auth/refresh`, retries original request
- [x] On refresh failure: clear tokens, redirect to `/login`
- [x] Google OAuth callback: strip tokens from URL after `loginWithTokens`

### 11. Vendor test infrastructure
- [x] `pnpm add -D fast-check msw` in `packages/Vendor`
- [x] `jest.config.js` with `setupFilesAfterEnv`, `testEnvironment: jsdom`, path aliases
- [x] `packages/Vendor/src/__tests__/msw/handlers.ts` — MSW handlers for all vendor API endpoints
- [x] `packages/Vendor/src/__tests__/msw/server.ts` — MSW node server

### 12. VendorLayout component
- [x] Sidebar nav: Dashboard, Services, Bookings, Availability, Profile
- [x] Active nav item via `usePathname()`
- [x] Vendor `businessName` + status badge in sidebar footer
- [x] Logout: calls `/auth/logout`, clears tokens, redirects to `/login`
- [x] TopBar with notification bell; `useSSE` hook mounted here

### 13. useSSE hook
- [x] `EventSource` with `?token=<accessToken>`
- [x] `booking.created` → `toast.info`, invalidate `["bookings"]`, `["notifications-unread"]`
- [x] `booking.confirmed` → `toast.success`; `booking.cancelled` → `toast.warning`; `ping` → no-op
- [x] Error: exponential backoff (1s→2s→4s→8s→16s→30s max), show "Reconnecting…"
- [x] Re-create on `accessToken` change; cleanup on unmount

### 14. React Query hooks
- [x] Query hooks: `use-dashboard`, `use-vendor-bookings`, `use-booking-detail`, `use-booking-messages`, `use-vendor-services`, `use-vendor-availability`, `use-vendor-profile`, `use-notifications`, `use-unread-count`
- [x] Mutation hooks: `use-confirm-booking`, `use-reject-booking`, `use-send-message`, `use-create-service`, `use-update-service`, `use-delete-service`, `use-upsert-availability`, `use-bulk-upsert-availability`, `use-update-profile`, `use-mark-notification-read`, `use-mark-all-read`
- [x] All mutations: `onError` → `getApiError` → `toast.error`, revert optimistic updates
- [x] HTTP 422: call `setError` for field-level errors when callback provided

### 15. Dashboard page
- [x] `useDashboard()` hook; skeleton loading; error + Retry button
- [x] 4 stat cards (Total, Pending, Confirmed, Active Services) + Recent Bookings table
- [x] Status badge colors: pending→yellow, confirmed→blue, completed→green, cancelled/rejected→red/grey, in_progress→indigo, no_show→grey

### 16. Bookings page
- [x] `useVendorBookings(filters)`; filter tabs: All, Pending, Confirmed, In Progress, Completed, Cancelled
- [x] Table: Customer Name, Event Date, Status Badge, Total Price, Actions
- [x] Confirm: optimistic update → `confirmed`, reverts on error
- [x] Reject: modal with optional reason textarea; row click → `/bookings/{id}`

### 17. Booking Detail page
- [x] `useBookingDetail(id)` + `useBookingMessages(id)`
- [x] Fields: Customer Name, Event Date, Service Name, Status Badge, Total Price, Event Location
- [x] Messages: chronological, vendor right-aligned, customer left-aligned; send button disabled in-flight

### 18. Services page
- [x] `useVendorServices(filters)`; table: Name, Category, Status, Capacity, Price Range, Actions
- [x] Add → `/services/new`; Edit → `/services/{id}/edit`; Delete: confirmation dialog
- [x] React Hook Form + Zod; on success: invalidate `["services"]`, navigate to `/services`

### 19. Availability page
- [x] `useVendorAvailability(startDate, endDate)`; monthly 7-column calendar grid
- [x] Cell colors: available→green, blocked→red, tentative→yellow, booked→blue (read-only)
- [x] Day click → modal: Available / Blocked / Tentative / Booked (disabled); optimistic update
- [x] SSE `booking.confirmed` → `invalidateQueries(["availability"])`

### 20. Profile page
- [x] `useVendorProfile()`; pre-populated: Business Name, Description, Contact Email, Phone, Website, City, Region
- [x] Status badge read-only; Edit enables fields + Cancel resets to original values
- [x] Zod: Business Name required; Website must start with `http://` or `https://`

---

## Phase 3 — Real-Time and Polish

### 21. Notifications
- [x] Bell → `useUnreadCount()`, badge when `count > 0`
- [x] Dropdown: 10 most recent, message + timestamp + unread dot
- [x] Click → `useMarkNotificationRead`; "Mark all as read" → `useMarkAllRead`

### 22. Route guards
- [x] Unauthenticated → `/login`; authenticated vendor on `/login` → `/dashboard`
- [x] `middleware.ts` reads non-sensitive cookie flag

### 23. Vendor checkpoint
- [ ] `pnpm test` passes with zero failures
- [ ] `pnpm typecheck` passes with zero errors
