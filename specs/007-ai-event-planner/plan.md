# Implementation Plan: AI Event Planner

**Branch**: `feature/ai-event-planner` | **Date**: 2026-04-07 | **Spec**: [spec.md](file:///home/ali/Desktop/Event-AI-Latest/specs/007-ai-event-planner/spec.md)
**Input**: Feature specification from `/specs/007-ai-event-planner/spec.md`

## Summary

Implements automatic event plan generation using the EventPlannerAgent with RAG-powered retrieval of domain knowledge (wedding timelines, budget allocation models, Pakistan-specific event customs). Plans are stored as versioned JSONB in Postgres, include timeline milestones, budget breakdowns, vendor recommendations from the marketplace, and task checklists. Users can edit, version, and export plans as PDF.

## Technical Context

**Language/Version**: Python ≥ 3.12 (AI Service), Node.js ≥ 20 (Backend)
**Primary Dependencies**: FastAPI, OpenAI Agents SDK, LangChain (RAG only), pgvector, Prisma
**Storage**: Neon DB (PostgreSQL) with pgvector for semantic retrieval
**Testing**: pytest-asyncio + respx (AI), Jest + Supertest (Backend)
**Performance Goals**: Plan generation < 30s; vendor queries < 200ms
**Constraints**: LangChain for RAG retrieval ONLY — NOT for agent orchestration. Zero LLM API calls in tests.

## Constitution Check

- [x] **Agent Architecture (§VII)**: EventPlannerAgent is a specialist with SRP, reached only via TriageAgent handoff.
- [x] **RAG Architecture (§VII.1-4)**: LangChain for document processing/retrieval; OpenAI Agents SDK for orchestration.
- [x] **API → Function → Tool (§VII.12)**: Business logic in pure functions, `@function_tool` wrappers for agents.
- [x] **Async-first (§VII.15)**: All endpoints `async def`, DB sessions via `yield`.

## Project Structure

```text
packages/agentic_event_orchestrator/
├── agents/
│   └── event_planner.py           # EventPlannerAgent definition
├── tools/
│   ├── event_tools.py             # get_user_events, save_event_plan
│   ├── vendor_tools.py            # search_vendors (reused from 006)
│   └── rag_tools.py               # [NEW] query_planning_knowledge
├── rag/
│   ├── knowledge_loader.py        # [NEW] LangChain doc loader + chunker
│   └── retriever.py               # [NEW] pgvector similarity search

packages/backend/
├── src/
│   ├── routes/
│   │   └── event-plans.routes.ts  # [NEW] CRUD + export endpoints
│   └── __tests__/
│       └── event-plans.test.ts    # [NEW] Route tests
```

## Phase 1: RAG Knowledge Base

**Tasks**:
1. Create domain knowledge documents (wedding/corporate event timelines, budget allocation models, Pakistan-specific customs).
2. Implement `knowledge_loader.py` using LangChain: load markdown docs, chunk with `RecursiveCharacterTextSplitter`.
3. Generate embeddings and store in pgvector via Neon DB.
4. Implement `retriever.py`: similarity search against embedded knowledge.

## Phase 2: Plan Generation Tool

**Tasks**:
1. Implement `generate_event_plan()` business logic function: accepts event details, queries RAG for context, calls LLM to produce structured plan JSON.
2. Wrap as `@function_tool` for EventPlannerAgent.
3. Plan schema: `{ timeline: Milestone[], budget: BudgetCategory[], vendors: VendorRecommendation[], tasks: PlanTask[] }`.
4. Vendor recommendations pulled from real marketplace data via `search_vendors` tool (real IDs, not hallucinated).

## Phase 3: Backend Plan Storage & API

**Tasks**:
1. Add `EventPlan` model to Prisma: `id`, `eventId`, `version`, `content` (JSONB), `generationMethod`, `status`, `createdBy`, timestamps.
2. Routes: `POST /api/v1/events/:id/plans/generate`, `GET /api/v1/events/:id/plans`, `PATCH /api/v1/events/:id/plans/:planId`, `GET /api/v1/events/:id/plans/:planId/export`.
3. Versioning: each save creates new version, previous versions retained.
4. Export: server-side PDF generation or return structured data for client-side rendering.

## Phase 4: Frontend Integration

**Tasks**:
1. React Query hooks: `useEventPlan`, `useGeneratePlan`, `useUpdatePlan`.
2. Plan viewer component: collapsible timeline, budget table, vendor cards, task checklist.
3. Inline editing for each section with auto-save.
4. "Generate Plan" button with loading state and progress indicator.

## Phase 5: Testing

**Tasks**:
1. RAG retrieval tests: verify relevant chunks are returned for known queries.
2. Plan generation tool tests: mock LLM via `respx`, verify output schema compliance.
3. Backend route tests: CRUD operations, versioning, authorization.
4. Budget validation: assert allocations sum to total event budget.
