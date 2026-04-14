# Requirements Document

## Introduction

Phase 1 of the Event-AI platform (an AI-powered event planning marketplace for Pakistan) is approximately 85% complete across three modules: `003-database-setup`, `013-fastapi-jwt-auth`, and `002-user-auth`. This spec covers the five remaining gaps that must be closed to reach full Phase 1 compliance with the project constitution and original module specs.

The gaps are:
1. **OAuth2 Password Form** — login endpoint must accept `OAuth2PasswordRequestForm` (form-encoded), not JSON
2. **Test Suite API Mismatch** — existing tests reference a stale `AuthService` API; must be rewritten to match the current implementation
3. **Admin Seed Data** — no idempotent seed script exists for the initial admin user and event category lookup data
4. **Database Health Endpoint** — the existing `/health/database` endpoint is missing the `/api/v1/` prefix and does not return the full stats required by FR-009
5. **Standardized Error Envelope** — auth endpoints return raw `detail` strings; all responses must follow the constitution's `{"success": ..., "data/error": ...}` envelope

---

## Glossary

- **Backend**: The `packages/backend` FastAPI service — the primary REST API for the Event-AI platform.
- **AuthService**: The Python class `src/services/auth_service.py` that encapsulates all JWT and password operations.
- **OAuth2PasswordRequestForm**: FastAPI's built-in form dependency that parses `application/x-www-form-urlencoded` login requests with `username` and `password` fields.
- **Error_Envelope**: The standardized JSON response shape mandated by constitution §VI.2: `{"success": false, "error": {"code": "ERROR_CODE", "message": "..."}}` for errors and `{"success": true, "data": {...}, "meta": {}}` for successes.
- **Error_Code**: A namespaced string from the taxonomy `AUTH_*`, `VALIDATION_*`, `NOT_FOUND_*`, `CONFLICT_*`, `INTERNAL_*` used in error envelopes.
- **Seed_Script**: An idempotent Python script at `packages/backend/src/scripts/seed.py` that populates essential initial data.
- **Health_Endpoint**: The route `GET /api/v1/health/db` that reports database connection pool status, query latency, and basic DB statistics.
- **ASGITransport**: The `httpx` transport adapter that allows tests to call a FastAPI app in-process without a running server.
- **conftest**: The pytest `conftest.py` file that provides shared fixtures (test DB session, async HTTP client) for the test suite.

---

## Requirements

### Requirement 1: OAuth2 Password Form Login

**User Story:** As a frontend developer integrating the login flow, I want the `POST /api/v1/auth/login` endpoint to accept `application/x-www-form-urlencoded` data via `OAuth2PasswordRequestForm`, so that the endpoint is fully compliant with the OAuth2 password grant standard and the project constitution's anti-pattern rules.

#### Acceptance Criteria

1. WHEN a client sends `POST /api/v1/auth/login` with `Content-Type: application/x-www-form-urlencoded` and fields `username` and `password`, THE Backend SHALL authenticate the user and return a `Token` response with `access_token`, `token_type`, `expires_in`, and `refresh_token`.
2. WHEN a client sends `POST /api/v1/auth/login` with a JSON body instead of form-encoded data, THE Backend SHALL return HTTP 422 Unprocessable Entity.
3. THE Backend SHALL apply the existing per-email/IP rate limiter (5 failed attempts per 15 minutes) to the form-based login endpoint without modification to the rate-limiting logic.
4. WHEN login succeeds, THE Backend SHALL include `WWW-Authenticate: Bearer` in the response headers on any subsequent 401 from the same session, consistent with constitution §VIII.5.
5. IF the `username` field is not a valid email address, THEN THE Backend SHALL return HTTP 422 with a validation error before attempting any database lookup.
6. THE Backend SHALL remove the `UserLogin` Pydantic JSON schema dependency from the login route handler and replace it exclusively with `OAuth2PasswordRequestForm`.

---

### Requirement 2: Auth Test Suite Rewrite

**User Story:** As a backend engineer, I want a correct, passing test suite for the authentication module that targets the actual current `AuthService` API, so that CI enforces correctness and regressions are caught automatically.

#### Acceptance Criteria

