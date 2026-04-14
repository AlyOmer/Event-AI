# Feature Specification: AI Agent Chat

**Feature Branch**: `006-ai-agent-chat`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "AI Agent Chat    Triage → Planner → Vendor Discovery → Booking agent pipeline"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI-Powered Event Planning Assistant (Priority: P1)

As an event planner (user), I want to chat with an AI assistant that helps me plan my event, so that I can get personalized recommendations, answers to questions, and assistance with vendor selection without spending hours researching.

**Why this priority**: This is the core user-facing AI feature—the primary interaction point where users experience the "AI" in Event-AI. Without a functional chat assistant, the AI service doesn't deliver value. This story covers the end-to-end user journey of conversing with the agent pipeline.

**Independent Test**: Can be fully tested by a user logging into the frontend portal, opening the chat interface, and asking questions like "Help me plan a wedding for 200 guests in Karachi with a budget of 500K PKR." The AI should respond with helpful information, ask clarifying questions, and eventually recommend suitable vendors. The entire conversation should flow naturally with relevant responses.

**Acceptance Scenarios**:

1. **Given** I am a logged-in user, **When** I open the AI chat interface and send my first message, **Then** I receive an initial response from the TriageAgent within 5 seconds (streaming), and the conversation continues with appropriate follow-up questions or suggestions.

2. **Given** I describe my event needs (type, size, budget, location), **When** the AI processes my message, **Then** the TriageAgent hands off to the EventPlannerAgent, who asks clarifying questions about date, style, preferences, and then hands off to VendorDiscoveryAgent to find matching vendors.

3. **Given** the VendorDiscoveryAgent has found vendors, **When** it presents recommendations, **Then** I see vendor names, categories, brief descriptions, and can ask for more details or request to book a vendor.

4. **Given** I express interest in booking a vendor, **When** I confirm details with the AI, **Then** the BookingAgent takes over to assist with initiating a booking request (creating an inquiry or provisional hold), collecting necessary information, and submitting it through the vendor marketplace.

5. **Given** I ask a question outside the platform's scope (e.g., "What's the weather forecast?"), **When** I submit, **Then** the AI politely declines or redirects to relevant platform capabilities, maintaining scope discipline.

6. **Given** I have a multi-turn conversation, **When** I continue chatting, **Then** the AI remembers context from earlier in the conversation and maintains coherent dialogue without requiring repetition.

---

### User Story 2 - Vendor Discovery and Recommendation (Priority: P2)

As an event planner, I want the AI to search the vendor marketplace and recommend vendors that match my event needs, so that I can quickly identify suitable vendors without manually browsing and filtering.

**Why this priority**: Vendor discovery is a key value proposition—the AI should accelerate the vendor matching process. This is a specialized capability of the agent pipeline (VendorDiscoveryAgent). It's P2 because the general chat (P1) must work first, but vendor discovery is a critical sub-feature.

**Independent Test**: Can be tested by a user telling the AI about their event (e.g., "I need a photographer and caterer for a wedding of 150 guests in Lahore, budget 300K"), and the AI returns a shortlist of 5-10 vendors with relevance explanations. The user can then ask for more details about a specific vendor or request to contact them.

**Acceptance Scenarios**:

1. **Given** I have described my event and requirements, **When** the VendorDiscoveryAgent is invoked, **Then** it queries the vendor marketplace (via backend API or direct database access) and returns a list of vendors matching my criteria (event type served, location, availability, ratings).

2. **Given** I receive vendor recommendations, **When** I ask "Tell me more about Photographer X," **Then** the AI provides details from the vendor's profile (services offered, portfolio highlights, reviews, pricing range if available).

3. **Given** the initial vendor list is too broad, **When** I refine my search with additional filters (e.g., "only show vendors with ratings above 4.0"), **Then** the AI re-queries and returns a narrower, more relevant list.

4. **Given** no vendors match my criteria exactly, **When** the AI searches, **Then** it returns the closest matches and suggests adjusting my requirements (e.g., "No photographers available in that area, but here are photographers from nearby cities who travel").

5. **Given** I want to see more options, **When** I request "show more vendors" or "next page," **Then** the AI retrieves and displays additional results beyond the initial batch.

6. **Given** I ask for vendor recommendations in a category not yet supported in my event (e.g., I forgot mention lighting), **When** I ask about lighting vendors, **Then** the AI searches for lighting vendors relevant to my event type and location and presents results.

