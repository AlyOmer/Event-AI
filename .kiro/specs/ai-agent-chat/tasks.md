# Tasks — AI Agent Chat System

## Task List

- [x] 1. Configuration and Lifespan Refactor
  - [x] 1.1 Create `config/settings.py` with `BaseSettings` + `@lru_cache` including all required fields: `database_url`, `gemini_api_key`, `gemini_base_url`, `gemini_model`, `mem0_api_key`, `ai_service_api_key`, `cors_origins`, `rate_limit_per_minute`, `session_ttl_days`, `max_handoff_depth`, `max_response_chars`
  - [x] 1.2 Create `config/dependencies.py` with `Depends()`-compatible async generators: `get_session`, `get_http_client`, `get_llm_client`, `get_run_config`, `get_settings`
  - [x] 1.3 Rewrite `main.py` with `@asynccontextmanager` lifespan that initialises `async_engine`, `async_sessionmaker`, `httpx.AsyncClient`, `AsyncOpenAI` (Gemini-compatible), `OpenAIChatCompletionsModel`, and `RunConfig(tracing_disabled=True)` on `app.state`
  - [x] 1.4 Remove all `sys.path.insert`, `nest_asyncio.apply()`, `load_dotenv`, and `Runner.run_sync()` calls from production modules (keep `server.py` as deprecated reference only)
  - [x] 1.5 Register all routers in `main.py` with correct prefixes and CORS middleware restricted to `settings.cors_origins`

- [x] 2. Database Models and Migration
  - [x] 2.1 Create `models/chat_session.py` with `ChatSession` SQLModel table (`id`, `user_id`, `started_at`, `last_activity_at`, `status`, `active_agent`, `metadata`) in `ai` schema
  - [x] 2.2 Create `models/message.py` with `Message` SQLModel table (`id`, `session_id`, `sequence`, `role`, `content`, `created_at`, `agent_name`, `tool_calls`, `token_count`, `latency_ms`) in `ai` schema
  - [x] 2.3 Create `models/agent_execution.py` with `AgentExecution` SQLModel table (`id`, `session_id`, `message_id`, `agent_name`, `started_at`, `ended_at`, `status`, `tokens_used`, `error`) in `ai` schema
  - [x] 2.4 Create `models/message_feedback.py` with `MessageFeedback` SQLModel table (`id`, `message_id`, `user_id`, `rating`, `comment`, `created_at`) in `ai` schema
  - [x] 2.5 Create Alembic migration `alembic/versions/xxxx_add_ai_chat_tables.py` that creates the `ai` schema and all four tables with indexes on `user_id`, `session_id`, and `created_at`
  - [x] 2.6 Implement reversible `downgrade()` that drops all four tables and the `ai` schema
  - [x] 2.7 Import all new models in `alembic/env.py` so autogenerate detects them

- [x] 3. ChatService
  - [x] 3.1 Create `services/chat_service.py` with `ChatService` class
  - [x] 3.2 Implement `get_or_create_session(session, user_id, session_id) -> ChatSession` — reuses existing active session if valid, creates new one otherwise
  - [x] 3.3 Implement `save_turn(session, chat_session, user_content, assistant_content, agent_name, latency_ms) -> tuple[Message, Message]` — persists user + assistant messages with auto-incrementing sequence
  - [x] 3.4 Implement `expire_old_sessions(session, ttl_days)` — sets `status=expired` for sessions with `last_activity_at` older than `ttl_days`
  - [x] 3.5 Implement `get_session_messages(session, session_id, limit=50) -> list[Message]` for history injection

- [x] 4. MemoryService
  - [x] 4.1 Create `services/memory_service.py` with `MemoryService` class using Mem0 Python SDK
  - [x] 4.2 Implement `get_user_memory(user_id: str) -> str` — returns last 10 memory entries as a formatted string; returns empty string if Mem0 unavailable (graceful degradation)
  - [x] 4.3 Implement `update_user_memory(user_id: str, messages: list[dict]) -> None` — adds conversation to Mem0; silently skips if unavailable
  - [x] 4.4 Implement `delete_user_memory(user_id: str) -> None` — deletes all memory for a user (right-to-forget)

