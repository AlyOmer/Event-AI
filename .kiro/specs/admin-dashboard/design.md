# Design Document

## Overview

Module 009 completes the Event-AI admin portal by wiring three missing backend API routes and
finishing two incomplete frontend pages. The design is deliberately minimal — the UI already
exists, the auth infrastructure already exists, and the database models already exist. The work
is primarily additive: new FastAPI route files, new Pydantic schemas, and frontend wiring.

---

## Architecture

### Component Interaction

```
packages/admin (Next.js)
  └── src/lib/api.ts (axios + NextAuth JWT)
        ├── GET  /api/v1/admin/stats          → AdminStatsRouter
        ├── GET  /api/v1/admin/vendors        → AdminVendorsRouter
        ├── PATCH /api/v1/admin/vendors/{id}/status → AdminVendorsRouter
        └── GET  /api/v1/admin/users          → AdminUsersRouter

packages/backend (FastAPI)
  └── src/api/v1/admin/
        ├── stats.py      (NEW)
        ├── vendors.py    (NEW)
        ├── users.py      (NEW)
        ├── approvals.py  (existing)
        └── categories.py (existing)
```

All new routes use the existing `require_admin` dependency and the existing `get_session`
dependency. No new middleware or auth logic is introduced.

---

## Backend Design

### New Files

#### `src/api/v1/admin/stats.py`

Single route: `GET /` (mounted at `/api/v1/admin/stats`).

Uses a single SQLAlchemy query with `func.count` and `func.sum` to compute all aggregates in one
round-trip:

```python
from sqlalchemy import func, select, case
from src.models.vendor import Vendor, VendorStatus
from src.models.user import User
from src.models.booking import Booking, BookingStatus

async def get_platform_stats(session: AsyncSession) -> dict:
    result = await session.execute(
        select(
            func.count(User.id).filter(User.is_active == True).label("total_users"),
            func.count(Vendor.id).filter(Vendor.status == VendorStatus.ACTIVE).label("active_vendors"),
            func.count(Vendor.id).filter(Vendor.status == VendorStatus.PENDING).label("pending_vendors"),
            func.count(Booking.id).label("total_bookings"),
            func.count(Booking.id).filter(Booking.status == BookingStatus.confirmed).label("confirmed_bookings"),
            func.count(Booking.id).filter(Booking.status == BookingStatus.pending).label("pending_bookings"),
            func.coalesce(
                func.sum(Booking.total_price).filter(
                    Booking.status.in_([BookingStatus.confirmed, BookingStatus.completed])
                ), 0.0
            ).label("total_revenue"),
        ).select_from(User).outerjoin(Vendor, Vendor.id == None).outerjoin(Booking, Booking.id == None)
    )
    # Note: use separate scalar subqueries for correctness across tables
```

> **Implementation note:** Because `User`, `Vendor`, and `Booking` are independent tables with no
> natural join key, the stats query uses three separate scalar subqueries rather than a single
> cross-join. This avoids Cartesian product inflation.

Correct pattern:

```python
stats = await session.execute(
    select(
        select(func.count()).where(User.is_active == True).scalar_subquery().label("total_users"),
        select(func.count()).where(Vendor.status == VendorStatus.ACTIVE).scalar_subquery().label("active_vendors"),
        select(func.count()).where(Vendor.status == VendorStatus.PENDING).scalar_subquery().label("pending_vendors"),
        select(func.count()).select_from(Booking).scalar_subquery().label("total_bookings"),
        select(func.count()).where(Booking.status == BookingStatus.confirmed).scalar_subquery().label("confirmed_bookings"),
        select(func.count()).where(Booking.status == BookingStatus.pending).scalar_subquery().label("pending_bookings"),
        select(func.coalesce(func.sum(Booking.total_price), 0.0))
            .where(Booking.status.in_([BookingStatus.confirmed, BookingStatus.completed]))
            .scalar_subquery().label("total_revenue"),
    )
)
row = stats.one()
```

#### `src/api/v1/admin/vendors.py`

Two routes:
- `GET /` — paginated vendor list
- `PATCH /{vendor_id}/status` — status update

**Vendor list query pattern:**

