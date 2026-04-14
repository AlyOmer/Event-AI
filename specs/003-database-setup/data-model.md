# Phase 1 Data Model: Database Setup

**Date**: 2026-04-07  
**Feature**: 003-database-setup

## Overview

This document defines the database schema changes, migration strategy, and data model for the cloud-only database setup feature. It covers schema organization (separate namespaces), infrastructure tables (seed logging, migration history), and guidelines for future feature schemas.

**Important**: This feature does NOT introduce application domain tables (those come in later features). It establishes the database platform, connection management, and migration infrastructure.

## Schema Organization

### Single Database, Multiple Schemas

The Neon database will contain two primary schemas to enforce monorepo package boundaries:

| Schema | Owner Package | Purpose |
|--------|---------------|---------|
| `public` | `packages/backend` | Core domain tables (users, events, bookings, vendors, etc.) |
| `ai` | `packages/agentic_event_orchestrator` | AI-specific tables (chat_sessions, messages, vectors, agent memory) |

**Rationale**:
- Prevents accidental cross-package table modifications
- Allows independent migrations (Prisma manages `public`, Alembic manages `ai`)
- Enables separate backup/restore strategies if needed
- Clear ownership boundaries

**Cross-Schema References**:
- Tables in `public` can reference tables in `ai` via foreign keys using qualified names (e.g., `ai.chat_sessions`)
- Tables in `ai` should avoid referencing `public` tables to prevent coupling; instead, use IDs and join in application logic
- If cross-schema references are absolutely necessary, use explicit schema qualifiers and ensure both schemas exist

### Extensions

**Required Extension**: `pgvector`

Enable once per database (ideally in template branch):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

This extension provides `vector` data type and similarity search operators (`<=>`, `<->`, etc.). Used by AI Service for semantic search and embeddings storage.

## Migration Strategy

### Prisma Migrate (Backend Package)

**Schema File**: `packages/backend/prisma/schema.prisma`

**Model Example**:
```prisma
model User {
  id        String   @id @default(uuid())
  email     String   @unique
  password  String
  name      String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("users") // snake_case table name
  @@index([email])
}
```

**Migration Workflow**:
1. Developer updates `schema.prisma` or adds new model
2. Run: `prisma migrate dev --name description` (creates migration, applies to local/dev branch)
3. Review generated SQL in `prisma/migrations/<timestamp>_description/migration.sql`
4. Ensure `rollback.sql` is correct (Prisma auto-generates but may need manual adjustment)
5. Commit migration files (not `prisma/schema.prisma` alone; migrations are source of truth)
6. CI runs: `prisma migrate deploy` on staging/production

**Important**: Prisma does NOT support schema namespaces directly. By default, tables go to `public`. That's fine—Backend owns `public`.

**Connections**:
- Use `DATABASE_URL` (pooled) for application
- Use `DIRECT_URL` (direct) for `prisma migrate deploy` to avoid transaction issues with DDL

### Alembic Migrations (AI Service Package)

**Configuration**: `packages/agentic_event_orchestrator/alembic.ini` or programmatic in `env.py`

**Model Definition**: SQLModel classes in `src/models/`

**Example Model**:
```python
class AgentMemory(Base, SQLModel):
    __tablename__ = "agent_memories"
    __table_args__ = {"schema": "ai"}  # Use ai schema

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(sa_type=Text)
    content: str = Field(sa_type=Text)
    embedding: Optional[list[float]] = Field(default=None, sa_column=Column(VECTOR(1536)))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("ix_agent_memories_embedding", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
```

**Migration Workflow**:
1. Developer adds/changes SQLModel class
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated script in `alembic/versions/`—autogenerate is not perfect; fix column types, naming, data migrations
4. Ensure `downgrade()` is implemented (never `pass`)
5. Test: `alembic upgrade head` on dev branch
6. Commit migration script
7. CI runs: `alembic upgrade head` on staging/production

**Schema Configuration**: In `env.py`, set `default_schema = 'ai'` or use `schema` argument in `MetaData`.

