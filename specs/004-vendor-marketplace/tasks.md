# Tasks: Vendor Marketplace

**Input**: Design documents from `/specs/004-vendor-marketplace/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md
**Tests**: Not requested in spec. Tests are OPTIONAL - only included if explicitly requested.
**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2], [US3])
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `packages/backend/src/`
- **Database**: `packages/backend/prisma/` or `packages/backend/src/db/migrations/`
- Paths below reflect the monorepo structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for vendor marketplace

- [ ] T001 Review existing database schema and migrations to understand current state
- [ ] T002 Create database migration(s) for vendor marketplace schema changes in packages/backend/src/db/migrations/
- [ ] T003 [P] Add environment variables for CDN (R2/S3) configuration in packages/backend/.env.example

**Checkpoint**: Schema changes planned, env configured

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Model (from spec.md entities)

- [ ] T004 [P] Create Category model (if not exists) with: id, name (unique), description, icon, displayOrder, active fields
- [ ] T005 [P] Create Category-Vendor many-to-many relationship via join table (vendor_categories or vendorCategory)
- [ ] T006 [P] Create ApprovalRequest model with: id, vendorId, type (new_registration, profile_edit_approval), status (pending, approved, rejected, more_info), submittedDate, reviewedDate, reviewedBy, decisionNotes, dataSnapshot
- [ ] T007 [P] Add marketplace-specific fields to Vendor model (if not present): keywords (String[]), pricingMin (Decimal), pricingMax (Decimal), rating (Decimal), totalReviews (Int), enhanced serviceAreas (JSON with geospatial data)
- [ ] T008 [P] Create VendorProfileVersion model for audit trail (optional but recommended): id, vendorId, snapshot, changeReason, changedBy, timestamp
- [ ] T009 [P] Create CustomerInquiry model: id, vendorId, customerName, customerEmail, customerPhone, message, preferredDate, status (new, contacted, quoted, converted, declined)

### Database Indexes & Extensions

- [ ] T010 [P] Enable PostgreSQL extension pg_trgm in migration (CREATE EXTENSION IF NOT EXISTS pg_trgm)
- [ ] T011 [P] Add full-text search indexes: GIN on to_tsvector('english', vendors.name), GIN on to_tsvector('english', vendors.description)
- [ ] T012 [P] Add trigram similarity indexes: GIN on vendors.name gin_trgm_ops, GIN on vendors.description gin_trgm_ops
- [ ] T013 [P] Add indexes for common filters: categories (id, name), vendors (status, tier, rating), vendor_categories (vendorId, categoryId), approval_requests (status, submittedDate)
- [ ] T014 [P] Add foreign key indexes: vendorId on services, documents, auditLogs, approval_requests, customer_inquiries

### Search Service Foundation

- [ ] T015 [P] Implement search.service.ts in packages/backend/src/services/search.service.ts with:
  - Full-text search using to_tsquery with weighting (name > description)
  - Trigram similarity fallback for partial matches
  - Combined ranking: full-text rank + trigram similarity + rating
  - Filter by: categoryIds, location (serviceAreas), status = 'ACTIVE', minRating, price range

**Checkpoint**: Foundation ready - database schema complete, indexes created, search service implemented

---

## Phase 3: User Story 1 - Vendor Self-Registration and Profile Management (Priority: P1) 🎯 MVP

**Goal**: Vendors can create and manage their own profiles with business info, services, contact details, and portfolio images

**Independent Test**: Vendor signs up, creates complete profile with services, contact info, and portfolio, then edits details. Vendor accesses/modifies own data without admin intervention.

### Tests for User Story 1 (OPTIONAL - only if tests requested)

> **NOTE**: Not requested in spec. Skip unless TDD approach chosen.

### Implementation for User Story 1

**Vendor Profile CRUD**:

- [ ] T016 [P] [US1] Update vendor validation schema in packages/backend/src/schemas/vendor.schema.ts (or index.ts) to include: serviceAreas (array with city, region, radius), address fields, enhanced required fields, length limits (description max 2000), URL validation
- [ ] T017 [US1] Ensure vendor profile update endpoint (PUT /api/v1/vendor/profile) in packages/backend/src/routes/vendor.routes.ts handles all marketplace fields correctly
- [ ] T018 [US1] Implement or verify portfolio image management endpoints:
  - POST /api/v1/vendor/profile/portfolio (adds image after upload)
  - DELETE /api/v1/vendor/profile/portfolio/:id
  - Ensure max 10 images limit enforced, file types JPG/PNG validated
- [ ] T019 [P] [US1] Verify CDN service in packages/backend/src/services/cdn.service.ts generates pre-signed upload URLs (PUT) and returns file URL (GET)
- [ ] T020 [US1] Implement soft delete for vendor profiles: update status to 'DEACTIVATED' (not hard delete) in DELETE /api/v1/vendor/profile
- [ ] T021 [US1] Add data validation: required fields (name, contactEmail), email format, phone format, URL format for website, max lengths (name 255, description 2000), prohibit profanity (basic filter)
- [ ] T022 [US1] Add audit logging for all vendor profile changes using existing AuditLog model (already in route, verify completeness)

**Service Management** (part of vendor profile):

- [ ] T023 [P] [US1] Review Service model in schema to ensure it includes: name, description, category, capacity, leadTime, requirements, inclusions, exclusions, images (String[]), featuredImage, pricing
- [ ] T024 [US1] Implement service CRUD endpoints (POST/GET/PUT/DELETE /api/v1/vendor/services) in packages/backend/src/routes/services.routes.ts
- [ ] T025 [US1] Add service-specific validation: capacity (Int), leadTime (Int hours/days), requirements (text), inclusions/exclusions (String[]), price (Decimal)

**Vendor Registration Flow** (self-service signup):

- [ ] T026 [US1] Implement vendor registration endpoint (POST /api/v1/vendor/register) that:
  - Creates vendor record with status = 'PENDING' (if approval workflow enabled) or 'ACTIVE' (if auto-approve)
  - Creates associated VendorUser linking to auth user (userId from JWT)
  - Validates unique business name within location (city/region)
  - Creates initial ApprovalRequest if approval required
- [ ] T027 [US1] Handle duplicate email detection: return 409 with helpful message if contactEmail already exists
- [ ] T028 [US1] Implement vendor profile retrieval endpoint (GET /api/vendor/:id) for public viewing (only returns ACTIVE vendors)

**Checkpoint**: User Story 1 complete - vendor can register, create/update profile with services and portfolio, soft-delete, all data validated and audited

---

## Phase 4: User Story 2 - Category Management and Curation (Priority: P2)

**Goal**: Administrators define and manage vendor categories for consistent classification

**Independent Test**: Admin creates/edits/deactivates categories, assigns vendors to categories. Changes propagate to vendor profiles and search filters.

### Implementation for User Story 2

**Category CRUD (Admin Only)**:

- [ ] T029 [P] [US2] Create category validation schema in packages/backend/src/schemas/category.schema.ts (name required, unique; description; icon URL; displayOrder Int; active Boolean)
- [ ] T030 [US2] Implement admin category routes in packages/backend/src/routes/admin.routes.ts:
  - GET /api/v1/admin/categories (list all with filters, sorted by displayOrder)
  - POST /api/v1/admin/categories (create)
  - GET /api/v1/admin/categories/:id
  - PUT /api/v1/admin/categories/:id
  - DELETE /api/v1/admin/categories/:id (soft-deactivate: set active=false; prevent hard delete if vendors assigned)
- [ ] T031 [US2] Add admin authorization to category routes: requireRole('admin') or requirePermission('category:write')
- [ ] T032 [US2] Prevent deletion of categories with vendor assignments: check vendor_categories count, return 409 Conflict with message "Cannot delete category with assigned vendors. Deactivate instead."
- [ ] T033 [US2] Ensure category read operations only return active categories to vendors, but admin sees all

**Vendor Category Assignment**:

- [ ] T034 [US1/US2] Update vendor profile update endpoint (PUT /api/v1/vendor/profile) to accept categoryIds array and manage join table entries
- [ ] T035 [US2] Validate that all categoryIds reference existing active categories before assignment (return 400 if any inactive/missing)
- [ ] T036 [US2] Add endpoint for vendors to list available categories: GET /api/v1/categories (public, only active categories, sorted by displayOrder)

**Checkpoint**: Categories fully managed by admin, vendors can select from active categories, changes visible in search filters

---

## Phase 5: User Story 3 - Vendor Search and Discovery (Priority: P2)

**Goal**: Customers search and filter vendors by category, location, keywords with relevance ranking

**Independent Test**: Search with keywords, apply category/location filters, sort by rating/price. Results paginated, relevant, under 500ms.

### Implementation for User Story 3

**Enhanced Public Vendor Search**:

- [ ] T037 [P] [US3] Update public vendor list endpoint (GET /api/v1/public/vendors) to use new search algorithm in packages/backend/src/routes/public-vendors.routes.ts:
  - Accept query params: q (keywords), category (comma-separated ids), city, region, minRating, maxPrice, sort (relevance, rating, price_asc, price_desc), page, limit
  - Use search.service.ts functions to build query
- [ ] T038 [US3] Implement full-text search: convert keywords to tsquery, rank by ts_rank with weight (name^2.0, description^1.0)
- [ ] T039 [US3] Add trigram similarity: compute similarity(name, query), similarity(description, query), threshold > 0.1
- [ ] T040 [US3] Combine rankings: final_score = (fulltext_rank * 0.6 + trigram_sim * 0.3 + rating * 0.1)
- [ ] T041 [US3] Filter vendors by: status = 'ACTIVE', category IN (if provided), serviceAreas contains location (JSONB containment), pricingMin/Max within range, rating >= minRating
- [ ] T042 [US3] Add pagination: limit default 20, max 100, return total count and page metadata
- [ ] T043 [US3] Add query length validation: if q length > 200, return 400; sanitize to prevent SQL injection (use parameterized queries only)

**Performance Optimization**:

- [ ] T044 [US3] Verify database indexes exist and are used: run EXPLAIN ANALYZE on search queries, adjust if needed
- [ ] T045 [US3] Add query performance logging: log queries taking > 500ms with parameters to aid optimization

**Search Results Quality**:

- [ ] T046 [US3] Ensure search returns vendor basic info: id, name, description (truncated), category names, location (city), rating, pricing range, logoUrl
- [ ] T047 [US3] Handle no results gracefully: return empty array with message "No vendors found matching your criteria. Try broader terms."

**Checkpoint**: Search functional with full-text + trigram, filters work, pagination, performance acceptable

---

## Phase 6: User Story 4 - Vendor Approval Workflow (Priority: P3)

**Goal**: Admins review and approve vendor registrations and significant profile changes

**Independent Test**: New vendor registration or significant edit enters approval queue. Admin approves/rejects/requests info. Vendor notified, status updates accordingly.

### Implementation for User Story 4

**Approval Request Creation**:

- [ ] T048 [US1/US4] Modify vendor registration (POST /api/v1/vendor/register) to:
  - Create vendor with status = 'PENDING'
  - Create ApprovalRequest with type='new_registration', status='pending', dataSnapshot of vendor info
- [ ] T049 [US1/US4] Modify vendor profile update endpoint (PUT /api/v1/vendor/profile) to detect critical field changes:
  - Critical: business name, contactEmail, primary category (first in categoryIds), business type
  - If critical fields changed, set vendor.status = 'PENDING', create ApprovalRequest with type='profile_edit_approval', dataSnapshot of changes
  - Non-critical changes (description, portfolio, services, serviceAreas) proceed without approval
- [ ] T050 [US4] Ensure public vendor routes (GET /api/v1/public/vendors, GET /api/v1/public/vendors/:id) filter only vendors with status = 'ACTIVE' (already should; verify)

**Admin Approval Endpoints**:

- [ ] T051 [US4] Implement admin approval routes in packages/backend/src/routes/admin.routes.ts:
  - GET /api/v1/admin/approvals?status=pending&page=1&limit=20 (list with filters, include vendor basic info)
  - GET /api/v1/admin/approvals/:id (show full snapshot, history)
  - POST /api/v1/admin/approvals/:id/approve (set ApprovalRequest.status='approved', log admin action)
  - POST /api/v1/admin/approvals/:id/reject (set status='rejected', require reason in body)
  - POST /api/v1/admin/approvals/:id/request-info (set status='pending', notify vendor)
- [ ] T052 [US4] Add admin authorization: requireRole('admin') or requirePermission('vendor:approve')
- [ ] T053 [US4] Implement approval logic in endpoint handlers:
  - On approve: update vendor.status = 'ACTIVE', set vendor.approvedBy = admin.userId, emit event
  - On reject: vendor.status remains 'PENDING', vendor can resubmit by editing profile
  - On request-info: vendor.status = 'PENDING', send message via notification service

**Notifications**:

- [ ] T054 [US4] Emit domain events via eventBus.service.ts:
  - vendor.approved with payload { vendorId, vendorName, adminId }
  - vendor.rejected with payload { vendorId, vendorName, reason, adminId }
  - vendor.approval-requested with payload { vendorId, type }
- [ ] T055 [US4] Extend notification service in packages/backend/src/services/notification.service.ts to handle these events:
  - Send in-app notification to vendor (create Notification record)
  - Send email notification to vendor using email.service.ts (templates for approved/rejected)
- [ ] T056 [US4] Create email templates in packages/backend/src/templates/email.templates.ts:
  - vendor-approval-approved.html/text
  - vendor-approval-rejected.html/text with reason
  - vendor-approval-requested.html/text (for request-info)

**Audit Logging**:

- [ ] T057 [US4] Ensure all admin approval actions are logged to AuditLog with:
  - entityType='vendor', entityId=vendor.id
  - action='approval_approved'/'approval_rejected'/'approval_requested'
  - changes include: fromStatus, toStatus, notes, approvalRequestId
- [ ] T058 [US4] Add admin action logging in admin approval endpoints before state changes

**Automatic Approval for Minor Edits**:

- [ ] T059 [US4] Define critical vs non-critical fields in a constant map (vendor.schema.ts or service)
- [ ] T060 [US4] Update vendor update logic to bypass approval for non-critical changes (description, portfolio, serviceAreas, services)

**Checkpoint**: Approval workflow complete: queue, actions, notifications, audit, auto-approval rules

---

## Phase 7: Integration & Cross-Cutting Concerns

**Purpose**: Polish, security hardening, and integration across all stories

### Rate Limiting

- [ ] T061 [P] Apply rate limiting to sensitive endpoints in route definitions:
  - Vendor profile update: 10 requests/hour (vendorRateLimit)
  - Portfolio upload: 50 requests/hour (uploadRateLimit)
  - Public vendor search: 100 requests/minute (publicApiRateLimit)
  - Admin approval routes: 60 requests/minute (adminRateLimit) + require admin role
- [ ] T062 [P] Verify rate limit configuration exists in packages/backend/src/middleware/rateLimit.middleware.ts and reuse

### Search Optimization

- [ ] T063 [P] Confirm pg_trgm extension creation in migration (T010) executed on database
- [ ] T064 [P] Refresh database statistics: ANALYZE vendors, categories, services, vendor_categories
- [ ] T065 [P] Add slow query logging for search endpoint (>500ms) using existing logger

### Authorization & Security

- [ ] T066 [P] Verify all vendor profile endpoints enforce vendor ownership: middleware requireVendorAccess checks req.user.vendorId matches vendor.id
- [ ] T067 [P] Ensure admin category and approval routes are protected by requireRole('admin')
- [ ] T068 [P] Add input sanitization middleware or schema rules:
  - Strip HTML tags from vendor description, service descriptions
  - Enforce text length limits: description 2000, service name 255
- [ ] T069 [P] Implement duplicate vendor detection on registration:
  - Check unique contactEmail (database unique constraint)
  - Check unique combination (businessName, city, region) with case-insensitive comparison
  - Return 409 with message if duplicate found

### Error Handling & Validation

- [ ] T070 [P] Add comprehensive validation error responses using existing validation middleware (validateBody, validateParams)
- [ ] T071 [P] Handle database constraint violations gracefully: P2002 (unique), P2003 (foreign key) with user-friendly messages
- [ ] T072 [P] Standardize error response format: { error: string, message?: string, details?: any }

### Monitoring & Observability

- [ ] T073 [P] Add business metrics logging (using existing metrics service or structured logs):
  - vendor.registration.count
  - approval.queue.size
  - approval.processing.time (histogram)
  - search.query.latency (histogram)
  - portfolio.upload.success/failure (counter)
- [ ] T074 [P] Log key business events with consistent format: vendor.created, vendor.updated, vendor.approved, vendor.rejected, category.created, search.performed

### Data Integrity

- [ ] T075 [P] Add database constraints:
  - categories.name UNIQUE
  - vendors (businessName, city, region) functionally unique index (where status != 'DEACTIVATED')
  - vendor_categories (vendorId, categoryId) composite primary key or UNIQUE
- [ ] T076 [P] Ensure foreign key constraints with proper ON DELETE behavior:
  - vendor_categories: ON DELETE CASCADE for vendorId and categoryId
  - services: ON DELETE CASCADE for vendorId
  - documents: ON DELETE CASCADE for vendorId
  - approval_requests: ON DELETE CASCADE for vendorId

### API Contract & Documentation

- [ ] T077 [P] Update OpenAPI/Swagger specs (if used) for all new endpoints
- [ ] T078 [P] Add response examples and error codes to route documentation comments

### Frontend Integration (if applicable)

- [ ] T079 [P] Provide API response shape documentation for frontend teams implementing vendor portal and admin UI
- [ ] T080 [P] Coordinate with frontend on error handling and loading states

**Checkpoint**: All cross-cutting concerns addressed, system secure, performant, observable

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational completion
  - US1 (P1) → US2 (P2) → US3 (P2) → US4 (P3) in priority order
- **Integration (Phase 7)**: Depends on all desired user stories being complete

### Within Each User Story

- Schema/migrations first (if needed)
- Validation schemas before endpoints
- Services before endpoints that use them
- Core implementation before polish/optimization
- Story complete before moving to next priority

### Cross-Story Dependencies

- **US2 (Categories)**: Depends on Category model; integrates with US1 (vendor category assignment)
- **US3 (Search)**: Depends on search indexes; uses vendor/category data from US1/US2
- **US4 (Approval)**: Depends on ApprovalRequest model; integrates with US1 vendor lifecycle

### Story Independence

- Each user story should be end-to-end testable after completion
- US1 can be tested without US2/US3/US4 (vendors create profiles independently)
- US2 can be tested without US3/US4 (admin manages categories)
- US3 can be tested after US1+US2 provide data but does not depend on US4
- US4 can be tested after US1 provides vendor creation flow

---

## Parallel Opportunities

**Phase 1 (Setup)**:
- T001 (review schema) sequential
- T002 (migration) and T003 (env) can be parallel if separate files

**Phase 2 (Foundational)**:
- Schema changes (T004-T009) should be in single migration file → SERIALIZE
- Index creation (T011-T014) can be in same or separate migrations, applied sequentially
- Search service (T015) can be developed independently in parallel with schema work (after interface defined)

**Phase 3 (US1 - P1)**:
- Parallel: T016 (schemas), T019 (CDN service verification), T023 (service model check), T026 (registration endpoint design)
- Sequential: T017 depends on T016; T018 and T020 depend on existing routes; T024 depends on T023
- US1 is MVP - prioritize completion before other stories

**Phase 4 (US2 - P2)**:
- Parallel: T029 (schemas), T030 (routes), T031 (middleware)
- Sequential: T032 before finalizing routes; T034 depends on Category model; T036 last

**Phase 5 (US3 - P2)**:
- T037-T040 (search service enhancements) can be developed in parallel before API integration (T037)
- T044-T045 (performance) after search logic complete

**Phase 6 (US4 - P3)**:
- Parallel: T051 (routes), T052 (middleware), T053 (approval logic)
- T048-T050 depend on US1 vendor flow modifications
- T054-T060 depend on endpoints/events being in place

**Phase 7 (Integration)**:
- Most tasks independent across different areas (rate limiting, auth, sanitization, metrics, data constraints)
- Can run in parallel; some dependencies on specific endpoints being complete (e.g., T066 needs vendor endpoints; T073 needs events logged)

---

## Parallel Example: User Story 1

```bash
# After foundational phase complete, launch US1 tasks in logical batches:

