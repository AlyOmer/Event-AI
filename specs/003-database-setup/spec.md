# Feature Specification: Database Setup

**Feature Branch**: `003-database-setup`  
**Created**: 2026-04-07  
**Status**: Draft (with clarifications)  
**Input**: User description: "database setup"

## Clarifications

### Session 2026-04-07

- **Q1**: Will local database provisioning be supported?  
  **A**: No local db will be used. The platform exclusively uses cloud-hosted Neon Serverless PostgreSQL for all environments (development, staging, production). Developers configure application connection strings to point to shared cloud databases; no local PostgreSQL instance is provisioned.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cloud Database Connection Configuration (Priority: P1)

As a developer starting work on the Event-AI platform, I want to configure the application to connect to a cloud-hosted Neon database quickly, so that I can run the application without managing local database infrastructure.

**Why this priority**: Without database connectivity, the application cannot function. Since local provisioning is not supported, configuring cloud connection is the foundational requirement. All other features depend on this.

**Independent Test**: Can be fully tested by a new developer cloning the repository, configuring environment variables with valid Neon connection strings, and starting the application successfully connected to the database.

**Acceptance Scenarios**:

1. **Given** I have cloned the repository and have valid Neon database connection strings, **When** I configure the environment variables and start the application, **Then** the application connects to the database, runs migrations automatically (or on command), and is fully operational.

2. **Given** I have an existing cloud database with applied schema, **When** I deploy a new version of the application, **Then** only pending migrations are applied (idempotent operation) and no existing data is lost.

3. **Given** database connection details are incorrect or the database is unreachable, **When** I start the application, **Then** I receive a clear error message indicating the connectivity issue and the application does not crash silently.

4. **Given** connection strings are valid but the database schema is not initialized, **When** the application starts (or a setup command is run), **Then** the database schema is created by applying all migrations from scratch.

---

### User Story 2 - Production Database Migration and Rollback (Priority: P2)

As a DevOps engineer deploying to production, I want to apply database migrations safely with rollback capability, so that I can update the database schema without risking data loss or extended downtime.

**Why this priority**: Critical for production deployments. Migration safety is essential for maintainability and must work correctly before any production deployment.

**Independent Test**: Can be tested by applying a migration to a staging database that mimics production, verifying the schema change, then rolling back to confirm reversibility. The process should complete within acceptable maintenance windows.

**Acceptance Scenarios**:

1. **Given** I have a production database running, **When** I apply a new migration, **Then** the migration is applied successfully with zero data loss, all existing queries continue to work, and the migration logs are recorded.

2. **Given** a migration has been applied but causes issues, **When** I execute the rollback command, **Then** the database schema is restored to its previous state, data integrity is maintained, and the rollback is fully logged.

3. **Given** I attempt to apply a migration that would cause data loss (e.g., dropping a non-empty column), **When** the migration is detected, **Then** the system warns me and requires explicit confirmation before proceeding.

4. **Given** multiple services are running during migration, **When** I apply the migration, **Then** services continue operating with minimal disruption (migrations run quickly, use online schema change patterns where applicable).

---

### User Story 3 - Database Health Monitoring and Alerting (Priority: P3)

As a system operator, I want to monitor database health and performance metrics, so that I can detect and diagnose issues before they cause user-facing problems.

**Why this priority**: Important for operational reliability but not as critical as basic connectivity and migrations. This can be implemented after core functionality is stable.

**Independent Test**: Can be tested by querying health endpoints, reviewing logs for slow queries, and verifying that alerts trigger when thresholds are exceeded (e.g., connection pool exhaustion, long-running queries).

**Acceptance Scenarios**:

1. **Given** the database is running, **When** I check the health status endpoint, **Then** I receive status information including connection pool status, query latency statistics, and any active alerts.

2. **Given** slow queries are occurring, **When** performance metrics are collected, **Then** queries exceeding 1 second are logged and aggregated for review (without exposing sensitive data in logs).

3. **Given** the database approaches connection pool limits, **When** monitoring detects high utilization, **Then** an alert is generated and metrics show the trend for operator intervention.

4. **Given** a database restart or failure occurs, **When** the system recovers, **Then** automatic recovery procedures execute (if configured) and service availability is restored within acceptable timeframes (<5 minutes).

