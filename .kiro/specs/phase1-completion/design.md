# Design Document: Phase 1 Completion

## Overview

Five targeted fixes to close the remaining Phase 1 gaps in `packages/backend`. All changes are confined to the FastAPI backend service. No new packages, no new services.

---

## Architecture

### Gap 1 — OAuth2 Password Form Login

**File**: `packages/backend/src/api/v1/auth.py`

Replace `user_in: UserLogin` with `form_data: OAuth2PasswordRequestForm = Depends()` in the `login` handler. Read `form_data.username` and `form_data.password` instead of `user_in.username` / `user_in.password`. The `UserLogin` schema is no longer used by the route but can remain in `schemas/auth.py` for reference.

```python
from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(login_limiter),
):
    ...
    result = await session.execute(select(User).where(User.email == form_data.username))
```

---

### Gap 2 — Auth Test Suite Rewrite

**Files**:
- Delete: `packages/backend/tests/test_auth.py`
- Delete: `packages/backend/src/__tests__/test_auth.py`
- Create: `packages/backend/tests/conftest.py` — shared fixtures (in-memory SQLite async engine, `AsyncClient` with `ASGITransport`)
- Create: `packages/backend/tests/test_auth_service.py` — unit tests for `AuthService` methods
- Create: `packages/backend/tests/test_auth_routes.py` — HTTP integration tests via `AsyncClient`

**Test DB strategy**: Use SQLite in-memory (`sqlite+aiosqlite:///:memory:`) with `SQLModel.metadata.create_all` in the fixture. Override `get_session` dependency via `app.dependency_overrides`.

---

### Gap 3 — Admin Seed Script

**File**: `packages/backend/src/scripts/seed.py`

Standalone async script using `asyncio.run()`. Uses the existing `engine` from `config/database.py` and `AsyncSession`. Reads `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` from env via `get_settings()` extended with two optional fields. Uses `select(...).where(...)` + upsert pattern (insert if not exists).

Categories seeded with a `slug` field derived from lowercased name (e.g. `"wedding"`). Matched by `name` since `Category` model has `name` as unique.

---

### Gap 4 — DB Health Endpoint at `/api/v1/health/db`

**Files**:
- `packages/backend/src/api/health.py` — rename route from `/database` to `/db`, update response to follow error envelope on failure
- `packages/backend/src/main.py` — change `app.include_router(health_router)` to `app.include_router(health_router, prefix="/api/v1")`

The existing logic (SELECT 1, pg_stat_activity, pg_extension) is correct — only the path and error shape need updating.

---

### Gap 5 — Standardized Error Envelope

**File**: `packages/backend/src/main.py`

Add two exception handlers after app creation:

```python
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": _infer_code(exc), "message": exc.detail}},
        headers=getattr(exc, "headers", None),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(exc.errors())}},
    )
```

`_infer_code()` maps HTTP status → error code prefix using the detail string or status code:
- 401 → `AUTH_*`
- 403 → `AUTH_ACCOUNT_LOCKED`
- 409 → `CONFLICT_*`
- 404 → `NOT_FOUND_*`
- 500 → `INTERNAL_*`

Auth route `HTTPException` `detail` strings are updated to structured dicts `{"code": "AUTH_INVALID_CREDENTIALS", "message": "..."}` so the handler can pass them through directly.

---

## Data Models

No new database tables. The `Category` model already exists with `name` (unique), `is_active`, `display_order`. Seed script uses it directly.

`Settings` in `config/database.py` gains two optional fields:
```python
seed_admin_email: Optional[str] = None
seed_admin_password: Optional[str] = None
```

---

## Error Code Mapping

| Scenario | HTTP | Code |
|---|---|---|
| Duplicate email on register | 409 | `CONFLICT_EMAIL_EXISTS` |
| Invalid credentials on login | 401 | `AUTH_INVALID_CREDENTIALS` |
| Account locked | 403 | `AUTH_ACCOUNT_LOCKED` |
| Invalid/expired refresh token | 401 | `AUTH_INVALID_REFRESH_TOKEN` |
| Invalid/expired reset token | 400 | `AUTH_INVALID_RESET_TOKEN` |
| No/bad Bearer token | 401 | `AUTH_CREDENTIALS_INVALID` |
| Pydantic validation failure | 422 | `VALIDATION_ERROR` |
| DB health check failure | 200 | `INTERNAL_DB_HEALTH_ERROR` |

---

## File Change Summary

| File | Action |
|---|---|
| `src/api/v1/auth.py` | Replace `UserLogin` with `OAuth2PasswordRequestForm`; update `detail` strings to structured dicts |
| `src/api/health.py` | Rename route `/database` → `/db`; wrap error response in envelope |
| `src/main.py` | Add `/api/v1` prefix to health router; add `HTTPException` + `RequestValidationError` handlers; remove `os.getenv` CORS hack |
| `src/config/database.py` | Add optional `seed_admin_email` / `seed_admin_password` fields to `Settings` |
| `src/scripts/seed.py` | Create new idempotent seed script |
| `tests/conftest.py` | Create shared test fixtures |
| `tests/test_auth_service.py` | Create unit tests for `AuthService` |
| `tests/test_auth_routes.py` | Create HTTP integration tests |
| `tests/test_auth.py` | Delete (stale) |
| `src/__tests__/test_auth.py` | Delete (stale) |
