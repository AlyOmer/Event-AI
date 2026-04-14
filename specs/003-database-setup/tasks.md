# Task Specification: Database Setup

**Branch**: `003-database-setup` | **Date**: 2026-04-09 | **Spec**: [specs/003-database-setup/spec.md](spec.md) | **Plan**: [specs/003-database-setup/plan.md](plan.md)

## Task Breakdown

### Phase 1: Alembic Configuration

- [x] **1.1: Map SQLModels to Alembic Metadata**
  - **Location**: `packages/backend/alembic/env.py`
  - **Action**: Add `from src.models import *` so Alembic can detect the existing SQLModel classes and generate schema structures automatically.
  - **Test**: Run `alembic current` without error.

- [x] **1.2: Generate Initial Schema Migration**
  - **Location**: `packages/backend/alembic/versions/`
  - **Action**: Run the `alembic revision --autogenerate -m "initial_schema"` command via `uv`.
  - **Test**: Verify that a new `.py` file is created with the `create_table` statements for User, Vendor, Booking, Category, etc.

- [x] **1.3: Enable pgvector Extension**
  - **Location**: Generated initial schema migration.
  - **Action**: Add `op.execute('CREATE EXTENSION IF NOT EXISTS vector;')` to the `upgrade()` method and the DROP statement to the `downgrade()` method.

- [x] **1.4: Apply the Migration**
  - **Location**: Database
  - **Action**: Run `uv run alembic upgrade head` to apply the migrations directly to the Neon database.
  - **Test**: Log into Neon DB (or check logs) to ensure the tables are actively created.

### Phase 2: SDD Artifact Updates

- [ ] **2.1: Update History Logs (PHR)**
  - **Location**: `history/prompts/database-setup/`
  - **Action**: Assume SDD flow has been successfully bridged from plan.md to tasks.md to execution.
