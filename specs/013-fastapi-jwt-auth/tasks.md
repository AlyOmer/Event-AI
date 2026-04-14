---
feature: "013-fastapi-jwt-auth"
title: "FastAPI JWT Authentication with OAuth2"
branch: "013-fastapi-jwt-auth"
---

# Tasks: FastAPI JWT Authentication with OAuth2

**Input**: Design documents from `/specs/013-fastapi-jwt-auth/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: TDD is REQUIRED. Write tests BEFORE implementation for each user story using `pytest-asyncio` and `httpx`. Target: 80% service coverage, 70% route coverage. Mock LLM and external API calls with `respx`. No live network calls during tests.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: User story label (US1, US2, US3). Omit for Setup, Foundational, Polish.
- Include exact file paths.

## Path Conventions (per plan.md)

- Backend root: `packages/backend/`
- Python source: `packages/backend/src/`
- Models: `packages/backend/src/models/`
- Services: `packages/backend/src/services/`
- Routes: `packages/backend/src/routes/`
- Schemas: `packages/backend/src/schemas/`
- Config: `packages/backend/src/config/`
- Middleware: `packages/backend/src/middleware/`
- Tests: `packages/backend/src/__tests__/`
- Migrations: `packages/backend/` (Alembic in root per plan.md)
- Package config: `packages/backend/pyproject.toml`

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Verify project structure and install required dependencies.

- [ ] T001 [P] Verify `packages/backend/pyproject.toml` exists and add missing dependencies: `python-jose[cryptography]`, `passlib[bcrypt]`, `slowapi` (for rate limiting). Ensure dev deps include `pytest`, `pytest-asyncio`, `httpx`. Run `uv sync` in `packages/backend/`.
- [ ] T002 [P] Create or update `packages/backend/.env` from `.env.example` with JWT settings: generate JWT_SECRET_KEY (32+ chars with `secrets.token_urlsafe(32)`), set `JWT_ALGORITHM="HS256"`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=7`.
- [ ] T003 [P] Verify database connection: ensure `DATABASE_URL` in `.env` is correct; test connectivity with a small async script or `alembic current`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

⚠️ **CRITICAL**: Phase 2 must complete before Phases 3–5.

### Database & Models

- [ ] T004 [P] Add `PasswordResetToken` model to `packages/backend/src/models/user.py` (table=True, fields: id PK UUID, user_id FK, token_hash VARCHAR(255), expires_at TIMESTAMPTZ, used_at TIMESTAMPTZ nullable, created_at). Index on `token_hash`. Ensure foreign key `ondelete=CASCADE`.
- [ ] T005 [P] In `packages/backend/src/models/__init__.py`, export `PasswordResetToken` alongside existing `User`, `RefreshToken`.

### Configuration

- [ ] T006 [P] Update existing `packages/backend/src/config/database.py`: Extend `Settings` class to include JWT fields: `jwt_secret_key`, `jwt_algorithm` (default "HS256"), `access_token_expire_minutes` (15), `refresh_token_expire_days` (7), and `cors_origins` with validator to split comma-separated env var. Add field validator for CORS parsing.
- [ ] T007 [P] (Already satisfied) The `get_session` dependency and async engine already exist in `database.py`. No new file needed.

### Auth Service

