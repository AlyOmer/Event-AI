# Implementation Plan: FastAPI JWT Authentication with OAuth2

**Branch**: `013-fastapi-jwt-auth` | **Date**: 2026-04-09 | **Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/013-fastapi-jwt-auth/spec.md`

## Summary

Implement JWT-based authentication for the FastAPI backend using OAuth2 password grant flow. Users register with email + strong password (bcrypt-hashed), log in to receive short-lived access tokens (15 min) and long-lived refresh tokens (7 days with rotation). Refresh token rotation invalidates old tokens on use, providing session revocation and theft detection. The system enforces rate limiting, structured JSON logging, and follows all FastAPI/SQLModel best practices per the project constitution.

**Research Outcome** (from `research.md`):
- JWT library: `python-jose[cryptography]` with HS256 algorithm
- Password hashing: `passlib[bcrypt]` with 12 salt rounds
- Rate limiting: `slowapi` in-memory (Redis-ready for scaling)
- Structured logging: `structlog` JSON output
- Settings: Pydantic `BaseSettings` + `@lru_cache`
- OAuth2: `OAuth2PasswordBearer` + `OAuth2PasswordRequestForm` (form-encoded body per spec)

---

## Technical Context

**Language/Version**: Python 3.13+ (constitution mandates ≥3.12)  
**Primary Dependencies**:
- FastAPI ≥ 0.135 (web framework)
- SQLModel ≥ 0.0.38 (ORM + Pydantic integration)
- asyncpg (async PostgreSQL driver)
- python-jose[cryptography] ≥ 3.3.0 (JWT signing/verification)
- passlib[bcrypt] ≥ 1.7.4 (password hashing)
- structlog ≥ 25.5.0 (structured logging)
- pydantic-settings ≥ 2.13.1 (configuration)

**Storage**: PostgreSQL (Neon) with existing `users` table. New tables: `refresh_tokens`, `password_reset_tokens`.  
**Testing**: pytest + httpx + pytest-asyncio (80% service coverage target)  
**Target Platform**: Linux server (Docker containerized), HTTPS in production  
**Project Type**: Backend API (FastAPI service within monorepo)  
**Performance Goals**:
- Login success rate: ≥95% within 2 seconds (SC-001)
- Token validation: ≥99% under 100ms (SC-002)
- 1,000+ concurrent authenticated users (SC-004)

**Constraints**:
- OAuth2 token endpoint MUST use `application/x-www-form-urlencoded` (not JSON) per RFC 6749
- JWTs signed only (not encrypted) — never store passwords in token payload
- Refresh tokens stored hashed (SHA-256); raw tokens sent only to client
- CORS whitelist only (no `*` in production)
- All auth endpoints rate-limited

**Scale/Scope**:
- 3 auth endpoints (register, login), 3 token management (refresh, logout, me), 2 password reset (request, confirm) = 8 core endpoints
- 2 new DB tables, 2 new SQLModel model classes
- Service layer: `AuthService`, helper functions
- Target: Monorepo package `packages/backend`, integrated into existing FastAPI app

**Known Dependencies**:
- Existing `packages/backend` has models (`User` with auth fields already present), routes, config, DB layer
- Existing auth middleware (`middleware/auth.middleware.ts` — Note: this is TypeScript, likely old frontend middleware; backend has no current auth implementation)
- Need to verify current `users` table schema matches `models/user.py` (already read: fields present)
- Database URL in `.env` already configured per constitution

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Evaluated Against `.specify/memory/constitution.md`

| Gate | Status | Notes |
|------|--------|-------|
| **I. Monorepo-First** | ✅ PASS | Backend package `packages/backend` exists; new code lives entirely within |
| **II. Technology Stack** | ✅ PASS | Stack matches: Python 3.13, FastAPI, SQLModel, asyncpg, bcrypt, structlog. New deps: `python-jose[cryptography]`, `passlib[bcrypt]`, `slowapi` — all permissible |
| **III. Event-Driven Architecture** | N/A (auth layer) | Auth events (`auth.login.success`) logged via structlog but not domain events; no event bus integration needed |
| **IV. Relational DB Standards** | ✅ PASS | Uses async engine (`create_async_engine`), `AsyncSession`, parameterized queries via SQLModel, `pool_pre_ping=True` |
| **V. Test-First Development** | ✅ PASS | TDD workflow enforced: tests written before feature code. No LLM calls in tests (respx mocks) |
| **VI. API Contract Discipline** | ✅ PASS | All endpoints use Pydantic schemas (`schemas/auth.py`). Responses follow `{success, data/error}` envelope |
| **VII. Augmented Memory & RAG** | N/A | Auth service does not use vector DB or agents |
| **VIII. Security & Secrets** | ✅ PASS | JWT secrets via `.env` (no hardcode). bcrypt ≥12 rounds. Rate limiting planned. CORS whitelist. WWW-Authenticate headers present. Token rotation. |
| **IX. Simplicity & Anti-Abstraction** | ✅ PASS | Single `AuthService` class; no unnecessary abstractions; models are SQLModel; no wrapper layers around FastAPI/JWT |
| **X. Code Quality** | ✅ PASS | Type hints on all functions. Ruff lint/format. Async-first (`async def`). Proper package structure (`pyproject.toml`). |

**Gates Violations**: None. All constitutional requirements satisfied.

---

## Project Structure

### Documentation (this feature)

```text
specs/013-fastapi-jwt-auth/
├── spec.md                     # Feature specification (input)
├── plan.md                     # This file (architecture decisions)
├── research.md                 # Phase 0 research output
├── data-model.md               # Entity definitions & ERD
├── quickstart.md               # Implementation walkthrough
└── contracts/
    ├── schemas.py              # Pydantic request/response models
    ├── openapi.yaml            # OpenAPI 3.1 specification
    └── migration_001_refresh_tokens.sql   # Alembic migration script