---

### User Story 3 - Booking Assistance and Inquiry Initiation (Priority: P3)

As an event planner, I want the AI to help me initiate contact with vendors and navigate the booking process, so that I can easily send inquiries or provisional booking requests without leaving the chat interface.

**Why this priority**: This is the action-oriented conclusion of the chat—moving from discovery to commitment. It's P3 because it builds on vendor discovery and depends on the booking/inquiry subsystem being implemented separately. This agent layer orchestrates rather than implements booking.

**Independent Test**: Can be tested by a user, after discussing their event and selecting a vendor, telling the AI "I want to book this vendor." The AI collects necessary information (event date, service type, special requests), confirms details, and submits an inquiry/booking request through the appropriate API. The user receives confirmation and can track the request status.

**Acceptance Scenarios**:

1. **Given** I have selected a vendor I'm interested in, **When** I say "Book this vendor" or "Send an inquiry," **Then** the BookingAgent collects required information (event date, service type, message) and creates a booking request in the system.

2. **Given** the BookingAgent is gathering details, **When** I provide incomplete information, **Then** it asks clarifying follow-up questions until it has all required fields.

3. **Given** I submit a booking request, **When** the operation succeeds, **Then** I receive a confirmation message with request ID and next steps (e.g., "Vendor will respond within 24 hours").

4. **Given** the booking request fails (vendor unavailable, validation error), **When** the AI attempts submission, **Then** it explains the issue and suggests alternatives (e.g., "That date is unavailable, would you like to propose another date?").

5. **Given** I want to modify or cancel a pending booking request, **When** I ask the AI to do so, **Then** the BookingAgent assists with the modification or cancellation, verifying my intent and executing the change.

6. **Given** I ask about the status of my bookings, **When** I inquire "What's the status of my booking with Photographer X?", **Then** the AI retrieves and reports the current status (pending, confirmed, declined) and any relevant details.

---

### User Story 4 - Contextual Memory and Personalized Assistance (Priority: P3)

As a returning user, I want the AI to remember my past events, preferences, and conversation history, so that I don't have to repeat information and can receive personalized recommendations.

**Why this priority**: Personalization significantly improves user experience but is not essential for first-time users. It relies on augmented memory infrastructure (Mem0 or equivalent). It's P3 because memory adds complexity and can be implemented after core chat flows work. It differentiates the platform as "intelligent."

**Independent Test**: Can be tested by a user having a conversation, then returning later (or starting a new conversation) and the AI recognizing them and recalling relevant context (e.g., "Welcome back, Ali! Last time you were planning a wedding, how did that go? Are you planning another event?"). The AI should reference past events, vendor interactions, and stated preferences.

**Acceptance Scenarios**:

1. **Given** I have previously created an event and discussed it with the AI, **When** I start a new conversation, **Then** the AI greets me by name and recalls key details about my last event (type, date, vendors used) without prompting.

2. **Given** I mention a preference during a conversation (e.g., "I prefer outdoor venues"), **When** later in the same or future conversation I ask for venue suggestions, **Then** the AI prioritizes outdoor venues and references my stated preference.

3. **Given** I have multiple events in my history, **When** I say "I'm planning another corporate event," **Then** the AI knows I have past corporate event experience and can reference what vendors I used before.

4. **Given** I correct the AI's mistaken recollection, **When** I provide the correct information, **Then** the AI updates its memory and acknowledges the correction, avoiding repeating the mistake.

