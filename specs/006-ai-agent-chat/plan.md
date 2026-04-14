# Implementation Plan: AI Agent Chat

**Branch**: `feature/ai-agent-chat` | **Date**: 2026-04-07 | **Spec**: [spec.md](file:///home/ali/Desktop/Event-AI-Latest/specs/006-ai-agent-chat/spec.md)
**Input**: Feature specification from `/specs/006-ai-agent-chat/spec.md`

## Summary

Implements the full AI agent chat pipeline: TriageAgent → EventPlannerAgent → VendorDiscoveryAgent → BookingAgent. Uses OpenAI Agents SDK for orchestration (NOT LangChain for orchestration), SSE streaming via `sse-starlette`, Mem0 for cross-session memory, and FastAPI with `@asynccontextmanager` lifespan for resource management. All tools are decorated with `@function_tool` and return JSON strings.

## Technical Context

**Language/Version**: Python ≥ 3.12 (AI Service), Node.js ≥ 20 (Backend proxy)
**Primary Dependencies**: FastAPI, OpenAI Agents SDK, Mem0, httpx, sse-starlette, SQLModel
**Storage**: Neon DB via asyncpg + SQLModel
**Testing**: pytest-asyncio + respx (zero LLM API calls in tests)
**Performance Goals**: First token < 3s streaming; single-tool response < 10s
**Constraints**: No `sys.path.insert`, no `nest_asyncio`, no `load_dotenv` hacks, no LangChain for orchestration
**Scale/Scope**: Core AI feature — primary user-facing differentiator.

## Constitution Check

- [x] **Agent Architecture (§VII)**: TriageAgent sole entry point, SRP per agent, `@function_tool` for all external calls.
- [x] **FastAPI Best Practices (§VII.9-15)**: Lifespan `@asynccontextmanager`, `Depends()` for DI, Pydantic `BaseSettings` + `@lru_cache`.
- [x] **No Banned Practices**: No `sys.path.insert`, no `nest_asyncio`, no `os.environ.get`, no `Runner.run_sync()`.
- [x] **Zero LLM calls in tests (§V)**: All tests use `respx` to mock HTTP LLM endpoints.

## Project Structure

```text
packages/agentic_event_orchestrator/
├── config/
│   └── settings.py               # Pydantic BaseSettings + @lru_cache
├── services/
│   ├── dependencies.py           # Depends() factories for session, http_client
│   └── memory.py                 # Mem0 integration
├── agents/
│   ├── triage.py                 # TriageAgent — sole entry point
│   ├── event_planner.py          # EventPlannerAgent
│   ├── vendor_discovery.py       # VendorDiscoveryAgent
│   └── booking.py                # BookingAgent
├── tools/
│   ├── vendor_tools.py           # search_vendors, get_vendor_details
│   ├── booking_tools.py          # create_booking_request, get_booking_status
│   ├── event_tools.py            # get_user_events, save_event_details
│   └── __tests__/
│       ├── test_vendor_tools.py
│       └── test_booking_tools.py
├── routers/
│   └── chat.py                   # /api/v1/ai/chat and /chat/stream
└── main.py                       # FastAPI app with lifespan
```

## Phase 1: Lifespan & Configuration

**Tasks**:
1. Implement `settings.py` with `BaseSettings` + `@lru_cache` for all env vars (DB URL, Gemini API key, Mem0 config).
2. Implement `main.py` with `@asynccontextmanager` lifespan initializing `async_engine`, `async_sessionmaker`, `httpx.AsyncClient`, and Gemini `AsyncOpenAI` client.
3. Implement `dependencies.py` with `Depends()` factories: `get_session`, `get_http_client`, `get_llm_client`.

## Phase 2: Agent Pipeline

**Tasks**:
1. Define `TriageAgent` with instructions for intent classification and handoff routing.
2. Define `EventPlannerAgent` with tools: `get_user_events`, `save_event_details`, `query_event_types`.
3. Define `VendorDiscoveryAgent` with tools: `search_vendors`, `get_vendor_details`.
4. Define `BookingAgent` with tools: `create_booking_request`, `get_booking_status`.
5. Each agent: single responsibility, < 50 lines of instructions, clear refusal patterns, security rules.
6. Wire handoffs: Triage → Planner/VendorDiscovery/Booking, with back-handoff to Triage.

## Phase 3: Tool Functions

**Tasks**:
1. All tools use `@function_tool` decorator with clear docstrings.
2. Input validation via Pydantic models, return `str` (JSON serialized).
3. Tools call backend REST API via `httpx.AsyncClient` with JWT auth, never access DB directly.
4. Graceful error handling: return descriptive error strings, never raise unhandled exceptions.

## Phase 4: Chat Endpoints & SSE

**Tasks**:
1. `POST /api/v1/ai/chat` — non-streaming endpoint using `Runner.run()`.
2. `POST /api/v1/ai/chat/stream` — streaming via `EventSourceResponse` + `Runner.run_streamed()`.
3. Persist every message to `chat_sessions` and `messages` tables with `agent_name` metadata.
4. Apply rate limiting: 30 req/min per user.
5. Backend proxy: mount AI endpoints under `/api/v1/ai/` in Fastify, proxying to FastAPI.

## Phase 5: Memory & Personalization

**Tasks**:
1. Integrate Mem0 for cross-session memory keyed by `user_id`.
2. On conversation start, retrieve user memory and inject into agent context.
3. After conversation, update memory with new preferences and facts.
4. Support `right-to-forget`: API endpoint to clear user memory.

## Phase 6: Testing

**Tasks**:
1. Tool tests: `pytest-asyncio` + `respx` mocking backend HTTP. Zero LLM API calls.
2. Agent integration tests: mock LLM responses, verify handoff chain.
3. Endpoint tests: `httpx` with `ASGITransport` for chat and stream endpoints.
4. Minimum 70% coverage on tools, integration tests for agent flows.