```python
stmt = select(Vendor).order_by(Vendor.created_at.desc())
if status_filter:
    stmt = stmt.where(Vendor.status == status_filter)
if q:
    stmt = stmt.where(
        or_(
            Vendor.business_name.ilike(f"%{q}%"),
            Vendor.contact_email.ilike(f"%{q}%"),
        )
    )
# Count total for pagination meta
count_stmt = select(func.count()).select_from(stmt.subquery())
total = (await session.execute(count_stmt)).scalar_one()
# Paginate
stmt = stmt.offset((page - 1) * limit).limit(limit)
vendors = (await session.execute(stmt)).scalars().all()
```

**Status update + domain event:**

```python
vendor.status = new_status
await session.commit()
await session.refresh(vendor)

event_type_map = {
    VendorStatus.ACTIVE: "vendor.approved",
    VendorStatus.REJECTED: "vendor.rejected",
    VendorStatus.SUSPENDED: "vendor.suspended",
}
event_bus.emit(event_type_map[new_status], {"vendor_id": str(vendor.id), "reason": reason})
```

#### `src/api/v1/admin/users.py`

Single route: `GET /` — paginated user list with optional vendor join.

```python
stmt = (
    select(User)
    .options(selectinload(User.vendor))  # requires User.vendor relationship
    .order_by(User.created_at.desc())
)
if role_filter:
    stmt = stmt.where(User.role == role_filter)
if q:
    stmt = stmt.where(
        or_(
            User.email.ilike(f"%{q}%"),
            User.first_name.ilike(f"%{q}%"),
            User.last_name.ilike(f"%{q}%"),
        )
    )
```

> **Note:** The `User` model currently has no `vendor` relationship. A `vendor` back-reference
> must be added to `User` (or a separate join used). The simplest approach is a LEFT OUTER JOIN
> on `vendors.user_id = users.id` rather than modifying the model relationship.

### New Pydantic Schemas

#### `src/schemas/admin.py` (new file)

```python
class AdminVendorRead(SQLModel):
    id: uuid.UUID
    business_name: str
    status: VendorStatus
    city: Optional[str]
    region: Optional[str]
    rating: float
    total_reviews: int
    created_at: datetime
    owner_email: str  # maps to vendor.contact_email

class AdminVendorStatusUpdate(SQLModel):
    status: VendorStatus
    reason: Optional[str] = None

class AdminUserVendorSummary(SQLModel):
    id: uuid.UUID
    business_name: str
    status: VendorStatus

class AdminUserRead(SQLModel):
    id: uuid.UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    vendor: Optional[AdminUserVendorSummary] = None

class AdminStatsResponse(SQLModel):
    totalUsers: int
    activeVendors: int
    pendingVendors: int
    totalBookings: int
    confirmedBookings: int
    pendingBookings: int
    totalRevenue: float
```

### `main.py` additions

```python
from src.api.v1.admin.stats import router as admin_stats_router
from src.api.v1.admin.vendors import router as admin_vendors_router
from src.api.v1.admin.users import router as admin_users_router

app.include_router(admin_stats_router,   prefix="/api/v1/admin/stats")
app.include_router(admin_vendors_router, prefix="/api/v1/admin/vendors")
app.include_router(admin_users_router,   prefix="/api/v1/admin/users")
```

---

## Frontend Design

### `packages/admin/src/lib/api.ts` additions

```typescript
// Stats
export const getStats = async () => {
    const response = await api.get("/admin/stats");
    return response.data?.data || response.data;
};

// Vendors (updated — was calling /admin/vendors already, now confirmed correct)
export const getVendors = async (params?: { page?: number; limit?: number; status?: string; q?: string }) => {
    const response = await api.get("/admin/vendors", { params });
    return response.data?.data || response.data;
};

export const updateVendorStatus = async (id: string, status: string, reason?: string) => {
    const response = await api.patch(`/admin/vendors/${id}/status`, { status, reason });
    return response.data;
};

// Users (updated — was calling /admin/users already, now confirmed correct)
export const getUsers = async (params?: { page?: number; limit?: number; role?: string; q?: string }) => {
    const response = await api.get("/admin/users", { params });
    return response.data?.data || response.data;
};

// Categories (for Settings page)
export const getCategories = async () => {
    const response = await api.get("/admin/categories");
    return response.data?.data || response.data;
};

export const createCategory = async (data: { name: string; slug: string; description?: string }) => {
    const response = await api.post("/admin/categories", data);
    return response.data;
};

export const deleteCategory = async (id: string) => {
    await api.delete(`/admin/categories/${id}`);
};
```