5. **Given** I ask "What do you know about me?", **When** I request my stored preferences, **Then** the AI summarizes relevant profile information (event types I've hosted, budget ranges, locations, vendor preferences) that it has remembered from past interactions.

---

### Edge Cases

- What happens when the AI agent pipeline encounters an unexpected error (LLM API failure, timeout, tool exception)? The system should catch errors, log them, and return a user-friendly error message to the user, while potentially retrying or escalating to human support if needed.

- What happens when a user asks malicious or prompt-injection questions trying to extract system prompts, bypass restrictions, or execute unauthorized actions? The AI must detect and refuse such attempts, respond with a safe generic message, and log the incident for security review. The TriageAgent should have clear refusal patterns.

- What happens when the conversation context grows very long (many messages) causing token limit issues? The system should summarize old context or use context-window management techniques (e.g., keep recent messages + summary of earlier) to stay within limits while preserving important information.

- What happens when multiple users are chatting simultaneously and the system hits rate limits or capacity constraints? The AI service must enforce rate limiting (30 requests per minute per user) and queue or reject excess requests with appropriate "try again later" messages. The system should scale horizontally.

- What happens when a user tries to perform an action requiring authorization (e.g., booking on behalf of another user, accessing another user's events)? The AI's tools must enforce authorization checks at the backend API level; the agent should not be able to bypass. If unauthorized, the tool returns an error and the AI informs the user.

- What happens when vendor data is stale or unavailable (vendor no longer active, changed pricing)? The tools querying vendor marketplace should handle "not found" or "inactive" gracefully and inform the user that the vendor is no longer available, possibly suggesting alternatives.

- What happens when the AI generates incorrect information (hallucination)? The system should provide sources or confidence indications where possible (e.g., "Based on your past events...", "I found these vendors..."). Users should have a way to report incorrect information, which feeds into improvement loops.

- What happens when the agent handoff fails (e.g., PlannerAgent cannot complete because of missing data)? The agent should ask the user for the missing information rather than failing. If a tool call fails, the agent should handle it gracefully and either retry, ask for clarification, or escalate.

- What happens when two users try to book the same vendor for the same date/time causing a conflict? The booking system (separate feature) should handle concurrency: first request wins, second is notified of conflict. The AI should communicate this clearly to the user and suggest alternatives.

- What happens when the user's session expires during a long chat? The chat interface should handle authentication gracefully—either maintain session silently if refresh token valid, or prompt user to re-login without losing conversation history (which may be stored server-side).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a chat interface (in the frontend portal) that connects to the AI service via Server-Sent Events (SSE) for streaming responses, allowing users to send messages and receive AI-generated replies in real-time.

- **FR-002**: The system MUST implement a TriageAgent as the sole entry point for user interactions; all user messages are first processed by TriageAgent, which routes to appropriate specialist agents (EventPlannerAgent, VendorDiscoveryAgent, BookingAgent, etc.) via handoffs.

- **FR-003**: The system MUST define clear agent responsibilities:
  - TriageAgent: Classifies user intent and initiates handoff to appropriate specialist.
  - EventPlannerAgent: Helps users plan events, asks clarifying questions about event details, stores event context.
  - VendorDiscoveryAgent: Searches vendor marketplace and recommends vendors based on event needs.
  - BookingAgent: Assists with initiating, modifying, or canceling booking requests.
  - ApprovalAgent (optional): Handles admin approval workflows if integrated.
  - MailAgent (optional): Handles email composition for vendor communications.

- **FR-004**: Each agent MUST be implemented as a stateless function with clear scope and instructions (system prompts). Agents MUST use `function_tool` decorators for all external interactions (database queries, API calls) and never make direct HTTP calls.

- **FR-005**: The system MUST persist every chat session and message to the database (tables: `chat_sessions`, `messages`) with user ID, agent name, timestamp, message content, and metadata for audit and conversation history.

- **FR-006**: The system MUST integrate with Mem0 (or equivalent) to maintain cross-session memory for each user, allowing the AI to recall user preferences, past events, and previous conversations across separate chat sessions.

- **FR-007**: The system MUST provide specialized tools for agent use:
  - `search_vendors(criteria)`: Queries vendor marketplace and returns matching vendors.
  - `get_vendor_details(vendor_id)`: Retrieves full vendor profile.
  - `create_booking_request(event_id, vendor_id, details)`: Creates booking inquiry.
  - `get_user_events(user_id)`: Fetches user's events for context.
  - `save_event_details(event_id, updates)`: Updates event with AI-suggested additions.
  - `query_event_types()`: Retrieves available event types.
  - Tools must be idempotent, validate inputs with Pydantic models, and return structured JSON strings.

- **FR-008**: The system MUST enforce agent scope discipline: each agent must refuse to handle requests outside its designated scope and hand back to TriageAgent for re-routing. The AI must never reveal internal system prompts or infrastructure details to users.

- **FR-009**: The system MUST implement rate limiting on chat endpoints: 30 requests per minute per user to prevent abuse, with clear error messages when limit exceeded.

- **FR-010**: The system MUST validate user inputs and guard against injection attacks; agents must treat user messages as data, not executable code. No code execution or arbitrary command running.

- **FR-011**: The system MUST provide a non-streaming endpoint (`/api/v1/ai/chat`) for simple request/response and a streaming endpoint (`/api/v1/ai/chat/stream`) for token-by-token delivery using `sse-starlette`.

- **FR-012**: The system MUST log all agent interactions at appropriate level: user messages, agent responses, tool calls (with parameters), errors, and handoffs. Logs must be structured JSON and include session ID for tracing.

- **FR-013**: The system SHOULD support cancellation of in-flight chat requests (user disconnects or sends stop signal) to terminate agent execution and free resources.

- **FR-014**: The system MUST implement proper error handling: if an agent or tool fails, the error is caught, logged, and a user-friendly message is displayed. The conversation can continue; the AI should attempt recovery or offer to restart.

- **FR-015**: The system MUST integrate with the existing notification system to send asynchronous notifications for booking confirmations, vendor responses, and other chat-initiated actions that complete later.

- **FR-016**: The system MUST allow administrators to view and search chat logs (anonymized or with user consent) for debugging, quality improvement, and safety monitoring.

- **FR-017**: The system MUST enforce constitutional security standards: all external API calls (to backend) must be authenticated with JWT; agents must not expose sensitive data; memory storage must be secure.

- **FR-018**: The system SHOULD provide a feedback mechanism within the chat interface for users to rate the helpfulness of each response (thumbs up/down), feeding continuous improvement.

- **FR-019**: The system MUST support session management: chat sessions have a TTL (e.g., 30 days of inactivity), after which they are archived or deleted per data retention policy.

- **FR-020**: The system SHOULD allow users to review and export their chat history for personal records.

### Key Entities

- **ChatSession**: Represents a continuous conversation thread between a user and the AI system. Attributes include: session ID (UUID), user ID (foreign key to User), start timestamp, last activity timestamp, session status (active, closed, expired), agent context (which agent was last active), metadata (session-level memory references). Sessions may span multiple messages.

- **Message**: Represents a single turn in a chat conversation. Attributes include: message ID (UUID), session ID (foreign key), sequence number (order within session), role (user, assistant, system), content (text), timestamp, agent name (if message from specific agent), tool calls (JSONB array of tools invoked), token count (for usage tracking), latency (ms to generate). Messages are immutable once stored.

- **AgentExecution**: Represents a recorded agent invocation (handoff) for audit and tracing. Attributes include: execution ID (UUID), session ID, message ID (trigger), agent name, input (user message or previous agent output), start time, end time, status (completed, errored, timeout), tokens used, errors (JSONB). One message may trigger multiple agent executions (handoff chain).

- **ToolCall**: Represents a single tool function invocation by an agent. Attributes include: tool call ID, agent execution ID, tool name, input parameters (JSON), output (JSON or error), execution time (ms), success flag. Tool calls are nested within AgentExecution.

- **UserMemory** (Mem0 entity): Represents persistent augmented memory for a user. Attributes include: user ID (unique), memory entries (JSON array of facts, preferences, event references), last updated timestamp, memory version. Mem0 manages this externally but the system must integrate.

- **VendorRecommendation** (derived): Not a stored entity per se, but the output of VendorDiscoveryAgent tool calls. Contains: vendor IDs, match scores, reasoning snippets. May be logged for analytics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: First-response latency: 90% of user messages receive an initial streaming response (first token) within 3 seconds of submission (measured end-to-end from user send to first token arrival).

- **SC-002**: Conversation quality: 85% of chat turns result in a "helpful" or "relevant" user feedback rating (thumbs up) when solicited (sampled).

- **SC-003**: Agent handoff success: 95% of conversations are successfully routed through the agent pipeline (Triage → appropriate specialist) without getting stuck or misrouted.

- **SC-004**: Vendor discovery accuracy: When users explicitly ask for vendor recommendations, 90% of the top 5 results are relevant (users mark as useful) based on user feedback or subsequent booking.

- **SC-005**: Booking initiation success: 80% of booking requests initiated via the AI chat result in a valid booking inquiry created in the system (not aborted due to missing info or errors).

- **SC-006**: System availability: AI chat endpoints maintain ≥99.5% uptime during business hours (9 AM - 9 PM), with graceful degradation if LLM service unavailable.

- **SC-007**: Error rate: ≤2% of chat conversations encounter unhandled errors that force the user to restart or escalate to human support.

### User Satisfaction

- Users rate AI assistant helpfulness ≥4/5 on average.
- Users report that the AI understands their needs ≥4/5.
- 70% of users who try the chat return for a second conversation within a week (retention).

### Business Impact

- Reduce human support workload by 40% (AI handles routine planning questions).
- Increase vendor booking conversion by 25% (AI assistance guides users to book).
- Improve user engagement: average session duration ≥10 minutes of conversation.
- Accelerate time-to-plan: users complete event planning (including vendor selection) in ≤3 days from first chat, compared to ≤7 days without AI.

## Assumptions

- The AI Agent service is implemented in `packages/agentic_event_orchestrator` as a FastAPI application, following the constitutional technology stack (Python 3.12+, FastAPI, OpenAI Agents SDK, asyncpg).

- The LLM provider is Gemini accessed via OpenAI-compatible endpoint (as per constitution). The system is designed to work with any OpenAI-compatible API.

- The backend APIs for vendor marketplace, events, and bookings exist and are callable from the AI service via REST (with JWT authentication). The agent tools use `httpx.AsyncClient` to call these APIs.

- Mem0 is used for cross-session memory storage. It could be self-hosted or cloud service. User memory is scoped per user and persists across sessions.

- Vendor search tool (`search_vendors`) queries the backend API (or possibly the database directly if allowed by architecture). The tool returns a manageable number of results (e.g., top 20) with sufficient detail for recommendation.

- BookingAgent does not execute payments; it only creates inquiry requests or provisional holds. Payment processing and contract signing are separate features.

- The chat interface exists in the user-facing frontend portal (`packages/user` per constitution) and uses SSE to stream AI responses. Frontend handles message rendering, streaming display, and feedback collection.

- Authentication: Users are already authenticated via `002-user-auth`. JWT tokens are passed from frontend to AI service via Authorization header (Bearer). The AI service validates tokens (or backend validates on its behalf) to ensure user identity.

- Rate limiting is enforced at the API gateway or FastAPI middleware. 30 requests per minute per user is a reasonable default; could be tuned.

- The agent instruction prompts (system prompts) are carefully crafted to enforce scope, use professional tone, follow constitutional principles (no harmful content), and handle edge cases. Prompt engineering is iterative but out of scope for this spec.

- Memory privacy: User memory stored in Mem0 is encrypted at rest and access-controlled. Users can request memory deletion (right to be forgotten), which the system must honor by clearing memory entries.

- The system is monitored for AI errors, abuse, and performance. Logs include session IDs for tracing. Alerting on high error rates or latency spikes is assumed part of observability (not in this spec).

- The AI service runs in a scalable deployment (horizontal scaling possible). FastAPI with async allows many concurrent connections. Resource limits (CPU/memory) are sized appropriately.

- The backend databases (vendor marketplace, events) are the Neon PostgreSQL from `003-database-setup`. The AI service uses SQLModel for its own tables (chat_sessions, messages) in the `ai` schema.

- Notifications for booking confirmations or vendor responses are handled by a separate notification service. The AI triggers these by publishing events or calling notification APIs.

- The chat interface includes a way to provide feedback (thumbs up/down) on individual messages. This feedback is stored and used for model improvement.

- Constitutional anti-patterns are followed: no direct database mutation outside tools, no hardcoded secrets, proper async patterns, structured logging.

- Future agents (ApprovalAgent, MailAgent, SchedulerAgent) may be added later without breaking the existing pipeline. The TriageAgent routing can be extended.

- Data retention: Chat messages and sessions are retained for 30 days of inactivity, then archived for 1 year before deletion, per privacy policy. Memory entries have similar retention.

- The AI must never store or request sensitive personal data (credit cards, SSN, passwords). If users provide such data accidentally, it should be redacted from logs and memory.

- The system should handle multi-language users (English, Urdu, etc.) as the LLM is multilingual. UI may be English-only for MVP.

- The agent pipeline depth is limited (max 5 handoffs) to avoid infinite loops. TriageAgent should detect loops and break out.

- Cost management: LLM API costs are tracked per user/session; the system may enforce usage quotas (e.g., 100 messages per day free, then paywall) but that's business logic not in scope.