# Batch 1 - Schema & Service Prep (parallel):
Task: T016 - Update vendor validation schemas
Task: T019 - Verify/refactor CDN service
Task: T023 - Review Service model

# Batch 2 - Core Endpoints (after Batch 1):
Task: T017 - Update vendor profile endpoint
Task: T018 - Portfolio endpoints
Task: T024 - Service CRUD endpoints

# Batch 3 - Registration & Supporting (parallel to Batch 2 where independent):
Task: T026 - Vendor registration endpoint
Task: T020, T021, T022 - Service model, validation, audit

# All US1 tasks complete → MVP ready for independent testing
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (schema migration, env vars)
2. Complete Phase 2: Foundational (Category, ApprovalRequest, indexes, search service) - **BLOCKS**
3. Complete Phase 3: User Story 1 (vendor profile + services + portfolio + registration)
4. **STOP and VALIDATE**: Test US1 independently:
   - Vendor registers → profile created (PENDING or ACTIVE)
   - Vendor updates profile with service areas and categories
   - Vendor uploads portfolio images (pre-signed URLs work)
   - Vendor creates/edits services
   - Vendor soft-deletes profile
   - All data validated, audit log entries created
5. Deploy/demo if ready

### Incremental Delivery

After MVP (US1) is stable:

1. Add Phase 4: US2 (Category Management) → Admin can curate categories, vendors assign them
2. Add Phase 5: US3 (Search Enhancement) → Full-text + trigram search with filters
3. Add Phase 6: US4 (Approval Workflow) → Admin approval queue, notifications
4. Add Phase 7: Integration + polish
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after foundation:

