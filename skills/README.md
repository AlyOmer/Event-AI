# Event-AI Subagents (Claude Code Skills)

**Location**: `skills/` directory in Event-AI project root

Comprehensive suite of specialized agents built as Claude Code skills for the Event-AI marketplace platform. Each skill encapsulates domain expertise and can be invoked directly via `/skill-name` command.

## 📋 Available Skills

### Core Development

#### `/api-designer`
Design REST API endpoints following Event-AI conventions.
- Generates Zod validation schemas
- Standard response envelopes
- Error handling with proper HTTP status codes
- Domain event emissions
- Rate limiting considerations

**Example**: `/api-designer --endpoint_name="create_booking" --method="POST" --purpose="Create a booking" --package="backend"`

---

#### `/db-architect`
Design Prisma schemas and migrations.
- snake_case table/column names with `@@map/@map`
- UUIDv4 IDs, Timestamptz fields
- Proper relation definitions
- Index strategies
- Neon PostgreSQL best practices

**Example**: `/db-architect --entity_name="Vendor" --purpose="Store vendor data" --fields=[{...}]`

---

#### `/agent-architect`
Design OpenAI Agents SDK agents.
- Single responsibility design
- `@function_tool` wrappers
- Handoff patterns
- Agent instruction templates
- Tool-to-business-logic mapping

**Example**: `/agent-architect --agent_name="VendorDiscoveryAgent" --responsibility="Find vendors" --handoffs=["BookingAgent"] --tools=[{...}]`

---

#### `/event-model`
Design domain events for event-driven architecture.
- Event envelope standard (eventId, correlationId, etc.)
- Fact-based naming (resource.action)
- Consumer registrations
- SSE channel mapping
- Idempotency strategies

**Example**: `/event-model --event_name="booking_created" --event_type="booking" --producer="backend" --payload=[{...}] --consumers=["AI Service","Email"]`

---

#### `/test-gen`
Generate TDD-compliant tests.
- Backend: Jest + Supertest
- AI Service: pytest-asyncio + httpx + respx
- Frontend: React Testing Library
- Mock LLM calls (respx)
- Coverage-focused test suites

**Example**: `/test-gen --test_type="integration" --target="search_vendors_tool" --framework="pytest" --mock_dependencies=["LLM"] --package="ai"`

---

#### `/review`
Code review against Event-AI constitution.
- Anti-pattern detection
- Security compliance
- Code quality standards
- Package boundary checks
- Constructive feedback with fixes

**Example**: `/review --file_path="packages/backend/src/routes/bookings.routes.ts" --change_type="new_feature" --package="backend"`

---

#### `/security-audit`
Security vulnerability scanning.
- OWASP Top 10 coverage
- JWT/authn checks
- Injection prevention
- Secrets scanning
- Rate limiting verification
- Dependency CVEs (guidance)

**Example**: `/security-audit --target="packages/backend/src/middleware/auth.middleware.ts" --audit_type="auth" --package="backend"`

---

#### `/perf-tune`
Performance optimization.
- N+1 query fixes
- Missing indexes
- API latency optimization
- Memory/CPU profiling guidance
- Before/after metrics

**Example**: `/perf-tune --target="GET /api/v1/vendors" --issue_type="slow_query" --package="backend"`

---

### Documentation

#### `/write-docs`
Generate professional documentation.
- API reference (with examples)
- Architecture diagrams/explanations
- Setup guides
- Changelog entries
- ADRs

**Example**: `/write-docs --doc_type="api_reference" --subject="POST /api/v1/bookings" --source_files=["bookings.routes.ts"] --audience="developers"`

---

#### `/adr`
Create Architecture Decision Records.
- Standard ADR template
- Context/Decision/Consequences
- Alternatives with pros/cons
- Cross-references
- Auto-numbering

**Example**: `/adr --title="Use Neon PostgreSQL" --context="Need cloud-native DB" --alternatives_considered=[{...}] --decision="Use Neon" --consequences=[...]`

---

### AI & Prompt Engineering

#### `/prompt-eng`
Model-specific prompt engineering.
- Optimize for Claude/GPT-4/Gemini
- Chain-of-thought prompting
- Few-shot examples
- Output format specifications
- Template management

**Example**: `/prompt-eng --action="create" --model="gemini-1.5-pro" --use_case="agent instruction" --constraints="Max 2k tokens"`

---

### Workflow Orchestration

