# Requirements Document

## Introduction

This spec covers the remaining gaps in the Vendor Marketplace module (004) of the Event-AI platform — an AI-powered event planning marketplace for Pakistan. The core vendor CRUD, approval workflow, search infrastructure, and customer inquiries are already built. This document specifies the seven targeted fixes needed to make the module production-ready: category assignment on vendor profiles, missing vendor self-service endpoints, a search count bug, a broken max_price filter, an approval status commit bug, structured error envelopes on vendor routes, and the missing `categories` field in `VendorRead`.

All work is confined to `packages/backend`. No new models or migrations are required — only schema, service, and route-layer changes.

---

## Glossary

- **Vendor**: A business or service provider registered on the marketplace, linked to a `User` account. Represented by the `Vendor` SQLModel.
- **Category**: An admin-curated classification tag (e.g., "Wedding Photography"). Represented by the `Category` SQLModel.
- **VendorCategoryLink**: The many-to-many join table (`vendor_categories`) linking `Vendor` to `Category`.
- **VendorCreate**: The Pydantic schema used when a vendor registers (`POST /api/v1/vendors/register`).
- **VendorUpdate**: The Pydantic schema used when a vendor updates their profile (`PUT /api/v1/vendors/profile/me`).
- **VendorRead**: The Pydantic response schema returned from all vendor endpoints.
- **ApprovalRequest**: A pending admin review record created on registration or critical profile edits.
- **VendorStatus**: Enum with values `PENDING`, `ACTIVE`, `SUSPENDED`, `REJECTED`.
- **ApprovalStatus**: Enum with values `PENDING`, `APPROVED`, `REJECTED`.
- **SearchService**: The service class in `search_service.py` responsible for building and executing vendor search queries.
- **VendorService**: The service class in `vendor_service.py` responsible for vendor CRUD operations.
- **ApprovalService**: The service class in `approval_service.py` responsible for processing admin approval decisions.
- **Error_Envelope**: The standardised JSON error response shape: `{"success": false, "error": {"code": "...", "message": "..."}}`.
- **Service**: A service offering listed by a vendor, with a `price_min` field, stored in the `services` table.
- **Soft-delete**: Setting `Vendor.status = SUSPENDED` rather than removing the row from the database.

---

## Requirements

### Requirement 1: Category Assignment on Vendor Registration and Profile Update

**User Story:** As a vendor, I want to assign myself to one or more categories when I register or update my profile, so that customers can discover me through category-based search and filtering.

#### Acceptance Criteria

1. WHEN a vendor submits `POST /api/v1/vendors/register` with a `category_ids` list, THE VendorService SHALL insert a `VendorCategoryLink` row for each provided category UUID.
2. WHEN a vendor submits `PUT /api/v1/vendors/profile/me` with a `category_ids` list, THE VendorService SHALL replace all existing `VendorCategoryLink` rows for that vendor with the new set.
3. WHERE `category_ids` is omitted from `VendorCreate` or `VendorUpdate`, THE VendorService SHALL treat the field as an empty list and make no changes to existing category links on update.
4. IF a provided `category_id` does not exist in the `categories` table, THEN THE VendorService SHALL raise a `ValueError` with a descriptive message identifying the invalid UUID.
5. THE VendorCreate schema SHALL include an optional field `category_ids: List[UUID] = []`.
6. THE VendorUpdate schema SHALL include an optional field `category_ids: Optional[List[UUID]] = None`.
7. WHEN `VendorService.create_vendor` is called, THE VendorService SHALL use `session.flush()` to obtain the vendor `id` before inserting `VendorCategoryLink` rows, within the same transaction.
8. WHEN `VendorService.update_vendor` is called with `category_ids` present, THE VendorService SHALL delete existing links and insert new ones before calling `session.commit()`.

---

### Requirement 2: Vendor Self-Service Read and Soft-Delete Endpoints

