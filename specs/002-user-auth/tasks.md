---
feature: "002-user-auth"
title: "User Authentication with JWT Tokens"
branch: "002-user-auth"
---

# Tasks: User Authentication with JWT Tokens

**Input**: Design documents from `/specs/002-user-auth/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), checklists/ (optional)

**Tests**: The feature constitution and plan mandate TDD. Tests are REQUIRED. For each user story, write contract and integration tests BEFORE implementation tasks. 80% service coverage, 70% route coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3). Omit for Setup, Foundational, Polish phases.
- Include exact file paths in descriptions.

## Path Conventions

- Backend source: `packages/backend/src/`
- Prisma schema: `packages/backend/prisma/schema.prisma` (create if missing)
- Environment: `packages/backend/.env.example`
- Tests: `packages/backend/src/__tests__/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure verification.

- [ ] T001 [P] Verify `packages/backend` directory structure exists with `src/routes`, `src/services`, `src/middleware`, `src/schemas`. Create missing directories if needed.
- [ ] T002 [P] Ensure required npm dependencies are installed: `fastify`, `prisma`, `@prisma/client`, `zod`, `jsonwebtoken`, `bcryptjs`, `@fastify/rate-limit`, `@fastify/cors`, `pino`, `speakeasy` (if 2FA kept), `qrcode` (if 2FA kept). Run `pnpm install` in `packages/backend`.
- [ ] T003 [P] Create or update `.env.example` in `packages/backend/` to document all required environment variables: `DATABASE_URL`, `JWT_SECRET` (256-bit random, min 32 chars), `JWT_REFRESH_SECRET` (256-bit random, min 32 chars), `JWT_ISSUER` (e.g., "EventAIVendorPortal"), `JWT_EXPIRES_IN=15m`, `JWT_REFRESH_EXPIRES_IN=7d`, `CORS_ALLOWED_ORIGINS`, `REDIS_URL` (if used for rate limiting), `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW_MS`, etc.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Database Schema

- [ ] T004 [P] Create or update Prisma schema at `packages/backend/prisma/schema.prisma` to include `User` model with fields: `id` (String @id), `email` (String @unique), `passwordHash` (String), `status` (String or enum with values: `active`, `suspended`), `lastLoginAt` (DateTime?). Add any other required fields from spec (FR-001, FR-002). If schema already exists, add missing fields via migration.
- [ ] T005 [P] Add `RefreshToken` model to schema with fields: `id` (String @id), `userId` (String, relation to User), `tokenHash` (String), `expiresAt` (DateTime), `revokedAt` (DateTime? optional), `createdAt` (DateTime @default(now())), `updatedAt` (DateTime @updatedAt).
- [ ] T006 Generate a new migration to apply schema changes. If using Prisma Migrate: `prisma migrate dev --name add-auth-models`. If using SQL migrations: create `packages/backend/src/db/migrations/012_add_auth_tables.sql` with CREATE TABLE for RefreshToken and ALTER TABLE for User if needed. Apply migration to development database.
- [ ] T007 Regenerate Prisma client: `prisma generate`. Verify `packages/backend/src/generated/client` includes updated models.

### Auth Service

- [ ] T008 [P] Confirm `packages/backend/src/services/auth.service.ts` uses bcrypt with at least 12 salt rounds (`SALT_ROUNDS=12`).
- [ ] T009 [P] Ensure `generateAccessToken` uses `config.jwt.expiresIn` set to 15 minutes and `generateRefreshToken` uses `config.jwt.refreshExpiresIn` set to 7 days with distinct secrets. Update `packages/backend/src/config/env.ts` to add `JWT_ISSUER` config and validate that `JWT_SECRET` and `JWT_REFRESH_SECRET` are at least 32 characters (256 bits); throw error if shorter.
- [ ] T010 [P] Add `clockTolerance: 30` (seconds) and `issuer: config.jwt.issuer` to `jwt.verify` options in `verifyAccessToken` and `verifyRefreshToken`, and update `generateAccessToken` and `generateRefreshToken` to include `issuer: config.jwt.issuer` in sign options to handle clock skew and verify token issuer (FR-006, FR-013).
- [ ] T011 Implement token rotation in `refreshTokens(refreshToken)` method:
  - Verify refresh token signature and payload.
  - Check that a corresponding `RefreshToken` record exists with matching tokenHash, is not revoked, and has not expired.
  - Revoke the old token (set `revokedAt`).
  - Create a new `RefreshToken` record with a new random token (hashed).
  - Return new access and refresh tokens.
