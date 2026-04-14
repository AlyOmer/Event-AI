# Feature Specification: Event Management

**Feature Branch**: `005-event-management`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "Event Management    Create/edit/cancel events, event types (wedding, corporate, etc.)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Event Creation and Basic Management (Priority: P1)

As an event organizer (user), I want to create, view, edit, and cancel my events, so that I can plan and manage my events (weddings, corporate functions, parties) through a self-service interface.

**Why this priority**: This is the core functionality—the ability to manage events. Without this, the platform has no central organizing concept. Events are the primary reason vendors and customers interact. All other features (vendor bookings, AI planning) depend on events existing.

**Independent Test**: Can be fully tested by a user creating an event with basic details (name, type, date, location), viewing it, editing it, and then canceling it. Each operation should be independently successful and update the event record accordingly.

**Acceptance Scenarios**:

1. **Given** I am logged in as a user, **When** I create a new event with name, event type, date, location, and guest count, **Then** the event is saved and I can view its details in my event dashboard.

2. **Given** I have an existing event, **When** I edit its details (e.g., change date or location), **Then** the changes are saved and reflected in all views.

3. **Given** I have an upcoming event, **When** I cancel it, **Then** the event status changes to "canceled" and any associated vendor bookings or AI plans are notified to handle cleanup (cancellation policies may apply).

4. **Given** I attempt to create an event with invalid data (e.g., past date, missing required fields), **When** I submit, **Then** I receive clear validation errors and the event is not created.

5. **Given** I want to view all my events, **When** I go to my events dashboard, **Then** I see a list of my events with status indicators (planned, active, completed, canceled) and can filter by status.

---

### User Story 2 - Event Type Management (Priority: P2)

As an administrator, I want to define and manage event types (wedding, corporate, birthday, conference, etc.), so that I can categorize events and enable type-specific workflows or vendor matching.

**Why this priority**: Event types provide essential taxonomy. They structure the platform, drive vendor categorization (vendor marketplace knows which vendors serve which event types), and may influence AI planning strategies. Admin-controlled ensures consistency. This enables better vendor matching and analytics but is not strictly required for basic event creation (hence P2).

**Independent Test**: Can be tested by an admin creating, editing, and deactivating event types. Each type has a name, description, and possibly icon. Vendors can indicate which event types they serve (see vendor marketplace spec). Events must select from active event types.

**Acceptance Scenarios**:

1. **Given** I am an admin, **When** I create a new event type (e.g., "Graduation Party") with description, **Then** it becomes available for users to select when creating events and for vendors to indicate service coverage.

2. **Given** an event type exists, **When** I edit its name or description, **Then** all events or vendor profiles referencing it are updated with the new name (or remain consistent via foreign key relationships).

3. **Given** an event type has associated events or vendors, **When** I attempt to delete it, **Then** the system prevents deletion or requires reassignment (no orphaned references).

4. **Given** event types are defined, **When** a user creates an event, **Then** they must select one of the active event types from a dropdown.

---

### User Story 3 - Event Details and Vendor Booking Integration (Priority: P2)

As an event organizer, I want to add detailed information to my event and connect with vendors, so that I can plan the event comprehensively and secure necessary services.

**Why this priority**: After basic event creation (P1), users need to enrich events with details and actually book vendors. This story ties events to vendor marketplace. It's P2 because vendors must exist first (vendor marketplace P1 needs to be implemented). This creates the core transaction loop: user creates event → searches vendors → sends inquiries/bookings → vendors respond.

**Independent Test**: Can be tested by a user editing their event to add a budget, guest count, special requirements, timeline; then searching for vendors (from vendor marketplace) and sending booking requests or inquiries. Vendors receive the request and can accept/decline.

**Acceptance Scenarios**:

1. **Given** I have created an event, **When** I add detailed information (budget, guest count, timeline, special requests), **Then** those details are saved and visible in the event planning view.

2. **Given** my event has details filled in, **When** I search for vendors (e.g., photographers in my city), **Then** I can shortlist vendors and send them an inquiry or booking request linked to my event.

3. **Given** I have sent booking requests to vendors, **When** the vendor responds (accepts, declines, or proposes changes), **Then** I receive a notification and my event's vendor list updates accordingly.

4. **Given** a vendor has been booked for my event, **When** I view my event details, **Then** I see the vendor's contact information, booking status, and any agreements or contracts (if separate).

---

### Edge Cases

- What happens when a user tries to create an event with a name that's too long or contains prohibited content? The system should enforce length limits (e.g., 100 characters) and content filtering (no profanity, no personal data), returning clear errors.

- What happens when a user tries to edit an event that has already passed (completion date in the past)? The system may allow edits if event not yet marked "completed", but once completed, events should be read-only to preserve historical accuracy.

- What happens when two users try to edit the same event simultaneously (race condition)? The system should use optimistic concurrency control (version numbers or updated_at timestamps) to detect conflicts and prompt the user to merge changes.