**User Story:** As a vendor, I want to read my own profile and deactivate my account, so that I have full self-service control over my marketplace presence without requiring admin intervention.

#### Acceptance Criteria

1. THE Vendor_Router SHALL expose `GET /api/v1/vendors/profile/me` protected by JWT authentication.
2. WHEN an authenticated vendor calls `GET /api/v1/vendors/profile/me`, THE Vendor_Router SHALL return the vendor's full profile as a `VendorRead` response with HTTP 200.
3. IF no vendor profile exists for the authenticated user on `GET /api/v1/vendors/profile/me`, THEN THE Vendor_Router SHALL return HTTP 404 with Error_Envelope `{"code": "NOT_FOUND_VENDOR_PROFILE", "message": "Vendor profile not found."}`.
4. THE Vendor_Router SHALL expose `DELETE /api/v1/vendors/profile/me` protected by JWT authentication.
5. WHEN an authenticated vendor calls `DELETE /api/v1/vendors/profile/me`, THE Vendor_Router SHALL set `vendor.status = SUSPENDED` and commit the change (soft-delete).
6. WHEN the soft-delete succeeds, THE Vendor_Router SHALL return HTTP 200 with `{"success": true, "data": {"message": "Vendor profile deactivated."}}`.
7. IF no vendor profile exists for the authenticated user on `DELETE /api/v1/vendors/profile/me`, THEN THE Vendor_Router SHALL return HTTP 404 with Error_Envelope `{"code": "NOT_FOUND_VENDOR_PROFILE", "message": "Vendor profile not found."}`.
8. WHILE a vendor's status is `SUSPENDED`, THE SearchService SHALL exclude that vendor from all public search results.

---

### Requirement 3: Search Total Count Correctness

**User Story:** As a customer, I want pagination metadata to reflect the true total number of matching vendors, so that I can navigate search results accurately.

#### Acceptance Criteria

1. THE SearchService SHALL execute a dedicated `count_stmt` against the database to obtain the total matching vendor count, independent of the pagination `limit` and `offset`.
2. THE SearchService SHALL apply identical filter logic to both `base_stmt` and `count_stmt`, including text search, category, location, rating, and price filters.
3. WHEN a text search query `q` is provided, THE SearchService SHALL combine the trigram filter and the ILIKE filter using `OR` logic (a vendor matches if either condition is true), and apply this combined filter to both `base_stmt` and `count_stmt`.
4. THE VendorService `search_vendors` method SHALL be removed or replaced so that total count is sourced from the `SearchService.search_vendors` return value, not from `len(items)`.
5. WHEN the search returns zero results, THE SearchService SHALL return `([], 0)` with total count of `0`.
6. FOR ALL valid search queries with pagination, the returned `total` SHALL equal the count of vendors matching the filters without any `LIMIT` or `OFFSET` applied.

---

### Requirement 4: max_price Filter Implementation

**User Story:** As a customer, I want to filter vendors by maximum price, so that I can find vendors whose services fit my budget.

#### Acceptance Criteria

1. WHEN `max_price` is provided in a search query, THE SearchService SHALL join the `services` table to the vendor query.
2. WHEN `max_price` is provided, THE SearchService SHALL filter to vendors that have at least one `Service` row where `Service.price_min <= max_price`.
3. THE SearchService SHALL implement the `max_price` filter using a subquery or join, replacing the current placeholder `Vendor.rating >= 0` filter entirely.
4. WHEN `max_price` is `None`, THE SearchService SHALL apply no price-based filter.
5. THE `max_price` filter SHALL be applied consistently to both `base_stmt` and `count_stmt`.

---

### Requirement 5: Approval Process Vendor Status Commit

**User Story:** As an admin, I want approval decisions to reliably update vendor status in the database, so that approved vendors become active and rejected vendors are correctly marked.

#### Acceptance Criteria