- [ ] T012 Implement `logout(userId, refreshToken?)` to revoke refresh token(s) in the `RefreshToken` table: if `refreshToken` provided, revoke that specific token; else revoke all active tokens for the user.
- [ ] T013 Update `register` method to return both `accessToken` and `refreshToken` (in addition to vendor and user) upon successful registration. Store the refresh token in `RefreshToken` table.
- [ ] T014 Update `login` method to return both `accessToken` and `refreshToken` (already likely present). Ensure the refresh token is stored in `RefreshToken` table with hashed value.
- [ ] T015 Ensure `forgotPassword` generates a cryptographically random reset token (32 bytes), stores its hash with `passwordResetExpires` set to now + 1 hour in the `User` table. Do not reuse tokens.
- [ ] T016 Ensure `resetPassword` looks up user by reset token hash and unexpired, updates `passwordHash`, and invalidates all refresh tokens for that user (force re-login). Clear reset token fields after use.
- [ ] T017 Add structured Pino logging to all public methods of `AuthService`: include `userId`, `email`, `ip`, `action`, `success` fields. Log failures with error details but no sensitive data.

### Middleware & Rate Limiting

- [ ] T018 [P] Implement custom rate limiting middleware for `/login` (in a new or existing file, e.g., `src/middleware/failureRateLimit.middleware.ts` or extend `rateLimit.middleware.ts`):
  - Track failed login attempts by composite key `ip:email` using Redis (preferred) or in-memory store.
  - Allow maximum 5 failed attempts per 15-minute window.
  - Respond with HTTP 429 when limit exceeded. Include `retry-after` header.
- [ ] T019 [P] Implement rate limiting for `/register` by IP: maximum 10 attempts per hour. Use similar middleware or extend existing `authRateLimitConfig` to track registrations separately.
- [ ] T020 Wire the custom rate limiters to `/login` and `/register` routes in `auth.routes.ts` (apply as preHandler).
- [ ] T021 Verify `authMiddleware` (src/middleware/auth.middleware.ts) extracts Bearer token, verifies signature, issuer, expiration, and attaches `request.user` and `request.vendorId`. Confirm it returns proper 401 errors for missing/invalid tokens.
- [ ] T022 Implement `optionalAuthMiddleware` for endpoints that can optionally use authentication (e.g., public vendor routes that show extra info if logged in).
- [ ] T023 Ensure `requireRole(allowedRoles)` and `requireUserType(allowedTypes)` export correctly and are used on admin-only routes.

### Security & CORS

- [ ] T024 [P] In `packages/backend/src/index.ts`, configure `@fastify/cors` with explicit allowlist read from `CORS_ALLOWED_ORIGINS` environment variable (comma-separated). Disallow wildcard `*` in production.
- [ ] T025 [P] Audit all database access in `auth.service.ts` and other packages to ensure only Prisma parameterized queries are used. If any raw SQL exists, parameterize it.
- [ ] T026 [P] Update `.env.example` with all auth-related environment variables (list all that are needed, including JWT secrets, DB URL, CORS, rate limit settings).

### Validation Schemas

- [ ] T027 [P] Update `registerSchema` in `packages/backend/src/schemas/index.ts` to enforce minimum 12-character password (change `.min(8)` to `.min(12)`). Keep complexity rules: uppercase, lowercase, number, special character.
- [ ] T028 [P] Ensure `loginSchema`, `forgotPasswordSchema`, `resetPasswordSchema` are correctly defined and used in route validations.

---

## Phase 3: User Story 1 - User Registration and Login (Priority: P1) 🎯 MVP

**Goal**: As a new user, I can create an account and log in to securely access protected resources.

**Independent Test**:
1. `POST /register` with valid email + strong password → returns 201 with `accessToken` and `refreshToken`.
2. Use returned `accessToken` in `Authorization: Bearer` header to call a protected endpoint → succeeds (200).
3. `POST /login` with same credentials → returns 200 with new `accessToken` and `refreshToken`.
4. Attempt the same with incorrect password → returns 401 with clear error.
5. Try registering the same email again → returns 409 with appropriate error.

### Tests for User Story 1 (TDD: Write First)