- What happens when an event is canceled but vendors have already been booked and possibly incurred costs? The system should handle cancellation policies: notify vendors, trigger refund/deposit workflows (outside scope), and update event status. Vendors may need to approve cancellation if contracts exist.

- What happens when an event type is deactivated while events still reference it? Existing events retain their event type (historical integrity), but new events cannot select that type. The system should not break existing references.

- What happens when a user has an excessive number of events (e.g., 1000+)? The system should paginate event lists and possibly archive old completed events to cold storage after a retention period (e.g., 2 years).

- What happens when vendor booking fails due to vendor unavailability or double-booking? The system should detect booking conflicts if the platform supports availability calendars; otherwise, vendors can reject inquiries. The user should receive clear feedback.

- What happens when an event requires AI-driven planning (AI agent suggests vendors, timeline, etc.) but that feature is not yet implemented? The spec focuses on event CRUD; AI planning is a separate future feature. The system should allow placeholder for AI-generated plan later.

- What happens when event details contain large amounts of text or attachments? The system should enforce reasonable limits (e.g., description ≤5000 characters, attachments ≤10 files × 10MB each) and handle uploads securely.

- What happens when an event is created with a date very far in the future (5 years)? The system should allow it, but archiving and data retention policies may eventually move very old events to archive.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow authenticated users to create events with essential fields: event name, event type (foreign key to EventType), date and time (start and optional end), location (venue name, address, city, country), expected guest count, and optional description.

- **FR-002**: The system MUST allow users to view a list of their own events, with pagination (20 per page), sorted by creation date (default) or event date, and filter by status (planned, active, completed, canceled).

- **FR-003**: The system MUST allow users to edit their events while the event is in "planned" or "active" status; once marked "completed" or "canceled", edits are restricted to admins only.

- **FR-004**: The system MUST allow users to cancel their events, changing status to "canceled" and recording cancellation date and reason (optional). Canceled events remain in history but are excluded from active views.

- **FR-005**: The system MUST enforce data validation on event fields: required fields, date must be in future (for planned/active events), guest count positive integer, location fields not empty, description length limits.

- **FR-006**: The system MUST provide an admin interface to create, read, update, and deactivate event types (wedding, corporate, birthday, etc.), with fields: type name (unique), description, icon (optional), and display order.

- **FR-007**: The system MUST require that every event selects an active event type; deactivated types cannot be assigned to new events but remain on existing events.

- **FR-008**: The system MUST support event status lifecycle: "draft" → "planned" → "active" (event day) → "completed" → (optional "archived"). Transitions: draft→planned (user confirms), planned→active (automatic on event date), active→completed (manual or auto after date), planned/active→canceled (user cancels).

- **FR-009**: The system MUST allow users to add detailed planning information to their events: budget estimate, timeline or schedule, special requirements (e.g., dietary restrictions, accessibility needs), and attachments (files up to size limit).

- **FR-010**: The system MUST associate vendors with events through a booking mechanism (see separate booking feature). This spec defines that events can have zero or more booked vendors; booking creation/modification is handled by the booking subsystem but must be navigable from the event view.

- **FR-011**: The system MUST enforce authorization: users can only access, create, edit, or cancel their own events; admins can view and manage all events; vendors can only see events they are booked for.

- **FR-012**: The system MUST log all significant event actions (creation, edit, cancellation, status changes) with user ID, timestamp, and changed fields for audit purposes.

- **FR-013**: The system MUST rate-limit event creation and updates to prevent abuse (e.g., 10 events created per day per user, 20 updates per hour per event).

- **FR-014**: The system MUST prevent users from editing events that belong to other users or that they are not authorized to modify (enforce ownership checks at API level).

- **FR-015**: The system MUST provide a search/browse feature for users to discover public events (if events are public) but primarily events are private to their creator and associated vendors. Event marketplace visibility is separate.

- **FR-016**: The system MUST support event duplication: users can create a new event based on an existing one (copy details), helpful for recurring events.

- **FR-017**: The system MUST send notifications for key event milestones: event reminder (e.g., 1 week before), vendor booking status changes, cancellation confirmations. Notification delivery is handled by separate notification system.

- **FR-018**: The system MUST maintain soft deletion for events: canceling marks as "canceled" but retains data; hard deletion (purge) is admin-only and only for events older than a retention period (e.g., 2 years) per data retention policy.

- **FR-019**: The system MUST allow admins to view all events across users for oversight, analytics, and support purposes, with filters by date, event type, status, etc.

- **FR-020**: The system MUST handle timezones correctly: event date/times are stored in UTC, displayed in user's local timezone based on their profile preference. Timezone conversions must be consistent.

### Key Entities

- **Event**: Represents a planned occasion (wedding, corporate function, etc.). Attributes include: unique identifier, user ID (owner), event name, event type (foreign key to EventType), start date/time (UTC), end date/time (optional), location (address fields), guest count, description (text), budget (numeric, optional), status (draft, planned, active, completed, canceled), created date, updated date, timezone (string like "Asia/Karachi"), special requirements (text), cancellation reason (text, nullable). Event is the central aggregate.

