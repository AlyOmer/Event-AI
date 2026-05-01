# Requirements Document

## Introduction

Module 009 completes the Event-AI admin portal (`packages/admin`). The portal's Next.js UI already
exists with pages for Dashboard, Vendors, Bookings, Users, and Settings, but the backend is missing
the three API routes the portal calls: `GET /api/v1/admin/stats`, `GET /api/v1/admin/vendors`,
`GET /api/v1/admin/users`. This module wires those missing backend routes, completes the Settings
page, and adds the Analytics overview panel to the dashboard — bringing the admin portal to full
production readiness.

**What already exists (do not rebuild):**
- `packages/admin` Next.js app with login, sidebar, layout, and all page skeletons
- `packages/admin/src/lib/api.ts` — axios client with NextAuth session injection
- `packages/backend/src/api/v1/admin/approvals.py` — vendor approval workflow
- `packages/backend/src/api/v1/admin/categories.py` — category CRUD
- `packages/backend/src/api/deps.py` — `require_admin` dependency

**What is missing:**
- Backend: `GET /api/v1/admin/stats` — platform-wide counts for the dashboard stat cards
- Backend: `GET /api/v1/admin/vendors` — paginated vendor list with status filter
- Backend: `PATCH /api/v1/admin/vendors/{id}/status` — approve / suspend / reject a vendor
- Backend: `GET /api/v1/admin/users` — paginated user list with role and status filters
- Frontend: Settings page — currently a stub; needs platform config management
- Frontend: Analytics panel — dashboard "Overview" card currently shows a placeholder

---

## Glossary

- **Admin_Portal**: The Next.js application in `packages/admin/`.
- **Backend**: The FastAPI application in `packages/backend/src/api/v1/`.
- **Admin_API_Client**: The axios instance in `packages/admin/src/lib/api.ts` that attaches the
  NextAuth JWT as a Bearer token.
- **require_admin**: The FastAPI dependency in `src/api/deps.py` that enforces `role == "admin"`.
- **Stats_Response**: The JSON object returned by `GET /api/v1/admin/stats` containing platform
  aggregate counts.
- **VendorStatus**: The Python enum `PENDING | ACTIVE | SUSPENDED | REJECTED` defined in
  `src/models/vendor.py`.
- **AdminVendorRead**: A Pydantic response schema for vendor rows in the admin list, including
  `id`, `business_name`, `status`, `city`, `rating`, `total_reviews`, `created_at`, and the
  owner's `email`.
- **AdminUserRead**: A Pydantic response schema for user rows in the admin list, including `id`,
  `email`, `first_name`, `last_name`, `role`, `is_active`, `email_verified`, `last_login_at`,
  `created_at`, and an optional nested `vendor` summary.
- **Approval_Event**: The `vendor.approved` or `vendor.rejected` domain event emitted when an
  admin changes a vendor's status.

---

## Requirements

### Requirement 1: Platform Stats Endpoint

**User Story:** As an admin, I want a single endpoint that returns platform-wide aggregate counts,
so that the dashboard stat cards display accurate live data without multiple API calls.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/admin/stats` protected by `require_admin`.
2. THE endpoint SHALL return a JSON body matching:
   ```json
   {
     "success": true,
     "data": {
       "totalUsers": 0,
       "activeVendors": 0,
       "pendingVendors": 0,
       "totalBookings": 0,
       "confirmedBookings": 0,
       "pendingBookings": 0,
       "totalRevenue": 0.0
     },
     "meta": {}
   }
   ```
3. `totalUsers` SHALL be the count of all `User` rows where `is_active = true`.
4. `activeVendors` SHALL be the count of `Vendor` rows where `status = ACTIVE`.
5. `pendingVendors` SHALL be the count of `Vendor` rows where `status = PENDING`.
6. `totalBookings` SHALL be the count of all `Booking` rows.
7. `confirmedBookings` SHALL be the count of `Booking` rows where `status = confirmed`.
8. `pendingBookings` SHALL be the count of `Booking` rows where `status = pending`.
9. `totalRevenue` SHALL be the sum of `total_price` for all `Booking` rows where
   `status IN (confirmed, completed)`.
10. THE endpoint SHALL execute all counts in a single database round-trip using SQLAlchemy
    `func.count` and `func.sum` — no N+1 queries.
11. IF the requesting user is not an admin, THE Backend SHALL return HTTP 403 with error code
    `AUTH_FORBIDDEN`.

---

### Requirement 2: Admin Vendor List Endpoint

**User Story:** As an admin, I want a paginated, filterable list of all vendors so that I can
review registrations, monitor status, and take approval actions from the Vendors page.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/admin/vendors` protected by `require_admin`.
2. THE endpoint SHALL accept query parameters: `page` (int, default 1), `limit` (int, default 20,
   max 100), `status` (optional, one of `PENDING | ACTIVE | SUSPENDED | REJECTED`), `q` (optional
   string, searches `business_name` and `contact_email` case-insensitively).