- [ ] T008 [P] Create `packages/backend/src/services/auth_service.py`: Implement `hash_password(password: str) -> str` using `passlib` bcrypt with rounds=12; `verify_password(plain, hashed) -> bool`.
- [ ] T009 [P] In `auth_service.py`, add `_generate_token_hash(token: str) -> str` using SHA-256 hex digest.
- [ ] T010 [P] In `auth_service.py`, add `create_access_token(user: User) -> tuple[str, int]`: encode JWT with `python-jose`, claims: `sub` (user.id), `email`, `role`, `iat`, `exp` (now + 15min), `iss="event-ai"`. Return token and expires_in seconds.
- [ ] T011 [P] In `auth_service.py`, add `create_refresh_token(session: AsyncSession, user: User) -> tuple[str, datetime]`: generate raw token (`secrets.token_urlsafe(64)`), hash it, create `RefreshToken` record with `expires_at = now + 7 days`, commit, return (raw_token, expires_at).
- [ ] T012 [P] In `auth_service.py`, add `create_tokens(session: AsyncSession, user: User) -> Token`: calls `create_access_token` and `create_refresh_token`, returns `Token` Pydantic model.
- [ ] T013 [P] In `auth_service.py`, add `verify_access_token(token: str, session: AsyncSession) -> User`: decode JWT (verify secret, algorithm, issuer="event-ai"), extract `sub`, fetch user from DB, validate `is_active`, raise 401 on failure with `WWW-Authenticate: Bearer` header.
- [ ] T014 [P] In `auth_service.py`, add `verify_refresh_token(session: AsyncSession, raw_token: str) -> User`: hash token, query `RefreshToken` where `token_hash==`, `revoked_at IS NULL`, `expires_at > NOW()`. If not found raise 401. Return associated user.
- [ ] T015 [US1-US2] In `auth_service.py`, implement `rotate_refresh_token(session: AsyncSession, raw_token: str) -> Token`: find token via `verify_refresh_token` logic, set `revoked_at=NOW()`, call `create_tokens` for user, commit, return new tokens.
- [ ] T016 [US2] In `auth_service.py`, implement `revoke_refresh_token(session: AsyncSession, raw_token: str)`: hash token, update matching `RefreshToken` set `revoked_at=NOW()` where `revoked_at IS NULL`, commit. Raise 401 if rowcount == 0.
- [ ] T017 [US3] In `auth_service.py`, implement `reset_password(session: AsyncSession, user: User, new_password: str)`: hash new password, update user, call `revoke_all_refresh_tokens(user.id)`, return.
- [ ] T018 [US3] In `auth_service.py`, implement `revoke_all_refresh_tokens(session: AsyncSession, user_id: UUID)`: `UPDATE refresh_tokens SET revoked_at=NOW() WHERE user_id=? AND revoked_at IS NULL`.
- [ ] T019 [P] Add structured logging (`structlog`) to all public `AuthService` methods: log `user_id`, `email`, `action`, `success` fields.

### API Schemas (Pydantic)

- [ ] T020 [P] Create `packages/backend/src/schemas/auth.py` with:
  - `UserRegister`: email (EmailStr), password (str, min 12), first_name, last_name (optional, max 100), role (default "user", max 50).
  - `UserLogin`: username (EmailStr), password (str).
  - `Token`: access_token (str), token_type (default "bearer"), expires_in (int), refresh_token (str).
  - `RefreshTokenRequest`: refresh_token (str).
  - `LogoutRequest`: refresh_token (str).
  - `PasswordResetRequest`: email (EmailStr).
  - `PasswordResetConfirm`: token (str), new_password (str, min 12).
  - `UserRead`: id (UUID), email, first_name, last_name, role, is_active, email_verified, last_login_at, created_at. Config `from_attributes=True`.
  - `SuccessResponse`: success (bool, default True), message (str).
- [ ] T021 [P] In `packages/backend/src/schemas/__init__.py` (create if missing), export all auth schemas.

### Rate Limiting

- [ ] T022 [P] Existing `packages/backend/src/middleware/rate_limit.py` already provides `rate_limit_dependency` and `RateLimitMiddleware`. Ensure it's usable (imports correct, no errors). No new file needed.
- [ ] T023 [P] Existing `packages/backend/src/middleware/login_rate_limit.py` provides login-specific limiter with IP+email composite tracking. Ensure it's integrated into auth routes. No new file needed.

### Auth Routes

- [ ] T024 [P] Create `packages/backend/src/api/v1/auth.py`:
  - Import `APIRouter`, `Depends`, `HTTPException`, `Request`, `status`.
  - Define `router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])`.
  - Implement `POST /register`: validate `UserRegister`, check for existing user, `hash_password`, create `User`, `session.add/flush/commit`, call `AuthService.create_tokens`, return `Token`. Log with structlog. On duplicate email raise 409.