- [ ] T029 [P] [US1] Write contract test for `POST /register` in `packages/backend/src/__tests__/contract/auth/register.contract.test.ts`: validates request schema, response status codes (201, 409, 400), and response shape. Use Supertest.
- [ ] T030 [P] [US1] Write integration test for happy-path registration flow in `packages/backend/src/__tests__/integration/auth/register.test.ts`: creates user, checks tokens in response, verifies user created in DB.
- [ ] T031 [P] [US1] Write contract test for `POST /login`.
- [ ] T032 [P] [US1] Write integration test for login flow: valid credentials → tokens; invalid credentials → 401; already registered email → success.
- [ ] T033 [P] [US1] Write test for auth middleware protecting a sample route (e.g., `GET /profile`): valid token → 200, missing token → 401, malformed token → 401.
- [ ] T034 [P] [US1] Write edge-case tests: duplicate registration, weak password (fails validation), extremely long inputs, concurrent registration attempts (if possible).

**Checkpoint**: All above tests must be written and FAIL before implementation begins.

### Implementation for User Story 1

- [ ] T035 [P] [US1] Update `POST /register` in `packages/backend/src/routes/auth.routes.ts` to return `accessToken` and `refreshToken` in the response body upon success (201). Include token fields in the JSON response.
- [ ] T036 [US1] In the register handler, ensure the `AuthService.register` method is called and then generate tokens (access & refresh) using the newly created user's data. Store refresh token hash in `RefreshToken` table.
- [ ] T037 [US1] Ensure `POST /login` returns both tokens (likely already) and stores refresh token in DB.
- [ ] T038 [US1] Apply custom rate limiters (T018, T019) to `/register` and `/login` routes.
- [ ] T039 [US1] Add audit logging for registration and login events in service methods (already covered in T017, but ensure they fire on these actions).
- [ ] T040 [US1] Verify that protected endpoints can be accessed using the access token returned by registration or login (e.g., test `GET /profile`).

**Checkpoint**: All tests for US1 should now pass. User Story 1 is independently functional.

---

## Phase 4: User Story 2 - Token Refresh and Secure Logout (Priority: P2)

**Goal**: As an authenticated user, I want to maintain my session securely and be able to log out.

**Independent Test**:
1. Log in to obtain access and refresh tokens.
2. Expire the access token (wait or modify expiry) → `POST /refresh-token` with refresh token returns new access and refresh tokens (200).
3. The old refresh token must be rejected after refresh (rotation).
4. `POST /logout` with refresh token → logs out; same refresh token used again → 401.
5. Call `/refresh-token` with logged-out refresh token → fails.

### Tests for User Story 2

- [ ] T041 [P] [US2] Write contract test for `POST /refresh-token`: valid refresh token → returns new tokens; invalid/expired → 401.
- [ ] T042 [P] [US2] Write integration test for token refresh flow: simulate access expiry, refresh, verify old refresh token invalidated.
- [ ] T043 [P] [US2] Write contract test for `POST /logout`: with valid refresh token → 200, token invalidated.
- [ ] T044 [P] [US2] Write integration test for logout: after logout, attempt refresh with same token → fails.
- [ ] T045 [P] [US2] Write test for refresh token reuse attack: use old refresh token after a successful refresh → should be rejected.

**Checkpoint**: Write tests first; ensure they fail.

### Implementation for User Story 2

- [ ] T046 [P] [US2] Implement `/refresh-token` endpoint in `auth.routes.ts` if not fully compliant: call `authService.refreshTokens`, return `{ accessToken, refreshToken }`. Ensure token rotation is enforced (old token revoked).
- [ ] T047 [US2] Implement `/logout` endpoint in `auth.routes.ts`: call `authService.logout` with user ID and refresh token from body. Return 200. Ensure `authMiddleware` protects this route.
- [ ] T048 [US2] In `AuthService.refreshTokens`, complete token rotation logic: after verifying old token and its DB record, mark it revoked and delete or update; create new `RefreshToken` record with hashed new token.
- [ ] T049 [US2] In `AuthService.logout`, revoke the provided refresh token (set `revokedAt`) or all tokens for the user if none provided (by setting `revokedAt` for all unrevoked tokens belonging to user).
- [ ] T050 [US2] Add audit logging for refresh and logout events (already in T017, ensure they are called).

**Checkpoint**: All US2 tests pass. US2 can be tested independently (e.g., after US1 is done, run US2 tests, or both together).