---

### Edge Cases

- What happens when the cloud database is unreachable due to network issues or credentials are invalid? The application should provide clear error messages and avoid infinite retry loops; implement exponential backoff and circuit breaker patterns for resilience.

- What happens when the shared development database is unavailable? Developers should have clear instructions for alternative workflows (e.g., using a personal Neon branch or waiting for maintenance). The application should not assume unlimited availability of shared resources.

- What happens when multiple developers share the same development database and their migrations conflict? Migration strategy must handle concurrent development: either each developer uses their own database branch, or migrations are coordinated to avoid conflicts. The spec assumes individual Neon branches for active development.

- What happens when database runs out of storage or reaches connection limits? Neon-specific limits should be monitored. The system should alert operators and reject new connections/writes appropriately.

- What happens during cloud provider outages affecting Neon? The system should have documented failover procedures and potentially multi-region deployment strategies for production.

- What happens when seed data depends on specific cloud database features (like pgvector) that might not be enabled on all Neon branches? The setup should check for required extensions and enable them if permissions allow, or provide clear instructions for manual enablement.

- What happens when credentials are compromised? The system should support seamless credential rotation via environment variable updates without requiring application restart (hot reload of connection configuration).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide configuration templates and documentation for setting environment variables (DATABASE_URL, DIRECT_URL) to connect to a Neon Serverless PostgreSQL instance.

- **FR-002**: The system MUST automatically detect database connection on application startup and run pending migrations unless explicitly disabled via configuration flag.

- **FR-003**: The system MUST manage database schema migrations using an incremental, versioned approach where each migration has both "up" (apply) and "down" (rollback) operations.

- **FR-004**: The system MUST store database connection configuration via environment variables only, never hardcoding credentials; must support both pooled connection strings (DATABASE_URL) and direct connection strings (DIRECT_URL) for migrations.

- **FR-005**: The system MUST enforce constitutional database standards: use Neon Serverless PostgreSQL, implement async connection pooling with pool_pre_ping, and configure proper indexes on foreign keys and commonly filtered columns.

- **FR-006**: The system MUST generate and store a migration history/log that records each applied migration with timestamp, version, and checksum for audit and rollback purposes.

- **FR-007**: The system MUST support rollback of migrations to any previous version by applying down migrations in reverse order, with clear rollback logs and data integrity validation.

- **FR-008**: The system MUST implement a backup strategy leveraging Neon's automated backups with point-in-time recovery; the application must provide configuration for backup retention and restoration procedures.

- **FR-009**: The system MUST provide database health monitoring endpoints or queries that report connection pool status, query latency statistics, and slow query logs (>1 second).

- **FR-010**: The system MUST seed essential initial data including at minimum: an administrator user account, system configuration records, and lookup tables required for application functionality; seed operations must be idempotent.

- **FR-011**: The system MUST validate database connection before proceeding with migrations or application startup, and fail fast with clear diagnostic error messages if connection cannot be established.

- **FR-012**: The system MUST handle database schema changes in a backward-compatible manner during deployments (supporting rolling updates where both old and new code versions access the same database).

- **FR-013**: The system MUST log all migration operations, backup/restore operations, and significant database events to an audit trail for compliance and debugging.

- **FR-014**: The system MUST protect database credentials using secure secret management practices: never commit secrets to version control, support integration with environment-specific secret stores, and enable credential rotation without application downtime.

- **FR-015**: The system MUST support vector extension (pgvector) setup on Neon databases, with proper index types (HNSW or IVFFlat) for semantic search capabilities, and fail gracefully if extension is unavailable.

### Key Entities

- **DatabaseConnection**: Represents a configured cloud database connection. Attributes include: connection string (pooled and direct), environment (development/staging/production), Neon branch/branch name, connection pool size settings, timeout values. The connection configuration is environment-specific and derived solely from environment variables; no local database instances are provisioned.

- **Migration**: Represents a schema change artifact. Attributes include: version number (timestamp-based or sequential), migration name, checksum/hash, apply timestamp, rollback timestamp (if applied), migration tags (e.g., "breaking", "data-loss"). Migrations are stored in version control and applied via Alembic.