- [x] 5. GuardrailService Refactor
  - [x] 5.1 Create `services/guardrail_service.py` with `GuardrailService` class wrapping the logic from `guardrails.py`
  - [x] 5.2 Implement `run_input_pipeline(message, user_id, settings) -> GuardrailResult` executing: rate limit → input length check → firewall → topic scope check
  - [x] 5.3 Implement `filter_output(text, max_chars) -> str` with PII redaction (email, phone, CNIC patterns) and length cap
  - [x] 5.4 Implement `audit(event_type, session_id, user_id, metadata)` — structured JSON audit log with append-only semantics
  - [x] 5.5 Ensure `GuardrailResult` dataclass has fields: `blocked: bool`, `message: str`, `reason: str`

- [x] 5b. Prompt Injection Firewall (LlamaFirewall)
  - [x] 5b.1 Add `llamafirewall` to `pyproject.toml` dependencies
  - [x] 5b.2 Create `services/prompt_firewall.py` with `PromptFirewall` class and `FirewallResult` dataclass
  - [x] 5b.3 Implement Layer 1: LlamaFirewall `PromptGuard 2` scanner — initialise in lifespan, block if `result.score >= settings.promptguard_threshold`; gracefully fall back to Layer 2 if LlamaFirewall unavailable
  - [x] 5b.4 Implement Layer 2: compiled regex matching for all 6 threat categories (`DIRECT_INJECTION`, `SYSTEM_PROMPT_EXTRACTION`, `ROLE_ESCALATION`, `INDIRECT_INJECTION`, `CONTEXT_OVERFLOW`, `TOOL_ABUSE`)
  - [x] 5b.5 Implement Layer 3: heuristic scoring — special char density >30%, token repetition ratio >50%, base64 blob detection, Unicode homoglyph detection, zero-width character detection
  - [x] 5b.6 Implement `sanitize(message: str) -> str` — strips zero-width chars, normalizes Unicode to NFC, collapses runs of >3 identical chars, trims to 2000 chars
  - [x] 5b.7 Create `data/injection_blocklist.yaml` with initial blocklist of direct injection phrases, system prompt extraction phrases, and role escalation phrases
  - [x] 5b.8 Add `promptguard_threshold`, `alignment_threshold`, `injection_blocklist_path`, `max_input_chars` fields to `Settings`
  - [x] 5b.9 Ensure `classify()` never raises an exception for any input — wrap all layers in try/except with fail-safe `blocked=True` default

- [x] 5c. Sandwich Defense Context Builder
  - [x] 5c.1 Create `services/context_builder.py` with `build_agent_input(message, memory_context, history, canary_token, firewall) -> str`
  - [x] 5c.2 Implement constraints preamble with canary token injection (canary generated at lifespan startup, stored on `app.state.canary_token`)
  - [x] 5c.3 Implement MINJA defense: re-sanitize each history turn through `firewall.sanitize()` before inclusion, treating stored history as untrusted
  - [x] 5c.4 Wrap user message with unique delimiters `[USER_MSG_7f3a9b]` / `[/USER_MSG_7f3a9b]` that do not appear in any agent instruction
  - [x] 5c.5 Append constraints reminder after user message (the "sandwich" closing)
  - [x] 5c.6 Generate canary token (UUID) in lifespan and store on `app.state.canary_token` — never in `.env` or any file