- [ ] T025 [US1] In `auth.py`, implement `POST /login`: query user by email; `verify_password`; on failure increment `failed_login_attempts` and check lockout (`locked_until`); on success reset `failed_login_attempts=0`, set `last_login_at=NOW()`, issue tokens, commit, return `Token`. Include `WWW-Authenticate: Bearer` header on 401.
- [ ] T026 [US1] In `auth.py`, implement `GET /me`: dependency `current_user: User = Depends(auth_service.verify_access_token)`; return `UserRead` model.
- [ ] T027 [US2] In `auth.py`, implement `POST /refresh`: accept `RefreshTokenRequest` body; call `AuthService.rotate_refresh_token`; return new `Token`.
- [ ] T028 [US2] In `auth.py`, implement `POST /logout`: accept `LogoutRequest`; call `AuthService.revoke_refresh_token`; return `SuccessResponse`.
- [ ] T029 [US3] In `auth.py`, implement `POST /password-reset-request`: accept `PasswordResetRequest`; find user by email (return 200 even if not found to prevent enumeration); generate token via `auth_service.create_password_reset_token`, store hash, commit; log token to console (dev); return `PasswordResetTokenResponse`. Apply rate limit dependency.
- [ ] T030 [US3] In `auth.py`, implement `POST /password-reset-confirm`: accept `PasswordResetConfirm`; call `auth_service.verify_and_consume_password_reset_token`; call `auth_service.reset_password`; return `SuccessResponse`.

### Dependencies & Main App

- [ ] T031 [P] (Optional) Create `packages/backend/src/api/deps.py` if deps grow. Currently auth routes import `get_session` and `auth_service` directly, no separate deps needed. Skip unless adding more shared dependencies.
- [ ] T032 [P] Update `packages/backend/src/main.py`:
  - Import `auth_router` from `src.api.v1.auth`.
  - Ensure CORS middleware uses `CORS_ORIGIN` from env (already present); verify split and strip.
  - Include auth router: `app.include_router(auth_router, prefix="/api/v1")`.
  - Lifespan already exists from `config.database`.

**Checkpoint**: At this point, all foundational code and all user story code should be complete. Proceed to testing and validation.

---

## Phase 3: User Story 1 — Registration & Login (Priority: P1) 🎯 MVP

**Goal**: New users register and log in using OAuth2 password flow to receive JWT tokens and access protected endpoints.

**Independent Test**:
1. `POST /api/v1/auth/register` with valid email + strong password → 200 with `access_token`, `refresh_token`.
2. `POST /api/v1/auth/login` (form-encoded) with same credentials → 200 with new tokens.
3. `GET /api/v1/auth/me` with `Authorization: Bearer {access_token}` → 200 returning user profile.
4. Register duplicate email → 409 Conflict.
5. Login with wrong password → 401 Unauthorized.

### Tests for US1 (TDD: Write First)

- [ ] T033 [P] [US1] Write `test_register_success` in `packages/backend/src/__tests__/test_auth.py`: POST valid registration, assert 200, tokens in response, user created in DB.
- [ ] T034 [P] [US1] Write `test_register_duplicate_email`: register same email twice, second returns 409.
- [ ] T035 [P] [US1] Write `test_register_weak_password`: password <12 chars or missing complexity, assert 422 validation.
- [ ] T036 [P] [US1] Write `test_login_success`: after registration, login with correct credentials, assert 200 + tokens.
- [ ] T037 [P] [US1] Write `test_login_invalid_credentials`: wrong password, assert 401 with `WWW-Authenticate: Bearer`.
- [ ] T038 [P] [US1] Write `test_login_for_inactive_user`: set `is_active=False`, assert 401 or 403.
- [ ] T039 [P] [US1] Write `test_get_current_user_success`: call `/me` with valid token, assert 200 and correct user data.
- [ ] T040 [P] [US1] Write `test_get_current_user_without_token`: call `/me` with no auth, assert 401.
- [ ] T041 [P] [US1] Write `test_get_current_user_invalid_token`: send malformed/expired token, assert 401.

**Checkpoint**: All US1 tests must FAIL before implementation begins.

---

## Phase 4: User Story 2 — Token Refresh & Logout (Priority: P2)

**Goal**: Users refresh expired access tokens and log out to invalidate sessions.

**Independent Test**:
1. Login → get tokens.
2. `POST /api/v1/auth/refresh` with refresh token → 200 with NEW tokens, old refresh token invalidated.
3. Attempt reuse of old refresh token → 401.
4. `POST /api/v1/auth/logout` with refresh token → 200; same token reused → 401.
5. Access token remains valid until expiry; refresh is blocked.

