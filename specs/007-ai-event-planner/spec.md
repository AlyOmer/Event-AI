# Feature Specification: AI Event Planner

**Feature Branch**: `007-ai-event-planner`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "AI Event Planner    Auto-generate event plans with vendor recommendation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Event Plan Generation (Priority: P1)

As an event organizer, I want the AI to automatically generate a comprehensive event plan for my event, so that I can have a structured blueprint of tasks, timeline, budget allocation, and vendor recommendations without starting from scratch.

**Why this priority**: This is the core value proposition of the AI Event Planner feature—automating the heavy lifting of event planning. Without automated plan generation, users must manually create plans, which is time-consuming and overwhelming. This feature accelerates planning and ensures nothing is missed.

**Independent Test**: Can be tested by a user creating an event (or using an existing event), then clicking "Generate Event Plan" or asking the AI to create one. The system should produce a complete event plan document with timeline, budget breakdown, vendor recommendations, and task list within a reasonable time (under 30 seconds). The plan should be viewable, editable, and savable.

**Acceptance Scenarios**:

1. **Given** I have created an event with basic details (type, date, location, guest count, budget), **When** I request an AI-generated event plan, **Then** the system returns a structured plan organized into: event timeline, budget allocation by category, recommended vendor types and specific vendor suggestions, and a checklist of planning tasks with suggested deadlines.

2. **Given** the AI generates a plan, **When** I review it, **Then** the plan is logically consistent: timeline milestones don't conflict, budget sums to total budget, vendor recommendations match event type and location, and tasks are sequenced properly.

3. **Given** I have insufficient information in my event (missing budget or guest count), **When** I request plan generation, **Then** the AI asks clarifying questions or makes reasonable assumptions (documented) and proceeds with those assumptions, flagging any assumptions made.

4. **Given** the AI generates a plan, **When** I save it, **Then** the plan is persisted and associated with my event, and I can view it later or share it with stakeholders.

5. **Given** multiple AI-generated plans exist for an event, **When** I compare them, **Then** each plan has a version number and timestamp, and I can retain multiple versions to track evolution.

---

### User Story 2 - Vendor Recommendations in Event Plan (Priority: P2)

As an event organizer, I want the AI-generated event plan to include specific vendor recommendations that match my event needs, so that I can quickly identify and contact suitable vendors without manual search.

**Why this priority**: Vendor recommendations are a key component of the event plan and directly leverage the vendor marketplace. This is the tangible "actionable" part of the plan—vendors the user can book. P2 because it builds on the plan generation but is essential for the plan's utility.

**Independent Test**: Can be tested by generating a plan for a specific event (e.g., "wedding for 150 guests in Lahore, budget 500K") and verifying that the recommended vendors are: (a) appropriate for the event type (e.g., photographers, caterers, venues), (b) located in or serving the specified city/region, (c) within the budget range, (d) currently active and available, and (e) include enough variety (3-5 options per category).

**Acceptance Scenarios**:

1. **Given** I have an event with defined requirements, **When** the AI generates a plan, **Then** it includes a "Recommended Vendors" section listing vendor categories (Photography, Catering, Venue, etc.) and for each category, suggests 3-5 specific vendors from the marketplace that match the event's location, budget, and availability.

2. **Given** vendor recommendations are presented, **When** I click on a vendor name, **Then** I can view the vendor's full profile (services, portfolio, reviews, contact info) in a new view.

3. **Given** a recommended vendor is fully booked or no longer active, **When** the AI queries the marketplace, **Then** it excludes inactive vendors and attempts to find alternatives if available; if none, it notes "No available vendors found in this category."

4. **Given** my budget is limited, **When** the AI recommends vendors, **Then** it considers price range (if vendors list price ranges) and prioritizes vendors within my budget, or provides a mix with notes on value.

5. **Given** I ask "Why did you recommend this vendor?", **When** I request justification, **Then** the AI provides reasoning based on vendor's ratings, relevance to event type, location proximity, and package offerings.

---

### User Story 3 - Plan Customization and Iteration (Priority: P3)

As an event organizer, I want to customize the AI-generated event plan to suit my preferences, so that I can adjust recommendations, modify timelines, and refine the plan as my vision evolves.