---

## Phase 5: User Story 3 - Password Reset (Priority: P3)

**Goal**: As a registered user who forgot my password, I can securely reset it.

**Independent Test**:
1. `POST /forgot-password` with a registered email → returns 200 (or 204). Confirm a reset token is stored (and email/in-app notification sent in demo mode).
2. Retrieve the reset token (from DB or mock) and `POST /reset-password` with new strong password → returns 200 with success message.
3. Attempt to use the same token again → returns 400 (invalid/expired).
4. Try to reset with an expired token → returns 400.
5. After reset, log in with old password → fails; with new password → succeeds.

### Tests for User Story 3

- [ ] T051 [P] [US3] Write contract test for `POST /forgot-password`: valid email → 200; invalid email format → 400.
- [ ] T052 [P] [US3] Write integration test for forgot-password flow: request reset, assert token generated in DB (or email sent in demo), token expiry set to 1 hour.
- [ ] T053 [P] [US3] Write contract test for `POST /reset-password`: valid token + strong password → 200; invalid/expired token → 400; weak password → 400.
- [ ] T054 [P] [US3] Write integration test for reset-password: use token, update password, verify old password no longer works, new password works.
- [ ] T055 [P] [US3] Write test for single-use token: after successful reset, same token cannot be used again.
- [ ] T056 [P] [US3] Write test for token expiry: manually expire token and ensure reset fails.

**Checkpoint**: Tests written and failing.

### Implementation for User Story 3

- [ ] T057 [P] [US3] Verify `POST /forgot-password` in `auth.routes.ts` uses `AuthService.forgotPassword`. Ensure it accepts email, generates reset token (with 1-hour expiry hash), and logs event. Response should be generic (do not reveal if email exists) per privacy best practice.
- [ ] T058 [P] [US3] Verify `POST /reset-password` uses `AuthService.resetPassword`. Ensure it validates token and expiry, hashes new password (using existing hash method), updates user, clears reset token fields, invalidates all refresh tokens for that user.
- [ ] T059 [US3] Add audit logging for password reset request and completion (already in T017; confirm usage).
- [ ] T060 [US3] Ensure password strength validation is enforced in the `resetPasswordSchema` (min 12 chars, complexity). If schema not used, add validation in route.

**Checkpoint**: All US3 tests pass. US3 independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize feature, ensure quality, performance, and documentation.

- [ ] T061 [P] Standardize JSON error response envelope across all auth endpoints: `{ error: string, message: string, code?: string, retryAfter?: number }`. Update any error replies that do not conform.
- [ ] T062 [P] Add global error handler in Fastify to catch uncaught exceptions and return sanitized error messages (no stack traces in production).
- [ ] T063 [P] Confirm CORS configuration uses explicit origins; test with frontend URL. Ensure no wildcard in production mode.
- [ ] T064 [P] Review all audit log statements for consistency: include `timestamp`, `userId`, `email`, `action` (e.g., 'login', 'logout', 'register', 'password_reset', 'refresh'), `ip`, `success` (boolean). Use a consistent logger format (JSON).
- [ ] T065 [P] Performance testing: Write simple load test script (e.g., using autocannon or k6) to measure login latency under moderate concurrency (100 requests). Target p95 < 200ms. Tune bcrypt rounds or use caching if needed (but spec says 12 rounds; ensure performance acceptable).
- [ ] T066 [P] Token validation latency: benchmark `authService.verifyAccessToken` repeatedly. Target p95 < 50ms. JWT verification should be fast.
- [ ] T067 [P] Security hardening: Test for common vulnerabilities:
  - SQL injection: attempt injection in login email field; ensure Prisma parameterization prevents.
  - XSS: not applicable to backend directly but ensure no reflected user input in error messages.
  - Token forgery: modify token signature → rejected.
  - Rate limit bypass: test with different IPs/email combos.