### Vendors Page (`packages/admin/src/app/vendors/page.tsx`)

The existing page already has the correct structure. Changes needed:
- Add `status` filter dropdown (currently only has search)
- Pass `{ page, limit, status, q }` as query params to `getVendors`
- Add `owner_email` column to the table
- Add debounce (300ms) to the search input using `useCallback` + `setTimeout`

### Users Page (`packages/admin/src/app/users/page.tsx`)

The existing page has a basic table. Changes needed:
- Add `role` filter dropdown
- Add search input with 300ms debounce
- Add pagination controls
- Pass `{ page, limit, role, q }` as query params to `getUsers`

### Settings Page (`packages/admin/src/app/settings/page.tsx`)

Replace the stub with three sections:
1. **Platform Info** — static display of API URL, admin email from `useSession`, package version
2. **Categories** — list from `GET /admin/categories` with add/delete actions
3. **Danger Zone** — placeholder section (no destructive actions in this module)

### Dashboard Analytics Panel (`packages/admin/src/app/page.tsx`)

Replace the placeholder `<div>` in the Overview card with a booking status breakdown:

```tsx
// Derived from stats data — no extra API call
const breakdown = [
    { label: "Pending",   count: stats.pendingBookings,   color: "bg-amber-400" },
    { label: "Confirmed", count: stats.confirmedBookings, color: "bg-emerald-400" },
    { label: "Other",     count: stats.totalBookings - stats.pendingBookings - stats.confirmedBookings, color: "bg-blue-400" },
];
```

Each row renders a label, count, and a `<div>` progress bar whose `width` is
`(count / totalBookings * 100).toFixed(1) + "%"`.

---

## Data Flow

```
Admin opens /vendors
  → React Query calls getVendors({ page: 1, limit: 20 })
  → GET /api/v1/admin/vendors?page=1&limit=20
  → require_admin validates JWT role
  → AdminVendorsRouter queries DB with pagination
  → Returns { success, data: [...], meta: { total, page, limit, pages } }
  → Vendors page renders table

Admin clicks "Approve" on a PENDING vendor
  → updateVendorStatus(id, "ACTIVE")
  → PATCH /api/v1/admin/vendors/{id}/status { status: "ACTIVE" }
  → Backend sets vendor.status = ACTIVE, commits, emits vendor.approved event
  → Returns updated AdminVendorRead
  → React Query invalidates ["vendors"] and ["stats"]
  → Both queries refetch automatically
```

---

## Error Handling

| Scenario | Backend Response | Frontend Behaviour |
|---|---|---|
| Non-admin calls any admin route | HTTP 403 `AUTH_FORBIDDEN` | NextAuth session expired → auto sign-out |
| Vendor not found on status update | HTTP 404 `NOT_FOUND_VENDOR` | Toast: "Vendor not found" |
| Delete category with vendors | HTTP 409 `CONFLICT` | Toast: backend error message |
| Stats endpoint DB error | HTTP 500 `INTERNAL_ERROR` | Dashboard error banner |
| Network timeout | Axios error | React Query retry (3 attempts) |

---

## Testing Strategy

All backend tests use `httpx.AsyncClient` with `ASGITransport` and an isolated async test session.
No real database or server is required.

**Test fixtures needed:**
- `admin_user` — a `User` with `role="admin"` inserted via test session
- `regular_user` — a `User` with `role="user"`
- `pending_vendor` — a `Vendor` with `status=PENDING`
- `active_vendor` — a `Vendor` with `status=ACTIVE`
- `admin_token` — JWT for `admin_user` generated via `AuthService.create_access_token`
- `user_token` — JWT for `regular_user`

**Test file locations:**
- `packages/backend/tests/test_admin_stats.py`
- `packages/backend/tests/test_admin_vendors.py`
- `packages/backend/tests/test_admin_users.py`