#### `/orchestrate`
Coordinate multiple agents for end-to-end feature development.
- Sequential stage execution
- Dependency management
- Progress tracking
- Dry-run planning mode
- Artifact compilation

**Example**: `/orchestrate --feature="marketplace" --workflow=["spec","plan","api_design","db_design","tests","code","review","docs"]`

---

## 🚀 Usage

### Invoking a Skill

Simply type `/skill-name` in Claude Code with the required parameters:

```bash
# Design a new API endpoint
/api-designer --endpoint_name="list_vendors" --method="GET" --purpose="Search vendors" --package="backend"
```

### Parameter Passing

- Named parameters: `--param="value"` or `--param=value`
- Arrays: `--fields=[{"name":"id","type":"String","required":true}]`
- Boolean flags: `--dry_run` (no value needed)

### Output

Each skill generates:
- Code files with proper formatting
- Documentation/explanations
- Next steps and verification commands
- References to constitution/specs

---

## 🏗️ Skill Architecture

Each skill is defined in `skills/<skill-name>.prompt.md` using Claude Code's skill definition format:

```yaml
---
name: Skill Name
description: What it does
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: concise
  tone: professional

invocation:
  command: /skill-name
  parameters: [...]  # typed schema

documentation: { ... }  # usage examples

# Skill content (system_prompt, user_message_template, output_format)
---
```

Skills are discovered automatically by Claude Code when placed in the `skills/` directory.

---

## 📦 Package Integration

Skills package-specific contexts:

| Package | Primary Skills | File Locations |
|---------|---------------|----------------|
| `backend` | api-designer, db-architect, test-gen, review, security-audit, perf-tune | `packages/backend/src/routes/`, `prisma/` |
| `ai` | agent-architect, event-model, test-gen, review | `packages/agentic_event_orchestrator/src/agents/`, `tools/` |
| `user`/`admin`/`vendor` | docs-writer, review, perf-tune | `packages/*/src/components/`, `src/app/` |
| `all` | adr, orchestrator, prompt-eng | project-wide |

---

## 🎯 TDD Workflow Integration

Skills support Event-AI's Test-First mandate:

1. `/plan` (manual or from spec) → define approach
2. `/tasks` (manual) → break into testable units
3. `/test-gen` → generate failing tests (RED)
4. `/api-designer` + `/db-architect` → define contracts
5. Implement feature code (GREEN)
6. `/review` → quality check
7. `/security-audit` → security gate
8. `/perf-tune` → optimize
9. `/docs-write` → document
10. `/adr` ← record decisions as they emerge

---

## 🔒 Conformance to Constitution

All skills enforce Event-AI constitution rules:

- **Package boundaries**: skills target correct package paths
- **Technology stack**: Prisma, Zod, Fastify, Pydantic, Next.js
- **Code quality**: TypeScript strict, Pydantic validation, Ruff compliance
- **Security**: Secrets management, rate limiting, CORS, JWT standards
- **Event-driven**: Domain events, at-least-once delivery
- **Anti-pattern avoidance**: Skills explicitly reject banned practices
- **TDD**: Tests generated with mocked LLM dependencies
- **Performance**: Latency targets, N+1 prevention

---

## 📝 Creating Custom Skills

To extend the skill set:

1. Study existing skills in `skills/` as templates
2. Copy skill structure (YAML frontmatter + content sections)
3. Define `invocation.command` (one-word `/` command)
4. Specify typed parameters
5. Write `system_prompt` with constitutional context
6. Provide `output_format` template
7. Test skill with various inputs

Register by placing `.prompt.md` file in `skills/`.

---

## 🐛 Troubleshooting

**Skill not recognized?**
- Ensure file ends with `.prompt.md`
- Check `skills/` is in project root
- Restart Claude Code session

**Parameters rejected?**
- Verify flag syntax: `--name="value"` or `--name=value`
- Arrays need JSON array format: `--fields=[{"name":"id"}]`
- Booleans: `--dry_run` (no value)

**Output not constitutional?**
- Review constitution.md for standards
- Some skills auto-correct anti-patterns
- Run `/review` on generated code

---

## 📚 References

- [Event-AI Constitution](../.specify/memory/constitution.md)
- [Claude Code Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [OpenAI Agents SDK Best Practices](https://agentfactory.panaversity.org)
- [Prisma Schema Design](https://www.prisma.io/docs)
- [FastAPI Patterns](https://fastapi.tiangolo.com)

---

**Version**: 1.0.0 | **Last Updated**: 2025-04-07 | **Branch**: 004-vendor-marketplace