- **Backup**: Represents a database backup snapshot managed by Neon. Attributes include: backup timestamp, size, retention period, point-in-time recovery window, restore status. Backups are automated by the platform; the application defines retention policies and restoration procedures.

- **SeedData**: Represents initial data that must be present for the application to function. Attributes include: seed type (admin-user, lookup-table, configuration), idempotency key, dependencies (order of seeding), and validation status. Seed data is applied after migrations and uses upsert patterns; designed for cloud environments where multiple instances may run seeds concurrently.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can configure application connectivity to a cloud database and have the application running in under 2 minutes from cloning the repository (includes cloning, environment configuration, and first application start). No local database installation required.

- **SC-002**: Migration application time: 95% of schema migrations complete in under 30 seconds on production-sized databases (excluding initial baseline migrations which may take longer for index creation).

- **SC-003**: Database availability: The database remains available for reads and writes during 99.9% of application operation time, excluding scheduled maintenance windows communicated in advance.

- **SC-004**: Migration rollback success: 100% of test migrations can be successfully rolled back without data loss (verified in staging environment before production deployment).

- **SC-005**: Backup success rate: Automated daily backups complete successfully 99.5% of the time, with backup duration under 15 minutes for databases up to 100GB.

- **SC-006**: Point-in-time recovery: System can recover to any point within the last 30 days with data loss no greater than 5 minutes of transactions (RPO ≤ 5 minutes).

- **SC-007**: Health check responsiveness: Database health status queries complete in under 200 milliseconds under normal load (<100 concurrent connections).

- **SC-008**: Connection pool efficiency: Connection pool maintains ≥95% utilization without exhausting connections during peak application load (tested with simulated concurrent users).

### User Satisfaction

- Developers rate database connectivity setup experience ≥4.5/5 for ease and clarity of configuration instructions.
- DevOps engineers report ≥4/5 confidence in production migration process and rollback capability.

### Business Impact

- Eliminate developer time spent installing and configuring local PostgreSQL: 100% reduction in local DB setup effort.
- Reduce environment configuration-related onboarding issues by 90% (from baseline of troubleshooting local DB mismatches).
- Zero production incidents caused by failed migrations or data loss per year.
- Reduce database-related downtime to ≤43 minutes per year (99.9% uptime).
- Ensure audit compliance: 100% of database schema changes are recorded with migration logs.

## Assumptions

- The project uses exclusively cloud-hosted Neon Serverless PostgreSQL for all environments (development, staging, production). Local PostgreSQL instances are not provisioned or supported.
- Database connection strings (DATABASE_URL, DIRECT_URL) are provided via environment variables; developers obtain these from a shared Neon project or create their own Neon branches.
- Migration tool is Alembic for all Python packages, following the monorepo package boundaries (constitution Section I).
- The database schema is defined incrementally via migration files stored in version control, not via a single baseline dump.
- Seed data is minimal and idempotent: admin user, essential lookup tables (event types, vendor categories), system configuration records. Seed data does not include production sample data.
- Developers are responsible for managing their own Neon database branches (creating branches from a template, applying migrations, handling conflicts). The setup tool configures connection but does not create cloud resources.
- Connection pool configuration defaults are provided but can be overridden via environment variables (pool size, timeout, etc.) to adapt to different environments and Neon plan limits.
- Backups are managed at the Neon DB platform level (automated backups) with point-in-time recovery; the application defines retention policies and restoration procedures but relies on Neon's built-in capabilities.
- Health monitoring uses standard PostgreSQL statistics (pg_stat_activity, pg_stat_statements if enabled) and connection pool metrics; no external monitoring agents are installed on the database itself.
- The database server timezone is UTC for consistency across regions; all timestamps are stored in UTC.
- The pgvector extension is required for semantic search features and must be enabled on the Neon database; the setup tool checks for extension availability and provides clear instructions if manual enablement is needed.
- Rollback capability requires that down migrations are properly defined for each schema change; this is a development discipline enforced by the TDD workflow.
- Migration ordering is determined by timestamp or version numbers; the migration tool ensures correct application order.
- In production, database schema changes follow a deployment strategy that supports backward compatibility (e.g., additive changes first, then code changes, then cleanup in later version).
- Shared development database usage enforces good migration hygiene: developers must apply migrations in order and avoid breaking changes that affect others.