### Tests for US2

- [ ] T042 [P] [US2] Write `test_refresh_token_success`: login, call `/refresh`, assert new tokens, assert old refresh token rejected.
- [ ] T043 [P] [US2] Write `test_refresh_invalid_token`: random token, assert 401.
- [ ] T044 [P] [US2] Write `test_refresh_expired_token`: manually create expired `RefreshToken`, assert 401.
- [ ] T045 [P] [US2] Write `test_logout_success`: login, logout with refresh token, assert 200, then old refresh token rejected.
- [ ] T046 [P] [US2] Write `test_logout_with_invalid_token`: logout with random token, assert 401.

**Checkpoint**: All US2 tests written and FAILING before implementation.

---

## Phase 5: User Story 3 — Password Reset (Priority: P3)

**Goal**: Registered users can securely reset forgotten passwords via time-limited tokens.

**Independent Test**:
1. `POST /api/v1/auth/password-reset-request` with registered email → 200, token recorded in DB (or logged).
2. Use that token with `POST /api/v1/auth/password-reset-confirm` + new strong password → 200, password updated in DB.
3. Reuse same token → 400 (already used).
4. Login with old password → fails; with new password → succeeds.
5. All existing refresh tokens invalidated after reset.

### Tests for US3

- [ ] T047 [P] [US3] Write `test_forgot_password_success`: registered user requests reset, assert 200, token record created in DB.
- [ ] T048 [P] [US3] Write `test_forgot_password_unregistered_email`: request with random email, still returns 200 (no enumeration leak).
- [ ] T049 [P] [US3] Write `test_reset_password_success`: after forgot-password, use token + new strong password, assert 200, password hash changed, old password fails.
- [ ] T050 [P] [US3] Write `test_reset_password_invalid_token`: random token, assert 400.
- [ ] T051 [P] [US3] Write `test_reset_password_expired_token`: manually set `expires_at` in past, assert 400.
- [ ] T052 [P] [US3] Write `test_reset_password_weak_password`: weak new password, assert 422 validation.
- [ ] T053 [P] [US3] Write `test_reset_password_single_use`: after successful reset, same token reused → 400.
- [ ] T054 [P] [US3] Write `test_reset_password_invalidates_all_sessions`: after reset, old refresh tokens should be revoked (query DB).

**Checkpoint**: All US3 tests written and FAILING before implementation.

---

## Phase 6: Integration & Migration

**Purpose**: Apply database migrations and verify end-to-end flow.

- [ ] T055 [P] Create Alembic migration (or raw SQL) for `password_reset_tokens` table if not auto-created. If using Alembic, generate revision: `uv run alembic revision --autogenerate -m "Add password_reset_tokens"`. Review migration file under `packages/backend/alembic/versions/`.
- [ ] T056 [P] Apply migrations to dev DB: `uv run alembic upgrade head`. Verify tables exist: `users`, `refresh_tokens`, `password_reset_tokens`.
- [ ] T057 [P] Run full test suite: `uv run pytest packages/backend/src/__tests__/ -v`. Ensure 100% pass, coverage ≥80%.
- [ ] T058 [P] Manual e2e verification with curl/HTTPie:
  1. Register → login → `/me` → `/refresh` → `/logout`.
  2. Rate limiting: 6 failed logins from same IP within 15min → 429 on 6th.
  3. Password reset: forgot → get token → reset → login with new password.
- [ ] T059 [P] Verify JWT token structure manually: decode access token (jwt.io or `jwt.decode(..., options={"verify_signature": False})`), confirm claims: `sub`, `email`, `role`, `iat`, `exp`, `iss="event-ai"`.
- [ ] T060 [P] Verify refresh tokens are stored hashed in DB (query `token_hash` column, confirm not plaintext).
- [ ] T061 [P] Confirm CORS preflight (OPTIONS) succeeds from allowed origins (check `Access-Control-Allow-Origin` header).

---

## Phase 7: Polish & Cross-Cutting