1. WHEN `ApprovalService.process_approval` is called with `status = APPROVED`, THE ApprovalService SHALL set `vendor.status = VendorStatus.ACTIVE` before calling `session.commit()`.
2. WHEN `ApprovalService.process_approval` is called with `status = REJECTED`, THE ApprovalService SHALL set `vendor.status = VendorStatus.REJECTED` before calling `session.commit()`.
3. THE ApprovalService SHALL call `event_bus.emit` only after `session.commit()` has completed successfully, using a new session or background task to avoid operating on a closed session.
4. IF `vendor` is `None` for the given `approval.vendor_id`, THEN THE ApprovalService SHALL still update the `ApprovalRequest` record and commit, logging a warning without raising an unhandled exception.
5. WHEN the approval commit succeeds, THE ApprovalService SHALL call `session.refresh(approval)` to return the updated record.
6. WHEN `status = APPROVED`, THE ApprovalService SHALL emit the `vendor.approved` domain event with `vendor_id`, `business_name`, and `approved_by` fields.
7. WHEN `status = REJECTED`, THE ApprovalService SHALL emit the `vendor.rejected` domain event with `vendor_id`, `business_name`, `rejected_by`, and `reason` fields.

---

### Requirement 6: Structured Error Envelopes on Vendor Routes

**User Story:** As an API consumer, I want all vendor route errors to return a consistent structured envelope, so that my client code can handle errors uniformly without parsing free-form strings.

#### Acceptance Criteria

1. THE Vendor_Router SHALL return all error responses using the Error_Envelope format: `{"success": false, "error": {"code": "...", "message": "..."}}`.
2. WHEN vendor registration fails due to a duplicate business name, THE Vendor_Router SHALL return HTTP 409 with `{"code": "CONFLICT_DUPLICATE_VENDOR", "message": "A vendor with this business name already exists in this location."}`.
3. WHEN vendor registration fails due to the authenticated user already having a vendor profile, THE Vendor_Router SHALL return HTTP 409 with `{"code": "CONFLICT_VENDOR_EXISTS", "message": "A vendor profile already exists for this account."}`.
4. WHEN a vendor profile is not found on any vendor route, THE Vendor_Router SHALL return HTTP 404 with `{"code": "NOT_FOUND_VENDOR_PROFILE", "message": "Vendor profile not found."}`.
5. WHEN an unexpected server error occurs on any vendor route, THE Vendor_Router SHALL return HTTP 500 with `{"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."}` and log the full exception via structlog.
6. THE Public_Vendor_Router SHALL return all error responses using the same Error_Envelope format.
7. WHEN a category UUID provided during registration or update does not exist, THE Vendor_Router SHALL return HTTP 422 with `{"code": "VALIDATION_INVALID_CATEGORY", "message": "One or more category IDs are invalid."}`.

---

### Requirement 7: VendorRead Includes Categories

**User Story:** As an API consumer, I want the vendor profile response to include the vendor's assigned categories, so that I can display category information without making additional requests.

#### Acceptance Criteria

1. THE VendorRead schema SHALL include a field `categories: List[CategoryRead] = []`.
2. WHEN `VendorService.get_by_id` returns a vendor, THE VendorRead serialiser SHALL populate `categories` from the eagerly loaded `Vendor.categories` relationship.
3. WHEN a vendor has no assigned categories, THE VendorRead serialiser SHALL return `categories` as an empty list `[]`.
4. THE CategoryRead schema used in VendorRead SHALL include at minimum: `id`, `name`, `description`, `icon_url`, `display_order`, and `is_active`.
5. WHEN `GET /api/v1/vendors/profile/me` is called, THE Vendor_Router SHALL use `selectinload(Vendor.categories)` to avoid N+1 queries.
6. WHEN `POST /api/v1/vendors/register` returns a `VendorRead`, THE Vendor_Router SHALL include the newly linked categories in the `categories` field.
7. WHEN `PUT /api/v1/vendors/profile/me` returns a `VendorRead`, THE Vendor_Router SHALL include the updated categories in the `categories` field.