**Why this priority**: Users need flexibility—AI provides a starting point, but every event is unique. Editing and iteration allow the user to take ownership. P3 because it's an enhancement over the basic generated plan; the MVP can have generation only, but customization greatly improves UX and plan utility.

**Independent Test**: Can be tested by generating a plan, then editing various sections: changing the timeline dates/times, adjusting budget allocations (e.g., increase catering budget, decrease decor), replacing recommended vendors with alternatives, adding custom tasks, and removing unwanted suggestions. After edits, the plan should save correctly and reflect changes. Re-opening the plan should show the customized version.

**Acceptance Scenarios**:

1. **Given** I have an AI-generated event plan, **When** I edit a timeline milestone (e.g., move "book venue" from 6 months before to 4 months before), **Then** the change is saved and dependent tasks may adjust automatically (e.g., "send invitations" date shifts accordingly).

2. **Given** I disagree with a vendor recommendation, **When** I replace it with another vendor from the marketplace or a custom entry, **Then** the plan updates to show my chosen vendor and removes the original recommendation.

3. **Given** I have a specific budget constraint, **When** I manually adjust budget allocations (e.g., increase photography budget by 20%, decrease flowers by 10%), **Then** the plan reflects the new numbers and total budget remains consistent (or warns if over budget).

4. **Given** I want to add a custom task not in the AI's list, **When** I add "Hire a special fireworks display" with a due date, **Then** it appears in my task checklist with the assigned date.

5. **Given** I've made extensive changes, **When** I choose to regenerate the plan (starting fresh), **Then** I can either keep my customized version or overwrite with a new AI-generated plan (with confirmation prompt).

---

### User Story 4 - Plan Export and Sharing (Priority: P3)

As an event organizer, I want to export and share my event plan with stakeholders (vendors, family members, collaborators), so that everyone is aligned on the event vision and responsibilities.

**Why this priority**: Collaboration is important—event planning involves multiple parties. Sharing the plan facilitates coordination. P3 because it's an enhancement after plan creation and customization exist. Not essential for MVP but valuable.

**Independent Test**: Can be tested by a user with a completed event plan clicking "Export" or "Share" and choosing a format (PDF, shareable link). The exported document should be well-formatted, include all plan sections, and be easy to read. A shareable link should allow view-only access to the plan for recipients without requiring login (or with appropriate permissions).

**Acceptance Scenarios**:

1. **Given** I have finalized my event plan, **When** I click "Export as PDF", **Then** a PDF document is generated with a professional layout, including event details, timeline chart, budget table, vendor list with contact info, and task checklist.

2. **Given** I want to share the plan with my fiancé/family, **When** I generate a shareable link and send it, **Then** the recipient can view the plan in their browser without needing to log in (read-only access).

3. **Given** I share a plan link, **When** the recipient opens it, **Then** they see the latest version of the plan with all customization intact.

4. **Given** I update my plan after sharing, **When** I save changes, **Then** the shareable link reflects the updated plan (always shows current version).

5. **Given** I no longer want to share a plan, **When** I revoke the shareable link, **Then** the link becomes invalid and cannot be accessed.

---

### Edge Cases

- What happens when the AI cannot generate a viable plan due to insufficient event details? It should either ask for more information or generate a partial plan with placeholders and clearly indicate what's missing.

- What happens when the AI suggests vendors that the user has already booked or rejected? The system should avoid recommending vendors already associated with the event unless explicitly requested.

- What happens when vendor availability changes after the plan is generated? The plan might become stale. The system could provide a "Check vendor availability" button or periodically warn that recommendations may be outdated.

- What happens when the generated plan's budget exceeds the user's stated budget? The AI should either adjust recommendations to fit or clearly flag the overage and suggest alternatives or increasing budget.

- What happens when the user has conflicting preferences (e.g., "luxury event" with "shoestring budget")? The AI should note the conflict and ask the user to prioritize or adjust expectations.

- What happens when the event date is very near (e.g., only 2 weeks away) and the AI cannot realistically fit all tasks? The plan should adjust timelines, note that some tasks may be rushed, or suggest postponing certain elements.

