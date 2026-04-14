# Tasks: Phase 2 — Vendor Marketplace Gaps

- [x] 1. Fix schemas
  - [x] 1.1 Add `category_ids` to `VendorCreate` and `VendorUpdate` in `src/schemas/vendor.py`
  - [x] 1.2 Add `categories: List[CategoryRead]` to `VendorRead` in `src/schemas/vendor.py`
  - [x] 1.3 Verify `CategoryRead` schema has all required fields in `src/schemas/category.py`

- [x] 2. Fix vendor_service.py
  - [x] 2.1 Add category link insertion in `create_vendor`
  - [x] 2.2 Add category link replacement in `update_vendor`

- [x] 3. Fix search_service.py
  - [x] 3.1 Fix count_stmt to use same OR filter as base_stmt for text search
  - [x] 3.2 Replace max_price placeholder with real subquery filter

- [x] 4. Fix approval_service.py
  - [x] 4.1 Set vendor.status before session.commit() for APPROVED and REJECTED cases
  - [x] 4.2 Move event_bus.emit after commit

- [x] 5. Fix vendors.py routes
  - [x] 5.1 Add `GET /profile/me` endpoint
  - [x] 5.2 Add `DELETE /profile/me` soft-delete endpoint
  - [x] 5.3 Wrap all HTTPException details as structured error dicts

- [x] 6. Fix public_vendors.py error envelopes