**Async Support**: Use `create_async_engine(DATABASE_URL)` and `async_sessionmaker`. Alembic can run async migrations if configured properly; if not, migrations may use sync engine for simplicity—acceptable as long as they apply correctly.

### Migration Coordination Between Packages

**Challenge**: Two independent migration systems (Prisma and Alembic) on same database. Order matters if one package depends on the other's tables.

**Solution**:
- Keep schemas separate; minimal cross-dependencies
- If cross-schema dependency exists (AI Service references Backend table), ensure Backend migrations run first
- For deployment: apply Backend migrations, then AI Service migrations
- For local dev: application startup can optionally auto-run pending migrations for both packages (configurable)

### Rollback Strategy

**Prisma**: `prisma migrate reset` (dev only, drops all data) or `prisma migrate deploy` with specific migration name to roll back to that version. In production, create explicit down migration.

**Alembic**: `alembic downgrade -1` or `alembic downgrade <revision>`.

**Testing**: All migrations must be tested for rollback on staging database before production deployment. CI can optionally run rollback tests on disposable branches.

## Infrastructure Tables

### Seed Log (Custom)

**Purpose**: Track which seed records have been applied to ensure idempotency.

**SQL** (created by Backend package, schema `public`):
```sql
CREATE TABLE seed_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  seed_name VARCHAR(255) UNIQUE NOT NULL,
  applied_at TIMESTAMPTZ DEFAULT NOW(),
  checksum VARCHAR(255)  -- SHA256 of seed data content to detect changes
);
```

**Usage**:
- Before inserting seed data, check if record with `seed_name` exists in `seed_log`
- If exists and checksum matches, skip
- If exists but checksum differs, upsert with new data and update `applied_at`
- All within transaction

**Seed Log Entries**: e.g., `admin_user`, `event_types`, `vendor_categories`, `system_config`

### Migration History (Managed by Tools)

**Prisma**: `_prisma_migrations` table in `public` schema. Auto-created.
```sql
SELECT * FROM _prisma_migrations;
-- Columns: id, checksum, finished_at, migration_name, logs, rolled_back_at
```

**Alembic**: `alembic_version` table in `ai` schema. Auto-created.
```sql
SELECT * FROM ai.alembic_version;
-- Columns: version_num
```

These tables are authoritative source of applied migrations. Never edit manually.

## Health Monitoring Schema

No new tables. Queries use system views:

**Connection Pool**:
```sql
SELECT
  count(*) as total,
  count(*) FILTER (WHERE state = 'active') as active,
  count(*) FILTER (WHERE state = 'idle') as idle,
  count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity;
```

**Query Latency (requires pg_stat_statements extension)**:
```sql
SELECT
  sqrt(median(total_exec_time)/calls*1000) as p50_ms,
  sqrt(95percentile(total_exec_time)/calls*1000) as p95_ms,
  sqrt(max(total_exec_time)/calls*1000) as p99_ms
FROM pg_stat_statements;
```
*Note: Percentile functions depend on PostgreSQL version; may need custom approximation.*

**Slow Queries**:
```sql
SELECT query, calls, mean_time, rows FROM pg_stat_statements WHERE mean_time > 1000 ORDER BY mean_time DESC LIMIT 10;
```

**Extensions**:
```sql
SELECT extname, extversion FROM pg_extension;
-- Check for 'vector'
```

All queries wrapped in try-except; failures return degraded status, not crash.

## Data Volume and Scale Assumptions

**Development Branches**: Small datasets (<10K rows per table). Migrations should be instantaneous.

**Staging/Production**: Expected scale:
- Users: 50K - 100K
- Events: 10K/year
- Bookings: 100K/year
- Vendor catalog: 5K vendors
- Chat messages: Millions (AI service)

**Performance Targets**:
- Index all foreign keys, email columns, timestamps
- Use partial indexes for filtered queries
- Vector dimension: 1536 (default OpenAI/Cosmos embeddings)
- pgvector index: HNSW with `m=16, ef_construction=64` (reasonable defaults)