- What happens when the AI's timeline suggests booking a vendor that is already fully booked for the event date? Vendor availability should be checked; if unavailable, the AI should either find alternatives or note "May require backup vendor."

- What happens if the user modifies the plan and then regenerates? Offer choice: keep current plan or overwrite with fresh AI generation. Avoid accidental loss of customizations.

- What happens when the generated plan includes tasks that require external services (e.g., "obtain marriage license") that are not vendor-related and may have jurisdiction-specific requirements? The AI should avoid giving legal/government advice beyond general guidance; mark such tasks as "research local requirements."

- What happens when the AI generates a plan that is overly generic or not tailored to the specific event? User feedback mechanism should allow rating the plan quality; continuous improvement loops should refine prompts and RAG retrieval.

- What happens when multiple users collaborate on the same event plan simultaneously? Concurrency control: optimistic locking (version numbers) to prevent overwrites; merge conflicts or warn before overwriting.

- What happens when the event plan references external information (e.g., "book venue 6 months in advance") that may not hold for all locations/cultures? The plan should be contextual; AI should be trained on regional norms (Pakistan-specific wedding timelines, etc.).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow users to request an AI-generated event plan for an existing event. The plan generation is triggered either via a button in the event details view or via a chat command to the AI agent.

- **FR-002**: The system MUST implement an EventPlannerAgent (specialist agent) responsible for generating event plans. This agent uses RAG (Retrieval-Augmented Generation) to access domain knowledge about event planning best practices, timelines, budget allocation guidelines, and vendor category recommendations.

- **FR-003**: The generated event plan MUST include the following sections:
  - Event Summary (basic event details)
  - Timeline: chronological milestones from planning lead-up to post-event, with suggested dates/durations based on event date.
  - Budget Breakdown: allocated amounts by category (venue, catering, photography, decorations, entertainment, attire, etc.) that sum to the total event budget, with reasoning for allocations based on event type and size.
  - Vendor Recommendations: list of recommended vendor categories (Photography, Catering, etc.) and for each, specific vendor suggestions pulled from the vendor marketplace with brief justification.
  - Task Checklist: actionable tasks (e.g., "Book venue", "Send invitations", "Finalize menu") with suggested deadlines and responsible party (usually the event organizer).

- **FR-004**: The system MUST store generated event plans in the database as structured data (JSONB or relational tables) with versioning. Each plan is associated with an event and has a version number, timestamp, and generation method (AI version).

- **FR-005**: The system MUST allow users to view, edit, and save changes to their event plans. Edits can modify timeline entries, budget numbers, vendor selections (replace recommendations), task list (add/remove/complete), and notes.

- **FR-006**: The system MUST support multiple versions of an event plan. When a user edits and saves, a new version is created. Users can view previous versions and optionally revert to an earlier version.

- **FR-007**: The system MUST integrate with the vendor marketplace (`004-vendor-marketplace`) to fetch active vendor data when generating recommendations. The RAG system retrieves vendor information (name, category, location, ratings, price range) relevant to the event's requirements.

- **FR-008**: The system MUST enforce that vendor recommendations respect event constraints: event type (wedding, corporate), location (city/region), and budget feasibility. The recommendation engine should score and rank vendors by relevance and quality.

- **FR-009**: The system MUST allow users to ask the AI to refine or regenerate parts of the plan (e.g., "give me more budget for catering", "suggest different photographer options", "add task for wedding favors"). The AI should update the plan accordingly.

- **FR-010**: The system MUST provide export functionality: users can export their event plan as a PDF document or generate a shareable view-only link. The export should be well-formatted and include all plan sections.

- **FR-011**: The system MUST persist all AI generation requests and results (prompt, plan generated, timestamp, user ID) for audit and potential fine-tuning.

- **FR-012**: The system SHOULD include a feedback mechanism on generated plans: users can rate the plan (helpful/not helpful) and provide comments. This feedback is stored and used to improve the AI over time.

- **FR-013**: The system MUST handle errors gracefully: if the AI service is unavailable or times out, the user receives a clear error message and can retry. Failed generation attempts are logged.

