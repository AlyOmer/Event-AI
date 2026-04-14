# Implementation Plan: User Authentication with JWT Tokens

**Branch**: `feature/user-auth` | **Date**: 2026-04-07 | **Spec**: [spec.md](file:///home/ali/Desktop/Event-AI-Latest/specs/002-user-auth/spec.md)
**Input**: Feature specification from `/specs/002-user-auth/spec.md`

## Summary

Implements secure user authentication using JWT access + refresh tokens, bcrypt password hashing, rate-limited login/registration endpoints, and password reset flow. All endpoints use Zod validation, structured Pino logging, and strict CORS configuration. The auth middleware enforces token verification on all protected routes across the platform.

## Technical Context

**Language/Version**: Node.js ≥ 20 (Backend)
**Primary Dependencies**: Fastify, Prisma, Zod, jsonwebtoken, bcryptjs
**Storage**: Neon DB (PostgreSQL) via Prisma
**Testing**: Jest + Supertest (Backend)
**Target Platform**: REST API consumed by Next.js portals
**Performance Goals**: Login < 200ms p95, token validation < 50ms
**Constraints**: JWT secrets MUST be 256-bit random; no default/dev fallback in production
**Scale/Scope**: Foundation — all other features depend on this.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Security (§VIII)**: bcrypt ≥ 12 rounds, 256-bit JWT secrets, CORS configured, rate limiting on auth endpoints.
- [x] **API Contracts (§VI)**: Zod schemas for all request/response, standardized error envelope, `/api/v1/` prefix.
- [x] **No Banned Practices**: No hardcoded secrets, no `any` types, no wildcard CORS.
- [x] **Test-First (§V)**: Jest + Supertest for route integration tests, 80% service coverage.

## Project Structure

### Documentation

```text
specs/002-user-auth/
├── plan.md              # This file
├── spec.md              # Feature specification
└── checklists/          # Quality checklists
```

### Source Code Context

```text
packages/backend/
├── src/
│   ├── routes/
│   │   ├── auth.routes.ts            # Registration, login, refresh, logout, password reset
│   │   └── user-auth.routes.ts       # User-facing auth (may merge)
│   ├── services/
│   │   └── auth.service.ts           # JWT sign/verify, password hashing, token rotation
│   ├── middleware/
│   │   └── auth.middleware.ts         # Token extraction & verification on protected routes
│   └── __tests__/
│       └── auth.test.ts              # Route + service integration tests
```

## Phase 1: Database & Auth Service Foundation

**Context**: The User model must include hashed password, status fields, and a RefreshToken table for token rotation and invalidation.

**Tasks**:
1. Verify `User` model in `schema.prisma` includes: `email` (unique), `passwordHash`, `status` (active/suspended), `lastLoginAt`.
2. Verify `RefreshToken` model exists with: `userId`, `tokenHash`, `expiresAt`, `revokedAt`.
3. Implement `auth.service.ts`: `hashPassword()`, `verifyPassword()`, `signAccessToken()`, `signRefreshToken()`, `verifyAccessToken()`, `rotateRefreshToken()`.
4. Access/refresh token expiry: 15 min / 7 days respectively.

## Phase 2: Auth Route Endpoints

**Context**: All auth endpoints under `/api/v1/auth/` must use Zod validation and return standardized envelopes.

**Tasks**:
1. `POST /register` — validate email + password strength (≥12 chars), hash password, create user, return access + refresh tokens.
2. `POST /login` — verify credentials, issue token pair, update `lastLoginAt`.
3. `POST /refresh` — accept refresh token, validate, rotate (invalidate old, issue new pair).
4. `POST /logout` — revoke the refresh token.
5. `POST /forgot-password` — generate a time-limited reset token (1 hour TTL), trigger `password.reset_requested` domain event.
6. `POST /reset-password` — validate reset token, update password hash, invalidate token.
7. Apply `@fastify/rate-limit` per constitution: 5 req/min on login, 10 reg/hr per IP.

## Phase 3: Auth Middleware & RBAC

**Context**: Every protected endpoint must pass through `authMiddleware` which extracts and verifies the JWT from the `Authorization: Bearer` header.

**Tasks**:
1. Implement `authMiddleware` in `auth.middleware.ts`: extract token, verify, attach `request.user`.
2. Support query-param token fallback for SSE endpoints (EventSource limitation).
3. Implement `requireRole()` and `requirePermission()` guards for RBAC enforcement.
4. Wire middleware into all existing and future route files.

## Phase 4: Security Hardening

**Context**: Constitution mandates explicit CORS, SQL injection prevention, and audit logging.

**Tasks**:
1. Configure `@fastify/cors` with explicit origin allowlist (no wildcard `*` in production).
2. Verify Prisma parameterized queries prevent SQL injection.
3. Log all auth events (register, login, logout, failed attempts, password reset) via Pino structured JSON.
4. Ensure `.env.example` documents all required auth environment variables.

## Phase 5: Testing

**Context**: TDD is non-negotiable. 80% coverage on services, 70% on routes.

**Tasks**:
1. Unit tests for `auth.service.ts`: password hashing, token signing/verification, token rotation.
2. Integration tests for all 6 auth endpoints via Supertest: happy paths + error paths.
3. Rate-limit verification: confirm 6th login attempt within 1 min returns 429.
4. RBAC tests: non-admin token on admin-only route returns 403.
