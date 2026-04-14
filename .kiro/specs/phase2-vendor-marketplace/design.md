# Design Document: Phase 2 — Vendor Marketplace Gaps

## Overview

Seven targeted fixes to `packages/backend`. No new models or migrations needed.

---

## Changes by File

### 1. `src/schemas/vendor.py`
- Add `category_ids: List[UUID] = []` to `VendorCreate`
- Add `category_ids: Optional[List[UUID]] = None` to `VendorUpdate`
- Add `categories: List[CategoryRead] = []` to `VendorRead`

### 2. `src/schemas/category.py`
- Ensure `CategoryRead` has `id`, `name`, `description`, `icon_url`, `display_order`, `is_active`

### 3. `src/services/vendor_service.py`
- `create_vendor`: after `session.flush()`, validate category_ids exist, insert `VendorCategoryLink` rows
- `update_vendor`: if `category_ids` in update_data, delete existing links, insert new ones
- `get_by_id`: already uses `selectinload(Vendor.categories)` — keep
- Remove `search_vendors` method (delegate to `search_service`)

### 4. `src/services/search_service.py`
- Fix `count_stmt` to use same combined OR filter as `base_stmt` for text search
- Replace `max_price` placeholder with real subquery: `Vendor.id IN (SELECT vendor_id FROM services WHERE price_min <= max_price)`
- Ensure `count_stmt` applies all filters identically to `base_stmt`

### 5. `src/services/approval_service.py`
- `process_approval`: set `vendor.status` before `session.commit()`
- APPROVED → `VendorStatus.ACTIVE`; REJECTED → `VendorStatus.REJECTED`
- Move `event_bus.emit` calls after commit (fire-and-forget, don't await in same session)

### 6. `src/api/v1/vendors.py`
- Add `GET /profile/me` — fetch vendor by `user_id`, return `VendorRead` with categories
- Add `DELETE /profile/me` — soft-delete (set `status=SUSPENDED`)
- Wrap all `HTTPException` details as structured dicts with `code` + `message`
- Catch `ValueError` from service layer and return 422 with `VALIDATION_INVALID_CATEGORY`

### 7. `src/api/v1/public_vendors.py`
- Wrap error responses in Error_Envelope format

---

## Error Code Map

| Scenario | HTTP | Code |
|---|---|---|
| Duplicate vendor (same name+location) | 409 | `CONFLICT_DUPLICATE_VENDOR` |
| User already has vendor profile | 409 | `CONFLICT_VENDOR_EXISTS` |
| Vendor profile not found | 404 | `NOT_FOUND_VENDOR_PROFILE` |
| Invalid category UUID | 422 | `VALIDATION_INVALID_CATEGORY` |
| Unexpected server error | 500 | `INTERNAL_SERVER_ERROR` |