```

### Source Code (repository root)

**Backend package** (`packages/backend`):

```text
packages/backend/
├── src/
│   ├── config/
│   │   ├── settings.py         # NEW: Settings (JWT, token expiry)
│   │   └── logging.py          # NEW: Structlog configuration
│   ├── models/
│   │   ├── user.py             # EXISTING: User, RefreshToken, PasswordResetToken
│   │   └── __init__.py
│   ├── services/
│   │   ├── auth_service.py     # NEW: AuthService class (password hash, JWT, token mgmt)
│   │   ├── email_service.py    # NEW: EmailService (SMTP wrapper)
│   │   └── __init__.py
│   ├── routes/
│   │   ├── auth.routes.py      # NEW: All 8 auth endpoints
│   │   └── __init__.py
│   ├── schemas/
│   │   └── auth.py             # NEW: Pydantic schemas for auth (imported from contracts)
│   ├── middleware/
│   │   └── rate_limit.middleware.py  # EXISTING: slowapi limiter (need to configure for auth)
│   ├── main.py                 # UPDATED: Lifespan, CORS, include_router(auth)
│   └── __tests__/
│       └── test_auth.py        # NEW: Full test suite (TDD)
├── pyproject.toml              # UPDATED: Add new dependencies
├── alembic.ini                 # UPDATED: Ensure migrations directory configured
├── .env                        # UPDATED: JWT_SECRET_KEY, token expiry settings
└── .env.example                # UPDATED: Template for new settings
```

**Structure Decision**: Existing monorepo structure retained. All auth code resides in `packages/backend` as a cohesive service layer. No new packages or directories created beyond conventional subdirectories (`config/`, `services/`, `schemas/`, `routes/`). The `user.py` model already contains `User`, `RefreshToken` classes — only `PasswordResetToken` needs to be added there (or as separate file if models grow).

---

## Complexity Tracking

No constitutional violations requiring justification.

---

## Phase 1 Deliverables

From the Phase 1 workflow, the following artifacts have been generated:

| Artifact | Path | Status |
|---|---|---|
| Technical Research | `research.md` | ✅ Complete |
| Data Model | `data-model.md` | ✅ Complete |
| API Contracts (schemas) | `contracts/schemas.py` | ✅ Complete |
| API Contracts (OpenAPI) | `contracts/openapi.yaml` | ✅ Complete |
| Database Migration | `contracts/migration_001_refresh_tokens.sql` | ✅ Complete |
| Quickstart Guide | `quickstart.md` | ✅ Complete |
| Agent Context Updated | CLAUDE.md | ✅ Complete |

**Next Phase**: `/sp.tasks` — Generate dependency-ordered task list with acceptance test cases for TDD workflow.

The plan is ready for implementation. All constitutional gates passed. Technical unknowns resolved via research. API contracts defined. Database migration prepared. Quickstart guide provides step-by-step implementation reference.