1. THE Test_Suite SHALL use `pytest-asyncio`, `httpx.AsyncClient` with `ASGITransport`, and a dedicated in-memory or test-database session — zero real production DB calls.
2. WHEN `AuthService.create_access_token(user)` is called with a `User` object, THE Test_Suite SHALL assert the returned tuple is `(jwt_string, expires_in_seconds)` and that the JWT decodes to the correct `sub`, `email`, `role`, `iss` claims.
3. WHEN `AuthService.verify_access_token(token, session)` is called with a valid token and a session that returns the matching `User`, THE Test_Suite SHALL assert the returned value is a `User` object (not a dict).
4. WHEN `AuthService.create_refresh_token(session, user)` is called, THE Test_Suite SHALL assert the returned tuple is `(raw_token_string, expires_at_datetime)` and that a `RefreshToken` row is persisted with a SHA-256 hash of the raw token.
5. WHEN `AuthService.verify_refresh_token_raw(session, raw_token)` is called with a valid, non-revoked, non-expired token, THE Test_Suite SHALL assert the returned value is the associated `User` object.
6. WHEN `AuthService.rotate_refresh_token(session, raw_token)` is called, THE Test_Suite SHALL assert the old `RefreshToken` record has `revoked_at` set and a new token dict is returned.
7. THE Test_Suite SHALL cover the HTTP layer via `AsyncClient`: registration (201/409), login (200/401/422/429), `/me` (200/401), refresh (200/401), logout (200/401), password-reset-request (200), password-reset-confirm (200/400).
8. THE Test_Suite SHALL achieve ≥ 80% line coverage on `src/services/auth_service.py` and ≥ 70% on `src/api/v1/auth.py` as measured by `pytest-cov`.
9. THE Test_Suite SHALL delete or replace both stale test files (`packages/backend/tests/test_auth.py` and `packages/backend/src/__tests__/test_auth.py`) so no test references the old `AuthService` API.
10. IF a test requires a `User` object in the database, THEN THE Test_Suite SHALL insert it via the test session fixture rather than calling a real database.

---

### Requirement 3: Admin Seed Data Script

**User Story:** As a DevOps engineer deploying the platform for the first time, I want an idempotent seed script that creates the initial admin user and event category lookup data, so that the application is immediately usable after migrations without manual database intervention.

#### Acceptance Criteria

1. THE Seed_Script SHALL be located at `packages/backend/src/scripts/seed.py` and executable via `uv run python -m src.scripts.seed` from the `packages/backend` directory.
2. WHEN the Seed_Script runs and no admin user exists, THE Seed_Script SHALL create a `User` record with `role="admin"`, `is_active=True`, `email_verified=True`, and credentials read from environment variables `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD`.
3. WHEN the Seed_Script runs and an admin user with the configured email already exists, THE Seed_Script SHALL skip user creation and log a structured message indicating the record already exists (idempotent).
4. THE Seed_Script SHALL create the following event categories if they do not already exist (matched by `slug`): `Wedding`, `Corporate`, `Birthday`, `Mehndi`, `Baraat`, `Walima`, `Conference`, `Party`.
5. WHEN the Seed_Script runs and a category with a given `slug` already exists, THE Seed_Script SHALL skip that category's creation (idempotent upsert pattern).
6. IF `SEED_ADMIN_EMAIL` or `SEED_ADMIN_PASSWORD` environment variables are not set, THEN THE Seed_Script SHALL exit with a non-zero status code and a clear error message before attempting any database writes.
7. IF `SEED_ADMIN_PASSWORD` is shorter than 12 characters, THEN THE Seed_Script SHALL exit with a non-zero status code and a validation error message.
8. THE Seed_Script SHALL use `structlog` for all output (structured JSON) and SHALL NOT use `print()` statements.
9. THE Seed_Script SHALL use the same `AsyncSession` and `get_settings()` patterns as the rest of the Backend (Pydantic `BaseSettings` + `@lru_cache`, `asyncpg` driver).
10. WHEN the Seed_Script completes successfully, THE Seed_Script SHALL log a summary of records created vs. skipped for both users and categories.

---

### Requirement 4: Database Health Endpoint Under `/api/v1/`

**User Story:** As a system operator, I want a database health endpoint at `GET /api/v1/health/db` that returns connection pool status, query latency, and basic DB statistics, so that I can monitor database health through the versioned API path consistent with the rest of the Backend.