- [x] 5d. Output Leak Detector
  - [x] 5d.1 Create `services/output_leak_detector.py` with `OutputLeakDetector` class and `LeakScanResult` dataclass
  - [x] 5d.2 Implement canary token detection — if canary appears in response, return `SAFE_FALLBACK` and log `CRITICAL` audit event
  - [x] 5d.3 Implement stack trace detection — detect `Traceback (most recent`, `File "/`, patterns
  - [x] 5d.4 Implement internal tool name detection — scan for `create_booking_request`, `search_vendors`, `guardrail_service`, etc.
  - [x] 5d.5 Implement `scan_stream_buffer(buffer: str) -> bool` for fast canary check on first 500 chars of SSE stream
  - [x] 5d.6 Store agent instruction fragments as SHA-256 hashes (not plaintext) for leak detection
  - [x] 5d.7 Integrate `OutputLeakDetector` into both streaming and non-streaming chat endpoints — scan before returning any response to client

- [-] 5e. Agent Instruction Hardening + AlignmentCheck
  - [ ] 5e.1 Create `agents/instructions.py` with all agent instruction strings as module-level constants (not inline)
  - [ ] 5e.2 Add `SECURITY_PREAMBLE` constant to every agent instruction: cannot-override statement, never-reveal-instructions rule, never-reveal-agent-names rule
  - [ ] 5e.3 Add explicit injection trigger phrase list to `TriageAgent` instructions (synced from firewall blocklist)
  - [ ] 5e.4 Ensure each agent instruction is ≤800 tokens — verify with a startup assertion
  - [ ] 5e.5 Integrate LlamaFirewall `AlignmentCheck` as a per-handoff validator — after each agent handoff, check that the receiving agent's planned action is aligned with original user intent; abort handoff if drift score ≥ `settings.alignment_threshold`
  - [ ] 5e.6 Integrate LlamaFirewall `CodeShield` — scan any agent response containing code blocks for SQL injection, string-concatenated queries, and insecure patterns before returning to user
  - [ ] 5e.7 Create `routers/admin_guardrails.py` with `POST /api/v1/admin/guardrails/test` — runs standard injection probe battery against live pipeline, returns pass/fail per probe; requires admin JWT

- [ ] 5f. TruLens RAG Faithfulness Evaluation
  - [ ] 5f.1 Add `trulens-core` and `trulens-apps-custom` to `pyproject.toml` dependencies
  - [ ] 5f.2 Create `services/trulens_evaluator.py` with `TruLensEvaluator` class
  - [ ] 5f.3 Implement `evaluate_rag_response(query, context, response, session_id, message_id) -> dict | None` — evaluates RAG Triad (context relevance, groundedness, answer relevance) asynchronously
  - [ ] 5f.4 Add `trulens_enabled: bool` and `trulens_groundedness_threshold: float` to `Settings`
  - [ ] 5f.5 Integrate TruLens evaluation as a `BackgroundTask` in the VendorDiscoveryAgent response path — does not block user response
  - [ ] 5f.6 Log `HALLUCINATION_RISK` audit event when groundedness < `settings.trulens_groundedness_threshold`
  - [ ] 5f.7 Store TruLens scores in `agent_executions.metadata` JSONB column
  - [ ] 5f.8 Add `GET /api/v1/admin/chat/faithfulness` endpoint returning aggregate TruLens scores per agent

- [ ] 5g. CI Security Testing (Promptfoo + Garak)
  - [ ] 5g.1 Create `promptfoo.config.yaml` with ≥20 adversarial prompts covering all 6 injection threat categories
  - [ ] 5g.2 Add `promptfoo eval` step to CI pipeline — fails build if any injection probe receives a non-blocked response
  - [ ] 5g.3 Create `.garak.yaml` configuration for weekly red-team runs covering: prompt injection, jailbreak, data extraction, role escalation probes
  - [ ] 5g.4 Add `garak` as a dev dependency in `pyproject.toml`
  - [ ] 5g.5 Configure both Promptfoo and Garak to run against local test instance with mocked backend — zero real Gemini API calls