- [ ] T062 [P] Standardize all error responses to envelope `{"success": false, "error": {"code": "...", "message": "..."}}`. Update route handlers to raise `HTTPException(status_code, detail={"code": "...", "message": "..."})` or use custom exception handler in `main.py`.
- [ ] T063 [P] Add request-level structured logging via middleware: log `method`, `path`, `status_code`, `duration_ms`, `user_id` (if authenticated), `client_ip`. Use `structlog` in `packages/backend/src/middleware/logging.py` (or extend existing).
- [ ] T064 [P] Add unit tests for `auth_service.py` functions: `hash_password`/`verify_password` round-trip, `create_access_token` expiry check, `rotate_refresh_token` revocation logic, `revoke_refresh_token`, `reset_password` token invalidation.
- [ ] T065 [P] Add security tests: SQL injection attempt via email field (e.g., `email="admin'--"`) should be safely parameterized; JWT token with invalid signature must fail; token without `iss` claim or wrong `iss` must fail.
- [ ] T066 [P] Create API documentation: `packages/backend/docs/auth-api.md` with endpoint summary, request/response examples, error codes, rate limits.
- [ ] T067 [P] Create down migration: `packages/backend/alembic/versions/XXX_down.sql` or ensure Alembic downgrade drops `password_reset_tokens` and cleans up.
- [ ] T068 [P] Spec compliance audit: Map each FR-001–FR-014 and SC-001–SC-007 from `spec.md` to implemented features. Document any deviations in `docs/compliance.md`.

---

## Dependencies & Execution Order

### Story Completion Order (by Priority)

1. **US1** (P1) — Registration & Login → MVP complete
2. **US2** (P2) — Refresh & Logout → depends on US1 tokens
3. **US3** (P3) — Password Reset → independent

### Phase Dependencies

- **Phase 1 (Setup)** → no dependencies → start immediately.
- **Phase 2 (Foundational)** → depends on Phase 1 → **BLOCKS** all user stories.
- **Phase 3–5 (User Stories)** → can run in parallel after Phase 2 completes.
- **Phase 6 (Integration)** → depends on at least US1 complete (can run partial tests after each story).
- **Phase 7 (Polish)** → after all desired user stories complete.

### Within Each Story (TDD Order)

1. Write all failing tests for that story.
2. Implement models/schemas (if any new).
3. Implement service methods.
4. Implement route handlers.
5. Run tests → fix → green.

---

## Parallel Opportunities

- **Phase 1**: All tasks (T001–T003) are independent - can run simultaneously.
- **Phase 2 Foundational**:
  - Database models (T004–T005) — sequential within group.
  - Config/database setup (T006–T007) — parallel, no shared files.
  - Auth service functions (T008–T019) — different functions in same file; commit together after all written.
  - Schemas (T020–T021) — parallel (single file creation/update).
  - Rate limiting (T022–T023) — same module, can combine.
  - Routes (T024–T030) — sequential within file; write all route functions together in one commit.
  - Dependencies/main (T031–T032) — sequential (deps before main update).
- **User Stories** (after Phase 2): Each story (US1/US2/US3) can be implemented independently in parallel by different developers. Within each story:
  - Tests (T033–T041 for US1; T042–T046 for US2; T047–T054 for US3) — all parallel (different test functions).
  - Implementation — sequential per story (models → services → routes).
- **Phase 6**: T055 (migration) first, then T056–T061 mostly independent.
- **Phase 7**: All polish tasks (T062–T068) independent; can run in parallel.

### MVP Scope

Minimum Viable Product = **Phase 1 + Phase 2 + US1 (Phase 3)**.

Deliverable: Working registration + login + protected `/me` endpoint with JWT auth. US2 and US3 are post-MVP enhancements.

---

## Implementation Strategy

1. **Setup**: Install deps via `uv sync`, configure `.env`.
2. **Foundational**: Implement `AuthService`, models, schemas, rate limiting, route stubs.
3. **TDD Cycle per Story**:
   - Write tests (Red) → run → confirm failures.
   - Implement minimal code (Green) → run tests → debug until green.
   - Refactor (Refactor) — clean up, add logging, edge case handling.
4. **Integration**: Apply migrations, run full suite, manual curl verification.
5. **Polish**: Error envelope standardization, logging, security tests, documentation.

---

**Total Tasks**: 68 (T001–T068)