#### Acceptance Criteria

1. THE Backend SHALL expose `GET /api/v1/health/db` (not `/health/database`) returning HTTP 200 with a JSON body when the database is reachable.
2. WHEN the database is reachable, THE Health_Endpoint SHALL return a response containing: `status` ("healthy"), `latency_ms` (float, round-trip time for `SELECT 1`), `connection_pool` object with `total`, `active`, `idle`, and `idle_in_transaction` counts from `pg_stat_activity`, and `extensions.pgvector` ("enabled" or "not_installed").
3. IF the database is unreachable or throws an exception, THEN THE Health_Endpoint SHALL return HTTP 200 with `status` set to "unhealthy" and an `error` field containing the exception message (no stack trace exposed to the client).
4. THE Health_Endpoint SHALL complete its response within 500 milliseconds under normal load.
5. THE Backend SHALL register the health router under the `/api/v1/` prefix so the full path is `/api/v1/health/db`, consistent with constitution §VI.3.
6. THE Backend SHALL retain backward compatibility: if the old `/health/database` route is still registered, it SHALL be removed or redirected to avoid confusion.
7. WHEN the health response is returned, THE Health_Endpoint SHALL follow the Error_Envelope format for error cases: `{"success": false, "error": {"code": "INTERNAL_DB_HEALTH_ERROR", "message": "..."}}`.

---

### Requirement 5: Standardized Error Envelope

**User Story:** As a frontend developer consuming the auth API, I want all responses — both success and error — to follow the standardized `{"success": ..., "data/error": ...}` envelope defined in the project constitution, so that the frontend can handle all API responses with a single, consistent parsing strategy.

#### Acceptance Criteria

1. THE Backend SHALL register a global exception handler in `src/main.py` that catches `HTTPException` and returns a JSON body matching `{"success": false, "error": {"code": "<Error_Code>", "message": "<detail>"}}` with the original HTTP status code.
2. WHEN `POST /api/v1/auth/register` succeeds, THE Backend SHALL return `{"success": true, "data": {<Token fields>}, "meta": {}}`.
3. WHEN `POST /api/v1/auth/register` fails with a duplicate email, THE Backend SHALL return HTTP 409 with `{"success": false, "error": {"code": "CONFLICT_EMAIL_EXISTS", "message": "Email already registered"}}`.
4. WHEN `POST /api/v1/auth/login` fails with invalid credentials, THE Backend SHALL return HTTP 401 with `{"success": false, "error": {"code": "AUTH_INVALID_CREDENTIALS", "message": "Incorrect email or password"}}` and the `WWW-Authenticate: Bearer` header.
5. WHEN `POST /api/v1/auth/login` fails because the account is locked, THE Backend SHALL return HTTP 403 with `{"success": false, "error": {"code": "AUTH_ACCOUNT_LOCKED", "message": "Account locked due to multiple failed login attempts."}}`.
6. WHEN any endpoint receives a request that fails Pydantic validation, THE Backend SHALL return HTTP 422 with `{"success": false, "error": {"code": "VALIDATION_ERROR", "message": "<Pydantic error summary>"}}`.
7. WHEN `POST /api/v1/auth/refresh` or `POST /api/v1/auth/logout` receives an invalid or revoked refresh token, THE Backend SHALL return HTTP 401 with `{"success": false, "error": {"code": "AUTH_INVALID_REFRESH_TOKEN", "message": "Invalid or expired refresh token"}}`.
8. WHEN `GET /api/v1/auth/me` is called without a valid Bearer token, THE Backend SHALL return HTTP 401 with `{"success": false, "error": {"code": "AUTH_CREDENTIALS_INVALID", "message": "Could not validate credentials"}}` and the `WWW-Authenticate: Bearer` header.
9. THE Backend SHALL add a `RequestValidationError` handler alongside the `HTTPException` handler so Pydantic 422 errors also follow the Error_Envelope format.
10. WHERE the `Token` response schema is used, THE Backend SHALL wrap it in the success envelope: `{"success": true, "data": {"access_token": "...", "token_type": "bearer", "expires_in": 900, "refresh_token": "..."}, "meta": {}}`.
11. THE Backend SHALL NOT change the HTTP status codes of any existing endpoint — only the response body shape changes to match the Error_Envelope.