- [x] 6. Agent Tools Refactor
  - [x] 6.1 Refactor `tools/vendor_tools.py` — rewrite `search_vendors`, `get_vendor_details`, `get_vendor_recommendations` as `@function_tool` async functions with Pydantic input models; all call backend REST API via injected `httpx.AsyncClient`; all return JSON strings
  - [x] 6.2 Refactor `tools/booking_tools.py` — rewrite `create_booking_request`, `get_my_bookings`, `get_booking_details`, `cancel_booking` as `@function_tool` async functions; `create_booking_request` includes idempotency key; all return JSON strings
  - [x] 6.3 Refactor `tools/event_tools.py` — rewrite `get_user_events`, `create_event`, `get_event_details`, `update_event_status`, `query_event_types` as `@function_tool` async functions; all return JSON strings
  - [x] 6.4 Remove all direct database access from tools — tools MUST call backend REST API only
  - [x] 6.5 Remove `set_session_context`, `mark_session_confirmed`, `clear_session_confirmed`, `is_session_confirmed` from `booking_tools.py` — confirmation is now handled by `BookingAgent` instructions

- [x] 7. Agent Pipeline Refactor
  - [x] 7.1 Create `agents/triage.py` with `TriageAgent` — sole entry point, scope enforcement, routing rules, injection detection, handoff depth guard; handoffs to `EventPlannerAgent`, `VendorDiscoveryAgent`, `BookingAgent`, `OrchestratorAgent`
  - [x] 7.2 Create `agents/event_planner.py` with `EventPlannerAgent` — tools: `get_user_events`, `create_event`, `get_event_details`, `update_event_status`, `query_event_types`; handoff to `VendorDiscoveryAgent` after event creation
  - [x] 7.3 Create `agents/vendor_discovery.py` with `VendorDiscoveryAgent` — tools: `search_vendors`, `get_vendor_details`, `get_vendor_recommendations`; handoff to `BookingAgent` on booking intent
  - [x] 7.4 Create `agents/booking.py` with `BookingAgent` — tools: `create_booking_request`, `get_my_bookings`, `get_booking_details`, `cancel_booking`; mandatory confirmation workflow in instructions
  - [x] 7.5 Create `agents/orchestrator.py` with `OrchestratorAgent` — coordinates multi-step flows; handoffs to all specialist agents
  - [x] 7.6 Create `agents/__init__.py` exporting `triage_agent` as the single public entry point
  - [x] 7.7 Remove `sdk_agents.py` module-level side effects (`nest_asyncio`, `sys.path.insert`, `load_dotenv`) — move agent definitions to individual files

- [x] 8. Non-Streaming Chat Endpoint
  - [x] 8.1 Create `routers/chat.py` with `POST /api/v1/ai/chat` endpoint
  - [x] 8.2 Implement full guardrail pipeline call: `guardrail_service.run_input_pipeline` before agent execution
  - [x] 8.3 Implement session management: call `chat_service.get_or_create_session` and inject Mem0 memory context
  - [x] 8.4 Run `Runner.run(triage_agent, agent_input)` with the assembled context
  - [x] 8.5 Apply output filter: `guardrail_service.filter_output(result.final_output)`
  - [x] 8.6 Persist turn: call `chat_service.save_turn` with user message, assistant response, agent name, and latency
  - [x] 8.7 Return `{"success": true, "data": {"response": str, "agent": str, "session_id": str, "guardrail_triggered": bool}}`
  - [x] 8.8 Handle errors: catch all exceptions, return HTTP 500 `AGENT_ERROR` with user-friendly message, log full traceback

- [x] 9. Streaming Chat Endpoint (SSE)
  - [x] 9.1 Add `POST /api/v1/ai/chat/stream` to `routers/chat.py` using `sse-starlette`'s `EventSourceResponse`
  - [x] 9.2 Implement async generator that calls `Runner.run_streamed(triage_agent, agent_input)` and yields each token as `data: {"token": str, "agent": str}`
  - [x] 9.3 Detect client disconnect via `await request.is_disconnected()` and break the generator loop
  - [x] 9.4 Emit final SSE event `{"done": true, "session_id": str, "agent": str}` after stream completes
  - [x] 9.5 Persist the assembled full response to `messages` table after stream finishes
  - [x] 9.6 Apply same guardrail pipeline and rate limiting as non-streaming endpoint

