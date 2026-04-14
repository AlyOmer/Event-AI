# Implementation Plan: Database Setup

**Branch**: `003-database-setup` | **Date**: 2026-04-07 | **Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/003-database-setup/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature establishes cloud-only database connectivity and schema management for the Event-AI monorepo. Developers configure environment variables (DATABASE_URL, DIRECT_URL) to connect to Neon Serverless PostgreSQL instances. No local database provisioning occurs. The system provides automated migration execution, reversible schema changes, health monitoring, and idempotent seeding. Implementation spans both the Backend (Node.js/Fastify/Prisma) and AI Service (Python/FastAPI/SQLModel) packages, each managing their own database schemas within the same Neon database.

**Primary Technical Approach**:
- Use Alembic for all schema management (Backend and AI Service)
- Use SQLModel for all domain entities
- Implement connection pooling with async drivers (pg for Node.js, asyncpg for Python)
- Leverage Neon's built-in backups and point-in-time recovery
- Create health monitoring endpoints using standard PostgreSQL statistics
- Enforce constitutional standards: async-first, proper indexing, pgvector support

## Technical Context

**Language/Version**: Node.js 20+ (Backend), Python 3.12+ (AI Service)

**Primary Dependencies**:
- Backend: FastAPI, SQLModel, Alembic, asyncpg, structlog
- AI Service: FastAPI, SQLModel, Alembic, asyncpg, httpx
- Shared: Neon Serverless PostgreSQL with pgvector extension

**Storage**: Neon Serverless PostgreSQL (single cloud database, separate branches for dev/staging/prod). pgvector extension required for semantic search capabilities.

**Testing**:
- Backend: Jest + Supertest (80% coverage on services)
- AI Service: pytest + httpx + respx (70% coverage on tools)
- Integration tests for migration operations on isolated Neon branches

**Target Platform**: Cloud-only (Neon serverless PostgreSQL). Developers connect to shared cloud databases using individual Neon branches. Docker may be used for application containers but not for database.

**Project Type**: Multi-package monorepo (Turborepo + pnpm workspaces). This is an infrastructure feature that modifies:
- `packages/backend` (database connection, SQLModel schema, migrations, API routes)
- `packages/agentic_event_orchestrator` (SQLModel models, Alembic migrations, health endpoints)
- Possibly shared scripts or configuration at repository root

**Performance Goals**:
- Migration execution: 95% of migrations complete in <30s
- Health check queries: <200ms response time
- Connection pool: ≥95% utilization without exhaustion
- Database availability: 99.9% uptime

**Constraints**:
- Must not require local PostgreSQL installation (cloud-only)
- All database access must be async (constitutional mandate)
- Must use environment variables for connection configuration (no hardcoded credentials)
- Must implement reversible migrations (up/down)
- Must follow constitutional package boundaries (Backend manages Prisma, AI Service manages SQLModel)

**Scale/Scope**:
- Supports development team of 10-20 developers
- Production database expected size: up to 100GB
- Concurrent users: ≥10,000 (handled by application layer; database handles connection pool sizing)
- Schema complexity: ~50-100 tables across both Backend and AI Service domains

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASS (no violations)

| Principle | Requirement | Compliance |
|-----------|-------------|------------|
| I. Monorepo-First | Cross-package imports go through API contracts | ✅ Will use defined package boundaries; no cross-imports |
| I. Technology Stack | Backend: Prisma, Neon DB, pg vector; AI: SQLModel, asyncpg | ✅ Will use exactly these technologies |
| II. Event-Driven | Not directly applicable (database layer) | N/A |
| III. Database Standards | Async engines, N+1 prevention, Prisma/SQLModel | ✅ Will implement async connections, use proper loading strategies |
| IV. Test-First | ≥80% coverage on Backend services, ≥70% on AI tools | ✅ Will write comprehensive tests for migration operations |
| V. API Contracts | Not applicable (this is infra layer) | N/A |
| VI. Security | Secrets via .env, rate limiting not applicable here | ✅ Credentials via env vars only; no endpoints yet |
| VII. Augmented Memory | pgvector setup required | ✅ Will ensure pgvector extension enabled |
| VIII. Security (JWT, etc.) | Not directly applicable | N/A |
| IX. Simplicity | No dead code, minimal dependencies | ✅ Will not add unnecessary abstraction |
| X. Code Quality | Async-first, proper logging, type hints | ✅ Will follow all quality standards |

