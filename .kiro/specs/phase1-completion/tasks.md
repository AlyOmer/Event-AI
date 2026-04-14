# Tasks: Phase 1 Completion

**Spec**: `.kiro/specs/phase1-completion/`
**Branch**: `phase1-completion`

---

## Task List

- [x] 1. Fix OAuth2 Password Form Login
  - [x] 1.1 Replace `UserLogin` JSON body with `OAuth2PasswordRequestForm` in `packages/backend/src/api/v1/auth.py` login handler
  - [x] 1.2 Update all references from `user_in.username` / `user_in.password` to `form_data.username` / `form_data.password`

- [x] 2. Standardize Error Envelope
  - [x] 2.1 Add `HTTPException` and `RequestValidationError` global handlers in `packages/backend/src/main.py`
  - [x] 2.2 Update auth route `HTTPException` detail strings to structured dicts with `code` and `message` fields
  - [x] 2.3 Fix CORS config in `main.py` to use `settings.cors_origins` instead of raw `os.getenv`

- [x] 3. Fix Database Health Endpoint
  - [x] 3.1 Rename route from `/database` to `/db` in `packages/backend/src/api/health.py`
  - [x] 3.2 Wrap unhealthy response in error envelope format in `packages/backend/src/api/health.py`
  - [x] 3.3 Add `/api/v1` prefix to health router registration in `packages/backend/src/main.py`

- [x] 4. Create Admin Seed Script
  - [x] 4.1 Add optional `seed_admin_email` and `seed_admin_password` fields to `Settings` in `packages/backend/src/config/database.py`
  - [x] 4.2 Create `packages/backend/src/scripts/__init__.py`
  - [x] 4.3 Create idempotent `packages/backend/src/scripts/seed.py` with admin user and category seeding

- [x] 5. Rewrite Auth Test Suite
  - [x] 5.1 Delete stale `packages/backend/tests/test_auth.py`
  - [x] 5.2 Delete stale `packages/backend/src/__tests__/test_auth.py`
  - [x] 5.3 Create `packages/backend/tests/conftest.py` with async test DB and `AsyncClient` fixtures
  - [x] 5.4 Create `packages/backend/tests/test_auth_service.py` with unit tests matching current `AuthService` API
  - [x] 5.5 Create `packages/backend/tests/test_auth_routes.py` with HTTP integration tests