- [x] 10. Feedback and Memory Endpoints
  - [x] 10.1 Create `routers/feedback.py` with `POST /api/v1/ai/feedback` — validates `message_id` belongs to authenticated user's session, stores `MessageFeedback` row
  - [x] 10.2 Create `routers/memory.py` with `DELETE /api/v1/ai/memory/{user_id}` — JWT auth, user can only delete their own memory, calls `memory_service.delete_user_memory`

- [x] 11. Admin Chat Endpoints
  - [x] 11.1 Create `routers/admin_chat.py` with `GET /api/v1/admin/chat/sessions` — paginated list of `ChatSession` records with `user_id` hashed; requires admin JWT; supports filtering by `status`, `date_range`
  - [x] 11.2 Add `GET /api/v1/admin/chat/sessions/{session_id}/messages` — returns all messages for a session; requires admin JWT
  - [x] 11.3 Add `GET /api/v1/admin/chat/feedback/stats` — aggregate feedback stats per agent
  - [x] 11.4 Return HTTP 403 `AUTH_FORBIDDEN` for non-admin callers on all admin endpoints

- [x] 12. Frontend — SSE Streaming Integration
  - [x] 12.1 Create `packages/user/src/app/api/ai/[...path]/route.ts` — Next.js API proxy that forwards requests to `AI_SERVICE_URL` and passes through SSE streams
  - [x] 12.2 Update `packages/user/src/app/chat/page.tsx` — replace `fetch("/api/chat")` with streaming `fetch("/api/ai/chat/stream")` using `ReadableStream` reader
  - [x] 12.3 Implement token-by-token rendering: maintain a partial message in state and append each token as it arrives
  - [x] 12.4 Update agent badge to reflect the current streaming agent (from `payload.agent` in SSE events)
  - [x] 12.5 Add thumbs up/down feedback buttons on each assistant message bubble; POST to `/api/ai/feedback` on click
  - [x] 12.6 Add error handling for SSE connection drops — display error message with retry button
  - [x] 12.7 Persist `session_id` from the final SSE `done` event to `localStorage` for conversation continuity

- [ ] 13. Unit Tests — Tools
  - [ ] 13.1 Write unit tests for `search_vendors` using `respx` to mock backend `GET /api/v1/public_vendors/search` — test happy path, empty results, and HTTP error
  - [ ] 13.2 Write unit tests for `create_booking_request` using `respx` — test happy path, validation error, and idempotency key
  - [ ] 13.3 Write unit tests for `get_user_events` and `create_event` using `respx`
  - [ ] 13.4 Write property-based test (Hypothesis) verifying all tool functions return valid JSON strings for any valid input

- [ ] 14. Unit Tests — GuardrailService and Firewall
  - [ ] 14.1 Write unit tests for injection detection — verify known injection patterns are blocked
  - [ ] 14.2 Write unit tests for topic scope check — verify off-topic messages are redirected
  - [ ] 14.3 Write unit tests for PII redaction — verify email, phone, and CNIC patterns are redacted from output
  - [ ] 14.4 Write property-based test (Hypothesis) verifying `run_input_pipeline` always returns a non-empty `GuardrailResult.message` for any valid UTF-8 input
  - [ ] 14.5 Write unit test for rate limiter — verify the 31st request within 60 seconds is rejected with HTTP 429
  - [ ] 14.6 Write `tests/unit/test_prompt_firewall.py` — unit tests for all 6 threat categories with at least 3 example inputs each; test LlamaFirewall PromptGuard 2 path with mocked `llamafirewall` module; test graceful fallback when LlamaFirewall unavailable
  - [ ] 14.7 Write property-based test (Hypothesis) verifying `PromptFirewall.classify()` never raises an exception for any `st.text()` input
  - [ ] 14.8 Write unit tests for `PromptFirewall.sanitize()` — verify zero-width char removal, Unicode NFC normalization, char run collapsing, and 2000-char trim
  - [ ] 14.9 Write `tests/unit/test_context_builder.py` — property-based test verifying sandwich structure: user content always between delimiters, constraints preamble before, constraints reminder after
  - [ ] 14.10 Write unit test for MINJA defense — verify that a history turn containing an injection phrase is sanitized before inclusion in agent context
  - [ ] 14.11 Write `tests/unit/test_output_leak_detector.py` — unit tests for canary token detection, stack trace detection, internal tool name detection; verify `SAFE_FALLBACK` is returned for each
  - [ ] 14.12 Write property-based test verifying `OutputLeakDetector.scan()` always returns a non-empty `safe_response` for any string input
  - [ ] 14.13 Write `tests/unit/test_trulens_evaluator.py` — mock TruLens session, verify `HALLUCINATION_RISK` audit event is logged when groundedness < threshold; verify graceful degradation when TruLens unavailable
  - [ ] 14.14 Write unit test for AlignmentCheck integration — mock LlamaFirewall drift detection result, verify handoff is aborted and safe fallback returned when drift score ≥ threshold