1. Developer A: US1 (vendor profile) - complete first
2. Developer B: US2 (categories) - start after foundation
3. Developer C: US3 (search) - start after foundation, after US1/US2 data exists for testing
4. Developer D: US4 (approval) - start after US1 complete
5. Integrate independently; each story testable in isolation

---

## Notes

- **[P]** tasks = different files, no dependencies within same phase
- **[Story]** label maps task to specific user story: [US1], [US2], [US3], [US4]
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Database changes (migrations) must be applied and verified before dependent tasks
- Existing codebase already has Vendor, Service, VendorUser, AuditLog, some vendor routes - extend, don't duplicate
- Existing auth/RBAC middleware should be reused: `requirePermission`, `requireRole` in packages/backend/src/middleware/rbac.middleware.ts
- Existing rate limiting middleware exists at packages/backend/src/middleware/rateLimit.middleware.ts - reuse
- Public vendor search endpoint exists at packages/backend/src/routes/public-vendors.routes.ts - enhance it
- Vendor routes exist at packages/backend/src/routes/vendor.routes.ts - extend them
- Admin routes exist at packages/backend/src/routes/admin.routes.ts - add category/approval endpoints there
- Notification service exists at packages/backend/src/services/notification.service.ts - extend for approval events
- CDN service exists at packages/backend/src/services/cdn.service.ts - verify R2/S3 pre-signed URLs
- Email service exists at packages/backend/src/services/email.service.ts - use for approval emails
- Event bus exists at packages/backend/src/services/event-bus.service.ts - emit domain events
- Search service exists at packages/backend/src/services/search.service.ts - enhance with trigram

---

**Feature**: 004-vendor-marketplace
**Branch**: 004-vendor-marketplace
**Date**: 2026-04-08
**Total Estimated Tasks**: 80
**MVP Scope**: US1 (T001-T027) ≈ 27 tasks
**Parallelizable Tasks**: ~35% (marked [P])
