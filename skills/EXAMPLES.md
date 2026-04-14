# Event-AI Subagents: Usage Examples

This document provides practical examples of using the Claude Code skills for the Event-AI marketplace platform.

## 📚 Table of Contents

1. [Building a Complete Feature: Vendor Marketplace](#1-building-a-complete-feature-vendor-marketplace)
2. [API Design & Database](#2-api-design--database)
3. [AI Agent Development](#3-ai-agent-development)
4. [Testing](#4-testing)
5. [Code Review & Security](#5-code-review--security)
6. [Documentation](#6-documentation)
7. [Workflow Orchestration](#7-workflow-orchestration)

---

## 1. Building a Complete Feature: Vendor Marketplace

### Scenario
Add a vendor marketplace where users can search, filter, and book vendors for events.

### Using Orchestrator (Full Workflow)

```bash
/orchestrate \
  --feature="marketplace" \
  --workflow=["spec","plan","tasks","adr","event_model","db_design","api_design","agent_design","tests","code","review","security","docs"] \
  --dry_run=false
```

This will execute all stages sequentially:
1. Review existing `specs/marketplace/spec.md`
2. Generate `plan.md` with architecture
3. Break down into `tasks.md` with test cases
4. Create ADRs for significant decisions
5. Design domain events (vendor.created, vendor.updated, vendor.booked)
6. Design Prisma schema (Vendor, Category, VendorReview, VendorAvailability)
7. Design REST endpoints (`/api/v1/vendors`, `/api/v1/vendors/:id/book`)
8. Design AI agents (VendorDiscoveryAgent, VendorRecommendationAgent)
9. Generate test suite
10. Implement code (TDD red→green)
11. Code review
12. Security audit
13. Generate documentation

---

## 2. API Design & Database

### Design Vendor List Endpoint

```bash
/api-designer \
  --endpoint_name="list_vendors" \
  --method="GET" \
  --purpose="Search vendors with filters: category, city, rating, availability date range, price range" \
  --request_fields='[
    {"name":"category", "type":"String", "required":false, "description":"Filter by vendor category (e.g., \"photographer\", \"caterer\")"},
    {"name":"city", "type":"String", "required":false, "description":"City within Pakistan"},
    {"name":"minRating", "type":"Float", "required":false, "description":"Minimum rating (1-5)"},
    {"name":"eventDate", "type":"String", "required":false, "description":"ISO date for availability check"},
    {"name":"page", "type":"Int", "required":false, "description":"Page number (default 1)"},
    {"name":"limit", "type":"Int", "required":false, "description":"Items per page (max 50, default 20)"}
  ]' \
  --response_fields='[
    {"name":"vendors", "type":"Array<Vendor>", "description":"List of matching vendors"},
    {"name":"total", "type":"Int", "description":"Total count for pagination"},
    {"name":"page", "type":"Int", "description":"Current page"},
    {"name":"pages", "type":"Int", "description":"Total pages"}
  ]' \
  --package="backend"
```

**Output**:
- Route file: `packages/backend/src/routes/vendors.routes.ts`
- Validation schema: `packages/backend/src/validation/vendor.schema.ts`
- Event emissions: none (read-only)
- Rate limiting: 60 req/min (public API)

---

### Design Vendor Entity

```bash
/db-architect \
  --entity_name="Vendor" \
  --purpose="Stores vendor profile, services offered, pricing, and availability" \
  --fields='[
    {"name":"businessName", "type":"String", "required":true, "unique":false, "indexed":true, "description":"Business name"},
    {"name":"category", "type":"VendorCategory", "required":true, "unique":false, "indexed":true, "description":"photographer, caterer, venue, etc."},
    {"name":"city", "type":"String", "required":true, "unique":false, "indexed":true, "description":"City in Pakistan"},
    {"name":"description", "type":"String", "required":false, "unique":false, "indexed":false, "description":"Vendor description"},
    {"name":"priceRange", "type":"Json", "required":false, "unique":false, "indexed":false, "description":"{min, max} in PKR"},
    {"name":"avgRating", "type":"Float", "required":false, "unique":false, "indexed":true, "description":"Average rating (1-5)"},
    {"name":"embedding", "type":"Vector? (1536)", "required":false, "unique":false, "indexed":true, "description":"pgvector embedding for semantic search"}
  ]' \
  --relations='[
    {"type":"one-to-many", "target":"VendorReview", "field":"reviews", "inverseField":"vendor"},
    {"type":"many-to-many", "target":"Category", "field":"categories", "inverseField":"vendors"}
  ]' \
  --indexes='[
    {"fields":["city","category"], "unique":false},
    {"fields":["category","avgRating"], "unique":false},
    {"fields":["embedding"], "unique":false, "notes":"HNSW pgvector index for similarity search"}
  ]'
```

**Output**:
- Prisma model: `packages/backend/prisma/models/Vendor.prisma`
- Migration SQL with indexes
- Notes on embedding column and GIN/HNSW index

---

## 3. AI Agent Development

### Design VendorDiscoveryAgent

```bash
/agent-architect \
  --agent_name="VendorDiscoveryAgent" \
  --responsibility="Find and evaluate vendors matching user event requirements (category, location, date, budget, style). Uses both structured search and semantic similarity." \
  --handoffs=["BookingAgent","ApprovalAgent"] \
  --tools='[
    {"name":"search_vendors", "purpose":"Structured DB search by filters", "parameters":["category:str","city:str","max_price:int","date:date"]},
    {"name":"semantic_search", "purpose":"Find vendors by description/style similarity", "parameters":["query:str","k:int=10"]},
    {"name":"get_vendor_details", "purpose":"Get full vendor profile including reviews", "parameters":["vendor_id:str"]}
  ]' \
  --package="ai"
```

**Output**:
- Agent instruction: `packages/agentic_event_orchestrator/src/agents/instructions/vendordiscoveryagent.md`
- Agent definition: `packages/agentic_event_orchestrator/src/agents/definitions/vendordiscoveryagent.py`
- Tool wrappers: `packages/agentic_event_orchestrator/src/tools/vendor_tools.py`

---

### Domain Event: Vendor Booked

```bash
/event-model \
  --event_name="vendor_booked" \
  --event_type="booking" \
  --description="A vendor has been booked for an event" \
  --producer="backend" \
  --payload_fields='[
    {"name":"bookingId", "type":"str", "required":true, "description":"UUID of the booking"},
    {"name":"vendorId", "type":"str", "required":true, "description":"Vendor being booked"},
    {"name":"eventId", "type":"str", "required":true, "description":"Event this booking is for"},
    {"name":"userId", "type":"str", "required":true, "description":"User who made booking"},
    {"name":"scheduledDate", "type":"str", "required":true, "description":"ISO date of booking"},
    {"name":"totalAmount", "type":"float", "required":true, "description":"Total in PKR"}
  ]' \
  --consumers=["Email Service","Vendor Portal","User Portal","AI Service (calendar sync)","Payment Service"]
```

**Output**:
- `DomainEvent` Prisma schema entry
- Pydantic envelope schema
- Consumer handler templates
- SSE channel registration

---

## 4. Testing

### Generate Integration Test for Vendor List Endpoint

```bash
/test-gen \
  --test_type="integration" \
  --target="list_vendors_endpoint" \
  --framework="jest" \
  --package="backend" \
  --mock_dependencies=["database","event bus"] \
  --context="Test pagination, filtering, sorting, and error cases"
```

**Output**: `packages/backend/src/__tests__/list_vendors.endpoint.test.ts` with:
- Supertest HTTP calls
- Zod validation error tests (400)
- Auth tests (401)
- Success case with pagination (200)
- Event emission assertions
- Database cleanup in afterEach

---

### Generate Unit Test for AI Tool

```bash
/test-gen \
  --test_type="unit" \
  --target="semantic_search_tool" \
  --framework="pytest" \
  --package="ai" \
  --mock_dependencies=["LLM (Gemini)","Neo4j/pgvector"] \
  --context="Test embedding generation and vector similarity search"
```

**Output**: `packages/agentic_event_orchestrator/src/__tests__/semantic_search_tool.test.py` with:
- `@pytest.mark.asyncio`
- `respx` mock for Gemini embedding API
- Async DB mock (resp. mock `AsyncSession`)
- Success case (returnsvendors sorted by cosine similarity)
- Error case (LLM API failure → retry → graceful error)

---

## 5. Code Review & Security

### Review New Code

```bash
/review \
  --file_path="packages/backend/src/services/vendor.service.ts" \
  --change_type="new_feature" \
  --package="backend" \
  --focus_areas=["N+1 queries","event emissions","rate limiting"]
```

**Output**:
- Line-by-line review
- Constitution violations flagged (CRITICAL/MAJOR/MINOR)
- Fix suggestions with code snippets
- PASS/NEEDS WORK/BLOCKED assessment
- Required actions checklist

---

### Security Audit

```bash
/security-audit \
  --target="packages/backend/src/middleware/auth.middleware.ts" \
  --audit_type="auth" \
  --package="backend" \
  --severity_filter="high"
```

**Output**:
- CVE references if applicable
- JWT secret strength check
- Token expiry recommendations
- WWW-Authenticate header check
- Rate limiting assessment
- Remediation steps

---

## 6. Documentation

### Generate API Reference

```bash
/write-docs \
  --doc_type="api_reference" \
  --subject="GET /api/v1/vendors" \
  --source_files=["packages/backend/src/routes/vendors.routes.ts","packages/backend/src/services/vendor.service.ts"] \
  --audience="developers"
```

**Output**:
- Complete API doc with:
  - Endpoint URL, method, description
  - Request query params table (types, required, defaults)
  - Response schema with example JSON
  - Error codes table (400,401,404,429,500)
  - cURL examples
  - TypeScript/React Query examples
  - Rate limit info
  - Related events and ADRs

---

### Generate Architecture Document

```bash
/write-docs \
  --doc_type="architecture" \
  --subject="Event-Driven Architecture in Event-AI" \
  --source_files=["packages/backend/src/services/event-bus.service.ts","packages/backend/prisma/models/DomainEvent.prisma"] \
  --audience="developers"
```

**Output**:
- Mermaid diagram of event flows
- Component responsibilities
- Event envelope specification
- At-least-once delivery explanation
- Dead-letter handling
- Technology choices (Fastify hooks → NATS JetStream future)

---

## 7. Workflow Orchestration

### Minimal MVP Workflow

```bash
/orchestrate \
  --feature="simple-booking" \
  --workflow=["plan","tasks","api_design","db_design","tests","code"] \
  --dry_run=false
```

**Plan first** (dry-run to see sequence):

```bash
/orchestrate \
  --feature="simple-booking" \
  --workflow=["plan","tasks","api_design","db_design","tests","code","review"] \
  --dry_run=true
```

**Output**:
- Stage-by-stage plan
- Agent assignments
- Dependency graph
- Expected artifacts
- Estimated timeline

---

## 🎯 Common Patterns

### Pattern 1: New Resource (CRUD)

1. `/db-architect` (design entity)
2. `/api-designer` (POST, GET, PUT, DELETE endpoints)
3. `/event-model` (resource.created, resource.updated, resource.deleted)
4. `/test-gen` (4 endpoints × 2-3 tests each)
5. Implement code
6. `/review`
7. `/security-audit`
8. `/write-docs` (API reference)

---

### Pattern 2: AI Agent + Tool

1. `/agent-architect` (design agent)
2. `/prompt-eng --action=create` (agent instruction)
3. `/db-architect` (if new tool needs DB table)
4. `/api-designer` (if tool exposes endpoint)
5. `/test-gen` (agent handoff test + tool unit test)
6. Implement tool business logic
7. Wire up agent
8. `/review` (check constitution rules: tools idempotent, docstrings present)
9. `/test-gen` for integration (agent → tool → DB)

---

### Pattern 3: PerformanceFix

1. `/perf-tune` (identify slow query)
2. Apply suggested changes (add index, refactor query)
3. `.env NODE_ENV=production pnpm --filter backend test:perf`
4. `/review` (check N+1 fixed)
5. `/write-docs` (update architecture if DB changed)

---

## 📋 TDD Checklist Integration

Every feature should satisfy:

```markdown
- [ ] Spec reviewed and approved
- [ ] Plan created with ADRs
- [ ] Tasks broken down with acceptance criteria
- [ ] Tests written first (RED) - used /test-gen
- [ ] Code implemented to pass tests (GREEN)
- [ ] Code reviewed - used /review
- [ ] Security audit passed - used /security-audit
- [ ] Performance targets met - used /perf-tune if needed
- [ ] Documentation complete - used /write-docs
- [ ] ADRs updated for decisions
- [ ] All constitutional checks passed
- [ ] CI green (lint, type-check, tests)
```

---

## 🐛 Troubleshooting

**Skill returns ERROR: Parameter missing**
→ Check parameter names against skill's YAML schema. Use `--help` equivalent: `/skills --action=info --skill=<name>`

**Generated code violates constitution**
→ Skills should auto-correct, but report via `/review` to catch. Some anti-patterns require manual fix (db migration strategy).

**Orchestrator blocked on stage**
→ Check dependency: db design before api design, tests before code, review before security.

**Want to customize output?**
→ Skills use templates in `output_format`. Copy to clipboard, edit, then paste to `/review` for validation.

---

## 📊 Skill Reference Matrix

| Skill | Input Files | Output Files | Constitution Rules Enforced |
|-------|-------------|--------------|---------------------------|
| api-designer | params | routes.ts, schema.ts | API contracts, Zod validation, envelope |
| db-architect | fields, relations | prisma/models, migrations | snake_case, UUID, indexes |
| agent-architect | agent spec | agent.md/.py, tools.py | SRP, handoffs, @function_tool |
| event-model | payload | DomainEvent.prisma, Pydantic | envelope, idempotency, fact-based |
| test-gen | target | __tests__/*.test.ts/py | TDD, respx mocking, coverage |
| review | code | review report | all 10 constitution sections |
| security-audit | code/config | audit report | security section (VIII) |
| perf-tune | target | optimization plan | performance section (IX) |
| docs-write | source | .md docs | clarity, completeness |
| adr | decision | history/adr/*.md | decision significance test |
| prompt-eng | prompt | optimized prompt | model-specific best practices |
| orchestrator | feature + workflow | staged output | full workflow |
| skill-manager | N/A | skill metadata | skill validity |

---

**Next**: Review the [README](README.md) for skill architecture details and creation guide.