- [ ] 15. Integration Tests — Chat Endpoints
  - [ ] 15.1 Write integration test for `POST /api/v1/ai/chat` happy path using `httpx.AsyncClient` with `ASGITransport` and `respx` to mock Gemini LLM responses
  - [ ] 15.2 Write integration test for `POST /api/v1/ai/chat` with rate limit exceeded → HTTP 429
  - [ ] 15.3 Write integration test for `POST /api/v1/ai/chat` with each injection threat category → guardrail triggered, safe redirect returned
  - [ ] 15.4 Write integration test for `POST /api/v1/ai/chat/stream` — verify SSE events are emitted in correct format (`data: {...}` lines) and final `done` event is present
  - [ ] 15.5 Write integration test for stream where mocked Gemini response contains canary token — verify stream is terminated and `SAFE_FALLBACK` is sent instead
  - [ ] 15.6 Write integration test for stream disconnect — verify generator terminates cleanly when client disconnects
  - [ ] 15.7 Write integration test for `ChatService.save_turn` idempotency — calling twice with same content results in exactly one message pair

- [ ] 16. Integration Tests — Admin and Feedback Endpoints
  - [ ] 16.1 Write integration test for `GET /api/v1/admin/chat/sessions` with valid admin JWT → returns paginated sessions
  - [ ] 16.2 Write integration test for admin endpoint with non-admin JWT → HTTP 403
  - [ ] 16.3 Write integration test for `POST /api/v1/ai/feedback` — happy path and unauthorized access to another user's message

- [ ] 17. Dependency Wiring and Smoke Test
  - [ ] 17.1 Verify `sse-starlette` is added to `pyproject.toml` dependencies
  - [ ] 17.2 Verify `mem0ai` is added to `pyproject.toml` dependencies
  - [ ] 17.3 Verify `hypothesis` is added to `pyproject.toml` dev dependencies
  - [ ] 17.4 Verify `pyyaml` is added to `pyproject.toml` dependencies (for blocklist loading)
  - [ ] 17.5 Verify `llamafirewall` is added to `pyproject.toml` dependencies
  - [ ] 17.6 Verify `trulens-core` and `trulens-apps-custom` are added to `pyproject.toml` dependencies
  - [ ] 17.7 Verify `promptfoo` and `garak` are added to `pyproject.toml` dev dependencies
  - [ ] 17.8 Initialise `PromptFirewall` (with LlamaFirewall), `OutputLeakDetector`, `ContextBuilder`, and `TruLensEvaluator` in lifespan and store on `app.state`; generate canary token UUID at startup
  - [ ] 17.9 Run `uv run pytest` and confirm all tests pass with zero real Gemini or backend API calls
  - [ ] 17.10 Run `uv run alembic upgrade head` against a test DB branch and confirm migration applies cleanly
  - [ ] 17.11 Run `uv run promptfoo eval` and confirm all ≥20 adversarial probes are blocked
  - [ ] 17.12 Manually verify the chat page streams responses in the browser with the updated frontend