**Partitioning**: Not needed yet. If event tables grow large, consider time-based partitioning (by month) using PostgreSQL declarative partitioning.

## Rollback and Recovery Procedures

### Application-Level Rollback

For each migration, test the `downgrade` path:
1. Apply migration to staging database (with sample data)
2. Run application tests against migrated schema
3. Roll back: `prisma migrate reset` (dev) or `alembic downgrade -1` (or to specific revision)
4. Verify data integrity, application functionality with old schema

**CI Integration**: Optional job that runs migration forward then backward on temporary Neon branch.

### Platform-Level Recovery (Neon PITR)

Neon provides point-in-time recovery to any second within retention period (7-30 days).

**Restore Process**:
1. In Neon console, create new branch from desired point-in-time (e.g., before bad migration)
2. Promote new branch to primary or test against it
3. Application re-points connection string to new branch

**RPO**: ≤5 minutes (based on WAL archiving frequency)
**RTO**: <15 minutes to restore and promote branch

**Note**: Application-level rollback (down migrations) is preferred for logical errors. PITR is for catastrophic failures or data corruption.

## Data Retention Policies

**Audit/Log Tables**: None defined yet (will come later). Constitutional principle: retain security events (AUTH_*) for 1 year minimum.

**Business Data**: No automatic purging. Required by business logic (e.g., soft delete for records).

**Logs**: Database query logs from pg_stat_statements are ephemeral (reset on restart). Application logs go to external system (Pino -> Loki/ELK).

## Security Considerations

**Authentication**: Database access controlled by Neon credentials. Connection strings contain username/password.

**Authorization**: Single database role per environment (no row-level security for now).

**Encryption**:
- In transit: TLS enforced by Neon (require `?sslmode=require` in connection URL)
- At rest: Neon handles disk encryption
- Secrets: stored in `.env`; in production, use secret manager (AWS Secrets Manager, etc.)

**SQL Injection Prevention**: Use ORM parameterized queries exclusively. Never build raw SQL with string concatenation.

**Row-Level Security**: Not implemented at this stage; may be needed later for multi-tenancy (vendor data isolation).

## Change Management

**Schema Changes**: All schema changes MUST go through migration files (Prisma or Alembic). Never manually `ALTER` production database.

**Migration Review**:
- PR requires at least one reviewer to verify migration SQL
- Destructive changes (DROP, ALTER TYPE) need explicit `--confirm-destructive` flag in production deploy
- Data migrations should be reversible or have compensation logic

**Version Control**:
- `packages/backend/prisma/schema.prisma` + `prisma/migrations/`
- `packages/agentic_event_orchestrator/models/` + `alembic/versions/`
- Never commit `.env` or connection strings

## Data Model Diagrams

### ER Overview (High-Level)

```
┌─────────────────┐         ┌─────────────────┐
│   public schema │         │     ai schema   │
│  (Backend)      │         │  (AI Service)   │
├─────────────────┤         ├─────────────────┤
│ users           │         │ chat_sessions   │
│ events          │         │ messages        │
│ bookings        │         │ agent_memories  │
│ vendors         │         │ embeddings      │
│ vendor_categories│        │ tool_executions │
│ event_types     │         │ ...             │
│ system_config   │         └─────────────────┘
│ seed_log        │
│ _prisma_migrations│
└─────────────────┘
```

No foreign keys crossing schemas initially. If needed, they reference by ID only (no FK constraints to avoid cross-schema dependency cycles).

### Seed Log Table (Definitive)

```sql
CREATE TABLE public.seed_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  seed_name VARCHAR(255) UNIQUE NOT NULL,
  applied_at TIMESTAMPTZ DEFAULT NOW(),
  checksum VARCHAR(255)
);
```

### Migration History Tables

Prisma (`public._prisma_migrations`): auto-managed.  
Alembic (`ai.alembic_version`): auto-managed.

---

**Data Model Complete**: All schemas, tables, and migration strategies defined. Ready to proceed to implementation (Phase 1) or generate tasks (/sp.tasks).