- [ ] T068 [P] Ensure all environment variables are documented and secrets are not committed. Verify in code that secrets are loaded from env and not defaulted in production.
- [ ] T069 [P] Update API documentation: Add auth endpoints to README or create `docs/auth-api.md` with request/response examples, error codes, rate limits, and sample usage (register → login → access profile → refresh → logout).
- [ ] T070 [P] Create a quickstart validation script (`scripts/validate-auth.sh` or Node script) that runs through the complete auth flow end-to-end using curl or fetch, verifying each step. This can be used for demos and CI sanity check.
- [ ] T071 [P] Create database rollback scripts for the changes made in Phase 2: down migration for RefreshToken table and any User model alterations. Store in `src/db/migrations/` with corresponding `down` SQL.
- [ ] T072 [P] Final review: create a checklist based on spec FRs and SC, verify each is met. Document any deviations or future work in `checklists/requirements.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS** all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - User stories can then proceed in parallel (if staffed) or sequentially in priority order (P1 → P2 → P3).
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - no dependencies on other stories.
- **User Story 2 (P2)**: Can start after Foundational - integrates with US1 endpoints but should be independently testable.
- **User Story 3 (P3)**: Can start after Foundational - independent of US1/US2 except for shared service utilities.

### Within Each User Story

- **Tests** (contract + integration) MUST be written and **fail** before implementation begins (TDD).
- **Schema/database** changes precede service updates.
- **Service methods** precede route handlers.
- **Core functionality** (happy path) before error handling and edge cases.
- **Story complete** before moving to next priority (though polish phase can start on completed stories).

### Parallel Opportunities

- **Phase 1** tasks (T001-T003) can all be executed in parallel.
- **Foundational** tasks within subgroups can run in parallel: Database tasks T004-T007 can be ordered but some like T004 and T005 (both schema edits) depend on each other; T006 migration depends on T004/T005; T007 depends on T006. Service tasks T008-T017 are mostly independent (different parts of the same file) and can be parallel if no overlapping changes; but if modifying the same file, better to do sequentially or use separate functions.
- After Foundational completes, all **User Story** phases can be implemented in parallel by different team members:
  - Developer A: US1 tests then impl.
  - Developer B: US2 tests then impl.
  - Developer C: US3 tests then impl.
- Within a story, test tasks (T029-T034 for US1) can all be written together. Implementation tasks may depend on each other: e.g., service changes before route changes; but multiple service methods can be done in parallel.
- **Polish** tasks T061-T072 can mostly be done in parallel across different aspects (performance, security, docs, rollback).

### Example Parallel Execution: User Story 1

```bash
# Write all tests for US1 together:
- T029, T030, T031, T032, T033, T034

# Implement service/token generation in parallel:
- T008, T009, T010, T011, T012, T013, T014  (all modify auth.service.ts but different functions; may combine in one commit)

# Implement route changes:
- T035, T036, T037, T038 (modify auth.routes.ts)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (critical).
3. Complete Phase 3: User Story 1 (registration + login) – write tests first, then implementation.
4. **STOP and VALIDATE**: Run US1 integration tests individually, manually test with curl or Postman: register → login → access protected → logout.
5. If US1 passes all acceptance criteria, the MVP is ready for deployment/demo.

### Incremental Delivery

- Foundation → US1 (MVP) → US2 → US3 → Polish. Each story adds value without breaking previous ones.
- After each user story, run its tests independently and consider deploying the increment if it meets the acceptance criteria.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (pairing on schema and service).
2. Once Foundational done:
   - Developer A focuses on US1 (tests then impl).
   - Developer B focuses on US2.
   - Developer C focuses on US3.
3. After all three stories pass, the team reconverges on Polish & cross-cutting tasks (error handling, logging, docs, performance, security).

---

## Notes

- **[P]** tasks = can be run in parallel (different files, no direct dependencies). Still ensure to run tests after each change.
- **[Story]** label maps task to specific user story for traceability. Non-story phases omit label.
- Each user story should be independently completable and testable from start to finish.
- Follow TDD: write failing tests BEFORE implementing the corresponding code. Commit test-first then implementation.
- Commit after each task or logical group (e.g., all model changes, all service changes).
- Stop at any checkpoint to validate the story independently against the acceptance scenarios.
- Avoid: vague tasks, multiple developers editing the same file simultaneously without coordination, and cross-story dependencies that break independence.
- The 2FA endpoints present in the codebase are out of scope for this feature (spec does not require them) and can be left as-is or deferred to a future enhancement.
- If the Prisma schema file does not exist at `packages/backend/prisma/schema.prisma`, create it by extracting model definitions from the generated client or by designing a new schema that includes all required tables.

---

**Total Tasks (including this summary)**: ~72 checklist items. The actual implementation tasks count is approximately 72 (T001–T072).
