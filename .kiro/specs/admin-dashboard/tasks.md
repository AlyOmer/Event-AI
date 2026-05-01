# Tasks — Module 009: Admin Dashboard

## Task List

- [x] 1. Backend: Admin Pydantic schemas
  - [x] 1.1 Create `packages/backend/src/schemas/admin.py` with `AdminVendorRead`, `AdminVendorStatusUpdate`, `AdminUserVendorSummary`, `AdminUserRead`, and `AdminStatsResponse` Pydantic models
  - [x] 1.2 Add `model_config = {"from_attributes": True}` to all read schemas

- [x] 2. Backend: Platform stats route
  - [x] 2.1 Create `packages/backend/src/api/v1/admin/stats.py` with `GET /` route protected by `require_admin`
  - [x] 2.2 Implement stats query using scalar subqueries for `total_users`, `active_vendors`, `pending_vendors`, `total_bookings`, `confirmed_bookings`, `pending_bookings`, `total_revenue` — all in a single DB round-trip
  - [x] 2.3 Return `{ "success": true, "data": <AdminStatsResponse>, "meta": {} }`

- [x] 3. Backend: Admin vendors route
  - [x] 3.1 Create `packages/backend/src/api/v1/admin/vendors.py` with `GET /` route accepting `page`, `limit`, `status`, `q` query params, protected by `require_admin`
  - [x] 3.2 Implement paginated vendor query with optional `status` filter (ILIKE on `business_name` and `contact_email` for `q`)
  - [x] 3.3 Return `{ "success": true, "data": [...], "meta": { "total", "page", "limit", "pages" } }`
  - [x] 3.4 Add `PATCH /{vendor_id}/status` route accepting `AdminVendorStatusUpdate` body, protected by `require_admin`
  - [x] 3.5 Implement status update: set `vendor.status`, commit, then emit `vendor.approved` / `vendor.rejected` / `vendor.suspended` domain event via `event_bus`
  - [x] 3.6 Return HTTP 404 `NOT_FOUND_VENDOR` if vendor does not exist

- [x] 4. Backend: Admin users route
  - [x] 4.1 Create `packages/backend/src/api/v1/admin/users.py` with `GET /` route accepting `page`, `limit`, `role`, `q` query params, protected by `require_admin`
  - [x] 4.2 Implement paginated user query with LEFT OUTER JOIN on `vendors` table (join on `vendors.user_id = users.id`) to fetch linked vendor summary without N+1 queries
  - [x] 4.3 Apply optional `role` filter and `q` ILIKE filter on `email`, `first_name`, `last_name`
  - [x] 4.4 Return `{ "success": true, "data": [...], "meta": { "total", "page", "limit", "pages" } }`

- [x] 5. Backend: Register new routers in main.py
  - [x] 5.1 Import `admin_stats_router`, `admin_vendors_router`, `admin_users_router` in `packages/backend/src/main.py`
  - [x] 5.2 Register routers at `/api/v1/admin/stats`, `/api/v1/admin/vendors`, `/api/v1/admin/users`

- [x] 6. Backend: Integration tests — stats endpoint
  - [x] 6.1 Create `packages/backend/tests/test_admin_stats.py` with `admin_user`, `regular_user`, `admin_token`, `user_token` fixtures using `httpx.AsyncClient` + `ASGITransport`
  - [x] 6.2 Test: `GET /api/v1/admin/stats` with admin token returns correct counts for seeded test data
  - [x] 6.3 Test: `GET /api/v1/admin/stats` with non-admin token returns HTTP 403