- **FR-014**: The system MUST validate that the generated plan's total budget does not exceed the event's total budget (unless user explicitly overrides). If suggested allocations sum to more than budget, the AI should adjust or flag the discrepancy.

- **FR-015**: The system MUST ensure that vendor recommendations do not include vendors that are inactive, rejected by the user in the past, or already booked for the event date (if availability data is accessible). The system should check these filters before presenting.

- **FR-016**: The system SHOULD support plan templates: users can save a customized plan as a template for future events of similar type, then generate new plans based on that template (semi-automated).

- **FR-017**: The system MUST log all plan generation, edits, exports, and shares for audit and usage analytics.

- **FR-018**: The system MUST enforce authorization: users can only access and modify plans for their own events; admins may view all plans for oversight.

- **FR-019**: The system SHOULD send notifications when a plan is generated, significantly modified, or shared with others, to keep stakeholders informed.

- **FR-020**: The system SHOULD provide a "Plan Health" indicator showing completeness (e.g., "70% tasks assigned") and flag potential issues (e.g., "Budget over-allocated", "Task deadline missed").

### Key Entities

- **EventPlan**: Represents a generated event plan document. Attributes include: plan ID (UUID), event ID (foreign key), version number, creation timestamp, created by (user ID), generation method (AI-only, AI+user-edited, manual), status (draft, final, archived). The plan as a whole is versioned.

- **PlanSection** (or embedded in EventPlan as JSONB): One of the main plan sections: Timeline, Budget, Vendors, Tasks, Notes. Could be modeled as separate tables or as a structured JSON document. For flexibility, JSONB is acceptable; for queryability, separate tables. Attributes would include section type and content.

- **TimelineMilestone**: Represents a point in the event planning timeline. Attributes: milestone ID, plan ID, title (e.g., "Book Venue"), suggested date (computed from event date), actual date (if user sets), description, dependencies (other milestones).

- **BudgetCategory**: Represents a line item in the plan's budget. Attributes: category ID, plan ID, category name (e.g., Catering), allocated amount, actual spend (later), notes.

- **VendorRecommendation**: Represents a specific vendor suggested in the plan. Attributes: recommendation ID, plan ID, vendor ID (foreign key to Vendor), reason for recommendation (text), status (suggested, contacted, booked, rejected), user rating of vendor (if user rates after contact).

- **PlanTask**: Represents an actionable task in the plan checklist. Attributes: task ID, plan ID, task name, description, suggested due date, assigned to (vendor or user), status (not started, in progress, completed), notes.

- **PlanVersion** (if separate from EventPlan): Represents a historical snapshot of a plan. Attributes: version ID, plan ID, version number, snapshot data (JSONB), created at, created by. Allows rollback.

- **PlanFeedback** (optional): User feedback on plan quality. Attributes: feedback ID, plan ID, user ID, rating (1-5), comments, timestamp.

**Note**: EventPlan could be a single aggregate with JSONB sections, or relational. The spec is flexible; implementation chooses based on query needs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Plan generation time: 90% of event plans are generated within 30 seconds of user request (from request to completed plan display).

- **SC-002**: Plan completeness: Generated plans include at least 80% of expected sections (timeline, budget, vendors, tasks) with non-empty content (i.e., not placeholders).

- **SC-003**: Vendor recommendation relevance: When users rate recommendations, at least 85% of suggested vendors are marked as "relevant" or better.

- **SC-004**: User adoption: 60% of events that reach "planned" status have an AI-generated event plan associated within 7 days of event creation.

- **SC-005**: Plan utility: 70% of users who generate a plan go on to edit at least one section (indicating engagement with the plan content).

- **SC-006**: Export success: 95% of plan export attempts (PDF or share link) succeed on first try without errors.

- **SC-007**: Plan accuracy: Budget allocations in generated plans sum correctly to the event's total budget in 100% of cases (no arithmetic errors).

### User Satisfaction

- Users rate generated event plans ≥4/5 for usefulness and relevance.
- Users report that event plans save them planning time: average time saved ≥5 hours per event compared to creating plan manually.
- 80% of users who generate a plan would recommend the feature to another event organizer.

### Business Impact