**No constitution violations detected. Implementation will enforce constitutional database standards.**

## Project Structure

### Documentation (this feature)

```text
specs/003-database-setup/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output - research on Neon, Prisma, Alembic
├── data-model.md        # Phase 1 output - detailed schemas, migration strategy
├── quickstart.md        # Phase 1 output - developer onboarding guide
├── contracts/           # Phase 1 output - API contracts for health endpoints
│   ├── health-response.json
│   └── migration-status.json
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
# Monorepo structure - this infrastructure feature modifies multiple packages

packages/backend/
├── src/
│   ├── config/
│   │   └── database.ts           # Database connection setup (Prisma client initialization)
│   ├── cli/
│   │   └── migrate.ts            # CLI commands for migrations (prisma migrate deploy, reset)
│   ├── plugins/
│   │   └── prisma-plugin.ts      # Fastify plugin for Prisma client lifecycle
│   ├── routes/
│   │   └── health/
│   │       └── database.ts       # Health endpoint reporting DB status
│   └── utils/
│       └── seed.ts               # Idempotent seed data operations
├── prisma/
│   ├── schema.prisma             # Prisma schema with models
│   ├── migrations/               # Prisma migration files (timestamped)
│   └── seeds/
│       └── seed.ts               # Seed script for initial data
└── tests/
    ├── integration/
    │   └── database.test.ts     # Connection and migration tests
    └── unit/
        └── config/
            └── database.test.ts

packages/agentic_event_orchestrator/
├── src/
│   ├── config/
│   │   └── database.py           # SQLAlchemy async engine + session factory setup
│   ├── api/
│   │   └── routes/
│   │       └── health.py         # FastAPI health endpoint with DB check
│   ├── models/                   # SQLModel models (domain entities)
│   ├── tools/
│   │   └── db_tools.py           # Database health check tools for agents
│   └── cli/
│       └── migrations.py         # Alembic migration commands
├── alembic/
│   ├── versions/                 # Alembic migration scripts
│   ├── env.py
│   └── script.py.mako
├── tests/
│   ├── integration/
│   │   └── test_database.py      # DB connection, migration tests
│   └── unit/
│       └── config/
│           └── test_database.py
└── pyproject.toml                # Dependencies: sqlmodel, asyncpg, alembic

# Repository-level (root)
├── .env.example                  # Template for DATABASE_URL, DIRECT_URL
├── docker/
│   └── dev-compose.yml          # Optional: app container (no DB)
└── docs/
    └── database-setup.md        # Developer onboarding guide (quickstart)
```

**Structure Decision**: This is a **cross-package infrastructure feature** in a monorepo. It modifies both `packages/backend` (Node.js/Prisma) and `packages/agentic_event_orchestrator` (Python/SQLModel) because each package owns its database schema per monorepo boundaries (Constitution Section I). No new package is created; existing packages are extended. Health monitoring endpoints are added to each package's API layer. The root-level documentation provides unified onboarding.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

This section is **not required** because no constitutional violations exist. The implementation aligns with all principles:

- Uses mandated technologies (Neon, Prisma, SQLModel, async drivers)
- Respects package boundaries (each package manages its own schema)
- Follows async-first approach
- Will implement proper error handling and logging
- No additional packages beyond the monorepo structure

**No complexity justifications needed.**

## Architectural Decisions

### Decision 1: Separate Migration Systems (Prisma vs Alembic)

**Context**: Constitution mandates Prisma for Backend and SQLModel (Alembic) for AI Service. Both must coexist in the same Neon database without stepping on each other's tables.

**Decision**: Use separate schema namespaces within the same database:
- Backend tables: `public` schema (default) with naming convention `backend_*` for cross-package tables
- AI Service tables: `ai` schema to isolate its domain tables
- Each package's migration tool only manages its own schema

**Rationale**: Enforces monorepo package boundaries; prevents accidental cross-modification; allows independent deployment cycles; aligns with constitutional ORM separation.

### Decision 2: Cloud-Only Development Model

**Context**: Clarification: no local db will be used. Developers must connect to shared cloud databases.