- [x] 7. Backend: Integration tests — vendors endpoint
  - [x] 7.1 Create `packages/backend/tests/test_admin_vendors.py` with `pending_vendor`, `active_vendor` fixtures
  - [x] 7.2 Test: `GET /api/v1/admin/vendors` returns paginated list with correct `meta` fields
  - [x] 7.3 Test: `GET /api/v1/admin/vendors?status=PENDING` returns only pending vendors
  - [x] 7.4 Test: `GET /api/v1/admin/vendors?q=test` matches `business_name` and `contact_email`
  - [x] 7.5 Test: `GET /api/v1/admin/vendors` with non-admin token returns HTTP 403
  - [x] 7.6 Test: `PATCH /api/v1/admin/vendors/{id}/status` with `{ status: "ACTIVE" }` sets vendor to ACTIVE
  - [x] 7.7 Test: `PATCH /api/v1/admin/vendors/{id}/status` with `{ status: "REJECTED" }` sets vendor to REJECTED
  - [x] 7.8 Test: `PATCH /api/v1/admin/vendors/{non_existent_id}/status` returns HTTP 404
  - [x] 7.9 Test: `PATCH /api/v1/admin/vendors/{id}/status` with non-admin token returns HTTP 403

- [x] 8. Backend: Integration tests — users endpoint
  - [x] 8.1 Create `packages/backend/tests/test_admin_users.py`
  - [x] 8.2 Test: `GET /api/v1/admin/users` returns paginated list with correct `meta` fields
  - [x] 8.3 Test: `GET /api/v1/admin/users?role=vendor` returns only vendor-role users
  - [x] 8.4 Test: `GET /api/v1/admin/users?q=test` matches email, first_name, last_name
  - [x] 8.5 Test: `GET /api/v1/admin/users` with non-admin token returns HTTP 403

- [x] 9. Frontend: Update `packages/admin/src/lib/api.ts`
  - [x] 9.1 Update `getVendors` to accept `{ page, limit, status, q }` params and pass them as query parameters
  - [x] 9.2 Update `getUsers` to accept `{ page, limit, role, q }` params and pass them as query parameters
  - [x] 9.3 Add `getCategories`, `createCategory`, `deleteCategory` helper functions calling `/admin/categories` endpoints

- [x] 10. Frontend: Vendors page — filter and search
  - [x] 10.1 Add `status` filter dropdown (`All | Pending | Active | Suspended | Rejected`) to `packages/admin/src/app/vendors/page.tsx`
  - [x] 10.2 Add 300ms debounce to the search input using `useCallback` + `useEffect`
  - [x] 10.3 Pass `{ page, limit, status, q }` as React Query key and API params so filters trigger refetch
  - [x] 10.4 Add `owner_email` column to the vendors table
  - [x] 10.5 Add "Suspend" action button for `ACTIVE` vendors (calls `updateVendorStatus` with `"SUSPENDED"`)

- [x] 11. Frontend: Users page — filter, search, and pagination
  - [x] 11.1 Add `role` filter dropdown (`All | User | Vendor | Admin`) to `packages/admin/src/app/users/page.tsx`
  - [x] 11.2 Add search input with 300ms debounce
  - [x] 11.3 Add pagination controls (Prev / Next) using `page` state
  - [x] 11.4 Pass `{ page, limit, role, q }` as React Query key and API params

- [x] 12. Frontend: Dashboard — stats wiring and analytics panel
  - [x] 12.1 Add "Revenue" stat card to `packages/admin/src/app/page.tsx` showing `totalRevenue` formatted as `PKR {amount}`
  - [x] 12.2 Set `staleTime: 60_000` on the `getStats` React Query call
  - [x] 12.3 Replace the "Analytics charts coming soon" placeholder in the Overview panel with a booking status breakdown (Pending / Confirmed / Other rows with progress bars)
  - [x] 12.4 Derive breakdown values from `stats` data — no additional API call

- [x] 13. Frontend: Settings page
  - [x] 13.1 Replace the stub in `packages/admin/src/app/settings/page.tsx` with a "Platform Info" section showing API URL, admin email from `useSession`, and portal version
  - [x] 13.2 Add a "Categories" section that fetches from `getCategories` and renders a list with delete buttons
  - [x] 13.3 Add a "New Category" form with `name`, `slug`, and optional `description` fields that calls `createCategory` on submit
  - [x] 13.4 Show success/error toasts for create and delete operations
  - [x] 13.5 Invalidate the `["categories"]` React Query cache after create or delete