- **EventType**: Represents a category of events. Attributes include: unique identifier, type name (unique, e.g., "Wedding", "Corporate", "Birthday"), description (text), icon (URL or identifier), display order (integer for sorting), active status (boolean), created date, updated date. Event types are curated by admins.

- **EventVersion** (optional, for audit): Represents historical snapshots of event data at key points. Attributes include: version ID, event ID, snapshot data (JSONB or relational copy), change reason (user edit, status change, cancellation), changed by (user ID), timestamp. Used for rollback and compliance.

- **Booking** (defined in separate Booking feature but linked here): Represents a vendor contracted for an event. Attributes include: booking ID, event ID (foreign key), vendor ID (foreign key), service type, status (pending, confirmed, canceled), terms, timestamps. Event may have many bookings.

- **EventAttachment** (optional): Represents files attached to an event (contracts, inspiration images, etc.). Attributes include: attachment ID, event ID, file name, storage URL, size, MIME type, uploaded by, uploaded at. Supports event planning documents.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a complete event (including all required fields and optional details) in under 5 minutes on average.

- **SC-002**: Event list pages (user's events) load in under 200 milliseconds for up to 100 events per user, with pagination.

- **SC-003**: Event edits are saved and reflected in under 1 second (from submission to successful response).

- **SC-004**: The system maintains ≥99.9% availability for event CRUD operations during business hours (9 AM - 9 PM local time).

- **SC-005**: Event status transitions (planned → active → completed) happen automatically with 100% accuracy based on scheduled dates or manual triggers.

- **SC-006**: 95% of event cancellations are processed successfully within 5 seconds, including any downstream notifications (vendor alerts).

- **SC-007**: Event data integrity: zero lost or corrupted events due to software errors (measured over 12 months).

### User Satisfaction

- Users rate event creation/management ease ≥4.5/5.
- Users report confidence that their event data is accurate and reliable ≥4/5.
- Admins rate event type management and oversight ≥4/5.

### Business Impact

- Enable users to plan and book events end-to-end without manual intervention: increase self-service event creation to 100% of customers.
- Reduce admin time spent on event creation support from 15 minutes per event to <2 minutes (automation + self-service).
- Increase event completion rate (events that proceed to booked vendors) to ≥70% (from current baseline if any).
- Maintain event data quality score ≥95% completeness (required fields filled) across all events.

## Assumptions

- Users are authenticated via `002-user-auth` feature; event ownership is tied to user accounts.

- Vendors and vendor marketplace exist (`004-vendor-marketplace`), and events can be linked to vendors via a separate Booking feature (not in this spec, but events have relationships to bookings).

- Event types are curated by administrators; vendors reference the same event types in their profiles (consistency between event types and vendor categories is assumed but not enforced by this spec).

- The database is the cloud-only Neon PostgreSQL from `003-database-setup`. Event and EventType tables reside in `public` schema managed by Backend package (Prisma).

- Notifications (email, in-app) for event milestones are handled by a separate notification system or service; this spec only requires that the system triggers appropriate notification events.

- Event search/browse for public events is minimal; primarily events are private to their owner and associated vendors. If public event directory is needed, it's a separate feature.

- Timezone handling: users set their timezone in their profile (from auth profile). Event date/times are stored in UTC; conversion happens at presentation layer. The spec does not define timezone database maintenance.

- Event duplication (FR-016) copies core fields but not bookings or vendor associations (those are event-specific and not duplicated).

- Cancellation policies (refunds, penalties) are business logic that may involve payment processing; that is out of scope. This spec only covers status change and optional reason capture.

- Attachments (FR-009 optional details) upload to object storage (CDN); the system stores URLs. File size limits: 10MB per file, max 10 files per event. File type restrictions: PDF, JPG, PNG, DOCX.

- Event status lifecycle: Draft (user saving incomplete), Planned (confirmed upcoming), Active (on the day(s) of event), Completed (after event ends), Canceled (abandoned). Transitions: draft→planned (user action), planned→active (automatic near event date or manual), active→completed (auto after end or manual), planned/active→canceled (user or admin).

- AI planning integration: Future feature where AI agents generate event plans, timelines, vendor recommendations. The Event entity may later include a reference to an AI-generated plan. This spec leaves room for that extension.

- Data retention: Completed and canceled events are retained for audit and business analytics for at least 2 years before archival or deletion, per legal requirements.

- Search within a user's own events (by name, date range, type, status) is supported; that's part of the event list filtering (FR-002). Full-text search on event descriptions is not required in MVP but can be added later.

- Event location fields are free-text but structured (venue name, address, city, country). Geocoding or map integration is separate.

- Event budget is an optional numeric field; currency is assumed to be PKR (Pakistani Rupees) for the Pakistan market, but could be multi-currency later. Not in scope.