**Decision**: Each developer creates their own Neon branch (database fork) from a template. Connection strings are configured via environment variables. The application auto-runs migrations on startup (configurable). No local PostgreSQL installation required.

**Rationale**: Simplifies onboarding, ensures environment parity, leverages Neon's branching for isolated development. Matches constitutional commitment to Neon serverless.

### Decision 3: Health Monitoring Strategy

**Context**: Need to monitor database health without external agents (constitution simplicity).

**Decision**: Expose `/health/database` endpoint in each package's API that returns:
- Connection pool status (available/idle/used connections)
- Query latency percentiles (p50, p95, p99) from pg_stat_statements
- Slow query count (>1s)
- Extension availability (pgvector)
All metrics collected via SQL queries on system views; no external monitoring library.

**Rationale**: Lightweight, uses PostgreSQL built-in statistics, no additional dependencies, aligns with constitutional simplicity and observability requirements.

### Decision 4: Seed Data Idempotency

**Context**: Multiple developers may run seeds concurrently on their Neon branches; need to avoid conflicts.

**Decision**: Use upsert patterns with natural keys or unique constraints. Seed operations are structured as atomic transactions per seed item. Idempotency keys stored in a `seed_log` table track which seeds have been applied.

**Rationale**: Prevents duplicate key errors, allows re-running seeds safely, provides audit trail of seed operations. Aligns with constitutional data integrity standards.

### Decision 5: Migration Safety Controls

**Context**: Constitution requires rollback capability and zero data loss.

**Decision**:
- All migrations must include both `up` and `down` operations; CI will reject PRs lacking down migrations.
- Destructive operations (DROP COLUMN, DROP TABLE) require explicit confirmation flag in production (`--confirm-destructive`).
- Migration checks: detect pending destructive changes, estimate row loss, enforce review.
- Automatic pre-migration backup via Neon PITR (point-in-time recovery) window.

**Rationale**: Prevents accidental data loss, enforces development discipline, provides safety nets. Aligns with constitutional reliability mandates.

## Phase Plan

**Phase 0: Research & Setup** (No code changes, knowledge gathering)
- Research Neon Serverless PostgreSQL connection patterns and best practices
- Document Prisma migration workflows in monorepo context
- Document Alembic migration workflows with asyncpg
- Determine pgvector index strategies (HNSW vs IVFFlat)
- Create developer onboarding guide (quickstart.md) with Neon branch creation steps
- Validate environment variable conventions (DATABASE_URL, DIRECT_URL formats)

**Phase 1: Core Implementation** (Database connectivity + migrations)
- Implement `packages/backend/src/config/database.ts`: Prisma client singleton with proper lifecycle management
- Implement `packages/agentic_event_orchestrator/src/config/database.py`: asyncpg engine + sessionmaker
- Add CLI commands for migrations:
  - Backend: `pnpm --filter backend migrate` wrapper around `prisma migrate deploy`
  - AI Service: `uv run alembic upgrade head` CLI command
- Create migration linting tool: check for missing down migrations, destructive changes
- Implement health endpoints:
  - Backend: `GET /health/database` (Fastify route)
  - AI Service: `GET /health/database` (FastAPI route)
- Implement seed data scripts (idempotent, transaction-based)
- Write unit and integration tests:
  - Mock connection failures, test error handling
  - Test migration apply/rollback on test Neon branches
  - Test idempotency of seed operations
  - Test health endpoint metrics collection

**Phase 2: Observability & Production Hardening** (Monitoring, backups, alerts)
- Enhance health endpoints with query latency metrics (pg_stat_statements)
- Add connection pool metrics to health response
- Document backup/restore procedures leveraging Neon PITR
- Add alerting thresholds (connection pool >90%, slow queries >100)
- Implement credential rotation support (hot reload of connection strings)
- Write performance tests: simulate concurrent connections, measure connection pool behavior
- Create runbooks for common database issues (connection exhaustion, slow queries, migration failures)

