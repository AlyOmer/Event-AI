# Quickstart: Database Setup for Developers

**Audience**: New developers joining the Event-AI project.  
**Scope**: Setting up cloud database connectivity (Neon Serverless PostgreSQL).  
**Time Target**: ≤2 minutes (excluding waiting for Neon branch creation).

**Important**: This project uses cloud-only databases. No local PostgreSQL installation required.

---

## Prerequisites

- Node.js 20+ installed
- Python 3.12+ installed
- pnpm package manager installed
- Git
- Neon account (access to Event-AI project)

---

## Step 1: Clone Repository and Install Dependencies

```bash
git clone https://github.com/your-org/event-ai.git
cd event-ai
pnpm install
```

Installs all workspace dependencies for Backend, AI Service, and frontend portals.

---

## Step 2: Get Your Neon Database Branch

1. Go to [Neon Console](https://console.neon.tech) and log in.
2. Select the **Event-AI project**.
3. You should see a `template` branch (created by DevOps). If not, ask a team member to create one.
4. Click **"Create Branch"** from the template.
5. Name your branch: `dev/your-username` (e.g., `dev/john`)
6. Click **Create**.
7. In your branch details, locate **Connection string** (pooled). Click **Copy**.

---

## Step 3: Configure Environment Variables

Create a `.env` file in the repository root:

```bash
cp .env.example .env
```

Edit `.env` and set:

```ini
# Backend & AI Service database connection
DATABASE_URL="postgresql://username:password@ep-xyz.pooler.us-east-2.aws.neon.tech/event_ai?connection_limit=20"
DIRECT_URL="postgresql://username:password@ep-xyz.us-east-2.aws.neon.tech/event_ai"

# JWT secret (for authentication feature later)
JWT_SECRET="your-random-256-bit-secret-here"
# (Generate with: openssl rand -base64 32)
```

Replace the connection string with the one you copied from Neon. The `connection_limit=20` is a safe default; adjust based on your Neon plan.

---

## Step 4: Verify Database Connection and Run Migrations

### Backend (Node.js)

```bash
pnpm --filter backend db:migrate
```

This runs `prisma migrate deploy` and applies any pending migrations to your Neon branch. You should see output:

```
Prisma schema loaded from prisma/schema.prisma
Datasource "db": PostgreSQL database "event_ai" at "ep-xyz.pooler..."
Applying migration `20240407120000_init`
The following migration(s) have been applied:
- Migration 20240407120000_init
```

### AI Service (Python)

```bash
cd packages/agentic_event_orchestrator
uv run alembic upgrade head
```

You should see:
```
INFO  [alembic.runtime.migration] Running upgrade -> 1234567890ab, initial migration
```

Both commands are idempotent—running them again does nothing if already applied.

---

## Step 5: Seed Initial Data

### Backend Seed (Admin User, Lookup Tables)

```bash
pnpm --filter backend db:seed
```

This creates:
- Admin user (email: `admin@example.com`, password from env var or generated)
- Event types (wedding, corporate, birthday, etc.)
- Vendor categories (photography, catering, venue, etc.)
- System configuration records

**Important**: The seed is idempotent. Running it multiple times is safe.

### AI Service Seed (Optional Initial Data)

```bash
cd packages/agentic_event_orchestrator
uv run python -m src.cli.seed
```

This may create default agent configurations or embedding indexes if needed.

---

## Step 6: Start Application Services

### Backend API

```bash
pnpm --filter backend dev
```

Starts Fastify server on `http://localhost:3000`. The server:
- Connects to database automatically on startup
- Applies pending migrations (if `AUTO_MIGRATE=true` in `.env`, default false)
- Health endpoint: `GET http://localhost:3000/health/database`

### AI Service

```bash
cd packages/agentic_event_orchestrator
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Starts FastAPI on `http://localhost:8000`.

Health endpoint: `GET http://localhost:8000/health/database`

---

## Step 7: Verify Health

Check database health endpoint:

```bash
curl http://localhost:3000/health/database | jq
```

Expected response:
```json
{
  "status": "healthy",
  "connection_pool": {
    "available": 19,
    "idle": 18,
    "used": 1,
    "total": 20
  },
  "latency_ms": {
    "p50": 2.5,
    "p95": 8.1,
    "p99": 15.3
  },
  "slow_queries_last_5m": 0,
  "extensions": {
    "pgvector": "enabled"
  },
  "timestamp": "2026-04-07T12:34:56Z"
}
```

If `status` is `degraded` or `unhealthy`, check:
- DATABASE_URL correct and database reachable
- pgvector extension enabled (`CREATE EXTENSION vector;`)
- Migration errors in server logs

---

## Troubleshooting

### Database Connection Refused

**Symptom**: Error: `password authentication failed` or `could not connect to server`.

**Solutions**:
1. Verify connection string copied correctly from Neon (no truncation)
2. Ensure Neon branch is active (not suspended for inactivity)
3. Check firewall: Neon IPs must be allowed (Neon typically allows all but some corporate firewalls block)
4. Test connection manually:
   ```bash
   psql "postgresql://username:password@host/db"
   ```

### Migration Already Applied Error

**Symptom**: Prisma/Alembic reports migration already applied when running `db:migrate`.

**Cause**: You're using the same Neon branch as someone else; they already applied that migration.

**Solution**: Migrations are global. Your branch should be up-to-date. If you're working on a new feature, create your own branch from template and apply your migrations there. Coordinate with team on migration timing.

### pgvector Extension Not Found

**Symptom**: Error: `extension "vector" does not exist`.

**Solution**: Enable extension manually (once per branch):
```bash
psql "postgresql://.../event_ai" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```
Or ask DevOps to enable in template branch.

### Seed Data Duplicate Key Errors

**Symptom**: `duplicate key value violates unique constraint` during seeding.

**Cause**: Seed script not idempotent (bug). Should use upsert.

**Solution**: Report issue. Meanwhile, manually delete conflicting rows or use different Neon branch.

### Connection Pool Exhausted

**Symptom**: `too many clients` or connection timeout.

**Cause**: Pool size too small for concurrent operations, or connections not being released.

**Solutions**:
1. Increase `connection_limit` in DATABASE_URL (up to Neon plan limit)
2. Ensure all database queries are properly awaited and connections released
3. Check for idle connections not being closed (pool idle timeout)
4. Use Neon's connection pooler effectively; consider reducing pool size if over-provisioning

### Migrations Fail Part-Way

**Symptom**: Migration error mid-apply; schema partially changed.

**Solution**:
- Prisma: Migrations are transactional. If error occurs, transaction rolls back automatically. Re-run.
- Alembic: Some DDL operations cannot run in transaction (e.g., CREATE INDEX CONCURRENTLY). Script must handle this. Report bug if migration not idempotent.

After fixing, re-run migration command.

---

## Next Steps After Database Setup

You now have a working cloud database connection! Continue with:

1. Authentication feature (`002-user-auth`): Implement JWT token management against your database
2. Build other features on top of the database
3. When adding new features that require database changes:
   - Backend: Update `prisma/schema.prisma`, generate migration, test on your branch
   - AI Service: Update SQLModel classes, run `alembic revision --autogenerate`, review, test
4. Push local migrations to git; team members will pull and apply to their branches

---

## Additional Resources

- [Neon Docs](https://neon.tech/docs)
- [Prisma Migrate Guide](https://www.prisma.io/docs/concepts/components/prisma-migrate)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- Project Constitution: `.specify/memory/constitution.md` (see Section IV for database standards)

**Need Help?** Contact the DevOps team or post in `#infra` Slack channel.

---

**Quickstart Complete**: You should now have a fully functional cloud database connection. The database is ready for development.