3. THE endpoint SHALL return the standard envelope:
   ```json
   {
     "success": true,
     "data": [ <AdminVendorRead>, ... ],
     "meta": { "total": 0, "page": 1, "limit": 20, "pages": 1 }
   }
   ```
4. EACH `AdminVendorRead` item SHALL include: `id`, `business_name`, `status`, `city`, `region`,
   `rating`, `total_reviews`, `created_at`, and `owner_email` (the `contact_email` field from the
   `Vendor` model).
5. WHEN `status` filter is provided, THE endpoint SHALL return only vendors matching that status.
6. WHEN `q` is provided, THE endpoint SHALL filter vendors where `business_name ILIKE %q%` OR
   `contact_email ILIKE %q%`.
7. THE endpoint SHALL order results by `created_at DESC` by default.
8. THE endpoint SHALL use `selectinload` or a JOIN to avoid N+1 queries when fetching vendor data.
9. IF the requesting user is not an admin, THE Backend SHALL return HTTP 403 with error code
   `AUTH_FORBIDDEN`.

---

### Requirement 3: Admin Vendor Status Update Endpoint

**User Story:** As an admin, I want to approve, suspend, or reject a vendor from the admin portal,
so that vendor lifecycle management is handled through a single, audited API action.

#### Acceptance Criteria

1. THE Backend SHALL expose `PATCH /api/v1/admin/vendors/{vendor_id}/status` protected by
   `require_admin`.
2. THE request body SHALL be `{ "status": "ACTIVE" | "SUSPENDED" | "REJECTED", "reason": string? }`.
3. WHEN `status = ACTIVE`, THE Backend SHALL set `vendor.status = ACTIVE` and emit a
   `vendor.approved` domain event via the event bus.
4. WHEN `status = REJECTED`, THE Backend SHALL set `vendor.status = REJECTED` and emit a
   `vendor.rejected` domain event.
5. WHEN `status = SUSPENDED`, THE Backend SHALL set `vendor.status = SUSPENDED` and emit a
   `vendor.suspended` domain event.
6. THE Backend SHALL persist the status change and commit before emitting the domain event.
7. THE Backend SHALL return the updated `AdminVendorRead` object wrapped in the success envelope.
8. IF `vendor_id` does not exist, THE Backend SHALL return HTTP 404 with error code
   `NOT_FOUND_VENDOR`.
9. IF the requesting user is not an admin, THE Backend SHALL return HTTP 403 with error code
   `AUTH_FORBIDDEN`.
10. THE Backend SHALL apply a rate limit of 60 requests per minute on this endpoint.

---

### Requirement 4: Admin User List Endpoint