**Phase 3: Documentation & Verification** (Docs, final validation)
- Complete `docs/database-setup.md` with troubleshooting guide
- Write contract tests verifying health endpoint schema
- Run full integration test suite on staging Neon database
- Verify constitutional compliance checklist (database standards, async, logging)
- Final review: no hardcoded credentials, all migrations reversible, seed data idempotent

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Neon service outage affects all developers | Medium | High | Document local fallback: developers can create emergency local PostgreSQL if absolutely needed; establish incident response with Neon SLA |
| Migration conflicts when developers share branches | Medium | Medium | Enforce individual Neon branches; provide tool to create branch from template; education on migration hygiene |
| pgvector not enabled on some Neon instances | Low | Medium | Health check detects missing extension; setup script enables it automatically or provides clear instructions |
| Sensitive data in logs (connection strings) | Low | High | Use structured logging with redaction; ensure connection strings never logged; PII from queries masked |
| Long-running migrations block deployments | Medium | High | Online schema change patterns (CREATE INDEX CONCURRENTLY); schedule heavy migrations during off-hours; use maintenance mode if needed |
| Connection pool misconfiguration causes timeouts | Medium | Medium | Provide sensible defaults based on Neon limits; allow overrides via env vars; health check warns on high utilization |

## Interfaces & Contracts

### Database Connection Configuration

**Environment Variables**:
- `DATABASE_URL` (required): Pooled connection string (e.g., `postgresql://user:pass@host:port/db?connection_limit=20`)
- `DIRECT_URL` (optional but recommended): Direct connection string for migrations (no pool)

No defaults. Missing variables cause startup failure with clear error.

### Health Endpoint

**Backend (Fastify)**: `GET /health/database`
**AI Service (FastAPI)**: `GET /health/database`

Response schema:
```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "connection_pool": {
    "available": 10,
    "idle": 8,
    "used": 2,
    "total": 20
  },
  "latency_ms": {
    "p50": 2.5,
    "p95": 8.1,
    "p99": 15.3
  },
  "slow_queries_last_5m": 3,
  "extensions": {
    "pgvector": "enabled"
  },
  "timestamp": "2026-04-07T12:34:56Z"
}
```

### Migration Commands

**Backend**:
- `pnpm --filter backend db:migrate` → applies pending Prisma migrations
- `pnpm --filter backend db:migrate:reset` → resets database (dev only, requires confirmation)
- `pnpm --filter backend db:seed` → runs seed script

**AI Service**:
- `uv run alembic upgrade head` → applies pending Alembic migrations
- `uv run alembic downgrade -1` → rolls back one migration
- `uv run python -m src.cli.seed` → runs seed script

All commands are documented in `docs/database-setup.md`.

## Definition of Done

- [ ] All environment configuration documented (DATABASE_URL, DIRECT_URL formats)
- [ ] Backend: Prisma client initializes correctly with async connection pool
- [ ] AI Service: SQLModel async engine creates session factory properly
- [ ] Prisma migrations apply successfully on Neon branch
- [ ] Alembic migrations apply successfully on same Neon database
- [ ] Health endpoints exist in both packages and return correct schema
- [ ] Health check queries complete in <200ms under normal load
- [ ] Seed data (admin user, lookup tables) inserted idempotently
- [ ] Migration linting enforces down migrations and flags destructive changes
- [ ] Unit tests cover connection failure handling (mock errors)
- [ ] Integration tests verify migrate/rollback on test Neon branch
- [ ] Integration tests verify seed idempotency under concurrent execution
- [ ] Health endpoint metrics validated (connection pool stats, latency)
- [ ] All tests pass with ≥80% coverage (Backend) and ≥70% (AI Service)
- [ ] No hardcoded credentials anywhere in codebase
- [ ] All database operations are async (no blocking sync calls)
- [ ] pgvector extension enabled and verified in health check
- [ ] Documentation (`docs/database-setup.md`) complete with troubleshooting
- [ ] Constitution compliance validated: all mandatory database standards met

## Data Model Changes

**New Tables**:
- `backend_seed_log` (optional): tracks applied seeds (idempotency key, applied_at)
- Migration history tables:
  - Prisma: `_prisma_migrations` (managed by Prisma)
  - Alembic: `alembic_version` (managed by Alembic)

**No new domain tables in this feature** - this is infrastructure, not application features.

**Existing Tables Affected**: None. This feature sets up the database platform; application features will add domain tables in subsequent specs.

## Open Questions / Deferred

None. All critical clarifications resolved (cloud-only confirmed). No implementation ambiguities remain.