- Accelerate event planning cycle: reduce average time from event creation to first vendor booking from 14 days to 7 days.
- Increase user engagement: users with AI-generated plans are 2x more likely to proceed to vendor bookings.
- Reduce support burden: fewer questions about "how to plan my event" because the AI provides structured guidance.
- Improve vendor matching quality: higher booking conversion from AI-recommended vendors compared to generic search.

## Assumptions

- Event data model exists (`005-event-management`) with fields for type, date, location, guest count, budget. AI Event Planner uses this as input.

- Vendor marketplace exists (`004-vendor-marketplace`) and provides an API or database access to query active vendors with filters (category, location, etc.). Vendor data includes category, service area, ratings, and optionally pricing or package information.

- The AI Event Planner is implemented as a specialist agent (EventPlannerAgent) within the `packages/agentic_event_orchestrator` service, using the OpenAI Agents SDK, and has access to RAG capabilities to retrieve domain knowledge (event planning timelines, best practices, budget guidelines) and vendor data.

- The RAG system (LangChain for document retrieval) indexes:
  - Internal knowledge base of event planning guides (wedding timelines, corporate event checklists, budget allocation models by event type and guest count)
  - Vendor catalog with embeddings for semantic matching (vendor descriptions, services) - though simple filtering may suffice initially.
  The RAG retrieval returns relevant context to the agent to inform plan generation.

- Generated plans are stored in the database (Neon Postgres). The storage format could be a JSONB column in an `event_plans` table, or normalized relational tables (Timeline, Budget, etc.). Either way, they're persisted and versioned.

- The frontend portal (`packages/user`) provides UI for: triggering plan generation, displaying the plan in a readable format, editing fields inline or via forms, exporting to PDF (using a library like Puppeteer or browser print-to-PDF), and generating shareable links.

- Users have authentication (`002-user-auth`) and ownership of events. Plans are only accessible to event owner and authorized admins.

- Budget field on Event is optional but should be provided for meaningful budget breakdown. If missing, AI asks user for budget or assumes a default based on event type and guest count (assumption: weddings 500K PKR for 150 guests, adjust proportionally).

- Vendor recommendations are not real-time availability checks; they are suggestions based on vendor profile data. Actual availability and booking must be handled separately (Booking feature). Recommendations may stale if vendor data changes; plan may include a "last updated" timestamp.

- The AI generates plans using LLM (Gemini) and must be instructed to output structured JSON matching the plan schema. The LLM call is wrapped in a tool function that returns the plan object.

- The system provides a user feedback mechanism: "Was this plan helpful?" with thumbs up/down. Feedback is stored in `plan_feedback` table and used to fine-tune prompts or train evaluation models later.

- Error handling: If the AI fails to generate a plan (timeout, malformed output), the system retries once; if still fails, returns error to user and suggests trying again or using manual plan creation.

- Export to PDF uses a server-side rendering approach or client-side print. In either case, the exported document is static and reflects the plan at export time. Future versions may add watermark or version control on exported docs.

- Shareable links are time-limited (e.g., valid for 30 days unless extended) and view-only. They are implemented via signed tokens or temporary public records.

- The system does not currently integrate with calendar applications (Google Calendar, Outlook) but could in future. Plan includes timeline dates; users can manually add to calendar.

- RAG knowledge base includes wedding-specific timelines for Pakistani context (e.g., pre-wedding events like mehndi, baraat, walima) and corporate event norms. The AI tailors timeline accordingly based on event type.

- The AI respects constraints: if budget is very low, it may recommend cost-saving measures or note where compromises may be needed.

- Multi-language: Plans generated in English; frontend may offer Urdu translation later. Out of scope for MVP.

- The AI may occasionally produce inaccurate vendor recommendations (hallucinate vendor details not in database). To mitigate, the tool that fetches vendor data should be authoritative: the plan's vendor recommendations are pulled from actual vendor IDs from the marketplace, not free-form LLM text. The LLM may describe, but the IDs are real.

- Data retention: Event plans are retained as long as the event exists. Deleted events may have plans soft-deleted as well.

- The system scales: generating a plan consumes LLM API call and some background processing; rate limiting (e.g., 5 plans per day per user) may be applied to manage costs.