**User Story:** As an admin, I want a paginated list of all registered users with their role,
verification status, and linked vendor, so that I can monitor the user base and identify issues.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/admin/users` protected by `require_admin`.
2. THE endpoint SHALL accept query parameters: `page` (int, default 1), `limit` (int, default 20,
   max 100), `role` (optional, one of `user | vendor | admin`), `q` (optional string, searches
   `email`, `first_name`, `last_name` case-insensitively).
3. THE endpoint SHALL return the standard envelope:
   ```json
   {
     "success": true,
     "data": [ <AdminUserRead>, ... ],
     "meta": { "total": 0, "page": 1, "limit": 20, "pages": 1 }
   }
   ```
4. EACH `AdminUserRead` item SHALL include: `id`, `email`, `first_name`, `last_name`, `role`,
   `is_active`, `email_verified`, `last_login_at`, `created_at`, and an optional `vendor` object
   containing `{ id, business_name, status }` if the user has a linked vendor.
5. WHEN `role` filter is provided, THE endpoint SHALL return only users with that role.
6. WHEN `q` is provided, THE endpoint SHALL filter users where `email ILIKE %q%` OR
   `first_name ILIKE %q%` OR `last_name ILIKE %q%`.
7. THE endpoint SHALL order results by `created_at DESC` by default.
8. THE endpoint SHALL use `selectinload` or an outer JOIN to fetch the linked vendor in a single
   query — no N+1 queries.
9. IF the requesting user is not an admin, THE Backend SHALL return HTTP 403 with error code
   `AUTH_FORBIDDEN`.

---

### Requirement 5: Backend Router Registration

**User Story:** As a backend engineer, I want all new admin routes registered in `main.py` under
the `/api/v1/admin/` prefix, so that they are reachable and consistent with the existing admin
route structure.

#### Acceptance Criteria

1. THE Backend SHALL create `src/api/v1/admin/vendors.py` containing the vendor list and status
   update routes.
2. THE Backend SHALL create `src/api/v1/admin/users.py` containing the user list route.
3. THE Backend SHALL create `src/api/v1/admin/stats.py` containing the stats route.
4. ALL three new routers SHALL be imported and registered in `src/main.py` under the prefix
   `/api/v1/admin/vendors`, `/api/v1/admin/users`, and `/api/v1/admin/stats` respectively.
5. ALL new routes SHALL use the `require_admin` dependency from `src/api/deps.py` — no inline
   role checks.
6. ALL new routes SHALL return responses following the standard `{ success, data, meta }` envelope.

---

### Requirement 6: Admin Portal — Vendor Page Wiring

**User Story:** As an admin, I want the Vendors page to load real data from the backend and allow
me to approve, suspend, or reject vendors inline, so that vendor management is fully functional.

#### Acceptance Criteria

1. THE `getVendors` function in `packages/admin/src/lib/api.ts` SHALL call
   `GET /api/v1/admin/vendors` and return the `data` array from the response envelope.
2. THE `updateVendorStatus` function SHALL call `PATCH /api/v1/admin/vendors/{id}/status` with
   body `{ status }`.
3. THE Vendors page SHALL support a status filter dropdown (`All | Pending | Active | Suspended |
   Rejected`) that passes the `status` query parameter to the API.
4. THE Vendors page SHALL support a search input that passes the `q` query parameter to the API
   with a 300ms debounce.
5. WHEN the admin clicks Approve on a `PENDING` vendor, THE page SHALL call `updateVendorStatus`
   with `status: "ACTIVE"` and show a success toast.
6. WHEN the admin clicks Suspend on an `ACTIVE` vendor, THE page SHALL call `updateVendorStatus`
   with `status: "SUSPENDED"` and show a success toast.
7. WHEN the admin clicks Reject on a `PENDING` vendor, THE page SHALL call `updateVendorStatus`
   with `status: "REJECTED"` and show a success toast.
8. AFTER any status mutation, THE page SHALL invalidate the `["vendors"]` and `["stats"]` React
   Query cache keys.
9. THE Vendors page SHALL display `business_name`, `owner_email`, `city`, `status`, `rating`, and
   `created_at` columns in the table.

---

### Requirement 7: Admin Portal — Users Page Wiring

**User Story:** As an admin, I want the Users page to load real user data from the backend,
including each user's linked vendor status, so that I can monitor the user base.

#### Acceptance Criteria

1. THE `getUsers` function in `packages/admin/src/lib/api.ts` SHALL call
   `GET /api/v1/admin/users` and return the `data` array from the response envelope.
2. THE Users page SHALL display `first_name + last_name`, `email`, `role`, `email_verified`,
   `last_login_at`, and the linked vendor's `business_name` + `status` (if present).
3. THE Users page SHALL support a role filter dropdown (`All | User | Vendor | Admin`) that passes
   the `role` query parameter to the API.
4. THE Users page SHALL support a search input that passes the `q` query parameter to the API
   with a 300ms debounce.
5. THE Users page SHALL display a paginated table with `page` and `limit` query parameters passed
   to the API.
6. THE Users page SHALL show a loading skeleton while data is fetching and an empty state when no
   users match the filter.

---

### Requirement 8: Admin Portal — Dashboard Stats Wiring

**User Story:** As an admin, I want the dashboard stat cards to display live data from the backend
stats endpoint, so that the numbers are always accurate.

#### Acceptance Criteria

1. THE `getStats` function in `packages/admin/src/lib/api.ts` SHALL call
   `GET /api/v1/admin/stats` and return the `data` object from the response envelope.
2. THE dashboard SHALL display the following stat cards using data from `Stats_Response`:
   - "Total Users" → `totalUsers`
   - "Active Vendors" → `activeVendors`
   - "Pending Approval" → `pendingVendors`
   - "Total Bookings" → `totalBookings`
3. THE dashboard SHALL display a "Revenue" stat card showing `totalRevenue` formatted as
   `PKR {amount}`.
4. WHEN `getStats` fails, THE dashboard SHALL display an error banner with the message "Failed to
   load dashboard stats" rather than crashing.
5. THE stats query SHALL use a `staleTime` of 60 seconds in React Query to avoid excessive
   re-fetching.

---

### Requirement 9: Admin Portal — Settings Page

**User Story:** As an admin, I want a Settings page that shows platform configuration and allows
me to manage event categories, so that I can maintain the marketplace without direct database
access.

#### Acceptance Criteria

1. THE Settings page SHALL display a "Platform Info" section showing: backend API URL, current
   admin email (from NextAuth session), and portal version (from `package.json`).
2. THE Settings page SHALL display a "Categories" section that lists all event categories fetched
   from `GET /api/v1/admin/categories`.
3. THE Settings page SHALL allow an admin to create a new category via a form that calls
   `POST /api/v1/admin/categories` with `{ name, slug, description }`.
4. THE Settings page SHALL allow an admin to deactivate a category via a button that calls
   `DELETE /api/v1/admin/categories/{id}`.
5. WHEN a category has assigned vendors, THE Settings page SHALL display the backend's 409 error
   message ("Cannot delete category with assigned vendors") as a toast notification.
6. THE Settings page SHALL add `getCategories`, `createCategory`, and `deleteCategory` helper
   functions to `packages/admin/src/lib/api.ts`.

---

### Requirement 10: Admin Portal — Analytics Overview Panel

**User Story:** As an admin, I want the dashboard Overview panel to show a breakdown of bookings
by status, so that I can quickly assess platform health without navigating to the Bookings page.

#### Acceptance Criteria

1. THE dashboard Overview panel SHALL replace the "Analytics charts coming soon" placeholder with
   a booking status breakdown using data from `Stats_Response`.
2. THE panel SHALL display four status rows: Pending, Confirmed, Completed (derived from
   `totalBookings - confirmedBookings - pendingBookings`), and Cancelled.
3. EACH row SHALL show a progress bar whose width is proportional to that status's share of
   `totalBookings`.
4. WHEN `totalBookings` is 0, THE panel SHALL display an "No bookings yet" empty state.
5. THE panel SHALL not make any additional API calls — it SHALL derive all values from the
   existing `getStats` response.

---

### Requirement 11: Backend Test Suite — Admin Routes

**User Story:** As a backend engineer, I want integration tests for all three new admin endpoints,
so that regressions are caught in CI and the admin API contract is verified.

#### Acceptance Criteria

1. THE test suite SHALL include integration tests for `GET /api/v1/admin/stats` verifying:
   - Returns correct counts when the test DB has known seed data.
   - Returns HTTP 403 when called by a non-admin user.
2. THE test suite SHALL include integration tests for `GET /api/v1/admin/vendors` verifying:
   - Returns paginated vendor list with correct `meta` fields.
   - `status` filter returns only vendors with that status.
   - `q` filter matches `business_name` and `contact_email`.
   - Returns HTTP 403 for non-admin callers.
3. THE test suite SHALL include integration tests for `PATCH /api/v1/admin/vendors/{id}/status`
   verifying:
   - Approving a `PENDING` vendor sets status to `ACTIVE`.
   - Rejecting a `PENDING` vendor sets status to `REJECTED`.
   - Returns HTTP 404 for a non-existent vendor ID.
   - Returns HTTP 403 for non-admin callers.
4. THE test suite SHALL include integration tests for `GET /api/v1/admin/users` verifying:
   - Returns paginated user list with correct `meta` fields.
   - `role` filter returns only users with that role.
   - Returns HTTP 403 for non-admin callers.
5. ALL tests SHALL use `httpx.AsyncClient` with `ASGITransport` — no real server required.
6. ALL tests SHALL use an isolated test database session — no production DB calls.
7. THE test suite SHALL achieve ≥ 80% line coverage on all three new route files.
