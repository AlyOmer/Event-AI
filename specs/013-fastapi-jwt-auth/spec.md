# Feature Specification: FastAPI JWT Authentication with OAuth2

**Feature Branch**: `013-fastapi-jwt-auth`  
**Created**: 2026-04-08  
**Status**: Draft  
**Input**: User description: "Implement JWT authentication for FastAPI agents using OAuth2 password flow"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - User Registration and Login (Priority: P1)

As a new user, I want to create an account and log in using OAuth2 password flow to securely access protected API endpoints.

**Why this priority**: This is the foundational authentication flow. Without registration and login, no authenticated user can access the system. This delivers the minimum viable product for security using standard OAuth2 patterns.

**Independent Test**: Can be fully tested by registering a new user, logging in with OAuth2 password flow, receiving JWT access and refresh tokens, and using the access token to access a protected endpoint.

**Acceptance Scenarios**:

1. **Given** I am not logged in, **When** I register with a valid email and strong password, **Then** my account is created and I receive both an access token and a refresh token.

2. **Given** I have a registered account, **When** I log in using OAuth2 password flow with correct credentials, **Then** I receive an access token (short-lived) and a refresh token (long-lived).

3. **Given** I have a valid access token, **When** I include it in the Authorization header (Bearer) of a request to a protected endpoint, **Then** the request succeeds and I receive the protected data.

4. **Given** I enter incorrect credentials during login, **When** I attempt to log in, **Then** I receive a 401 Unauthorized response with a clear error message and no tokens are issued.

---

### User Story 2 - Token Refresh and Secure Logout (Priority: P2)

As an authenticated user, I want to refresh my access token when it expires and be able to log out to terminate my session securely.

**Why this priority**: Essential for maintaining long-lived sessions without requiring frequent re-authentication. Logout provides user control and security. Builds on P1.

**Independent Test**: Can be tested by logging in, allowing the access token to expire (or manually invalidating it), using the refresh token to obtain a new access token, and then logging out to invalidate the refresh token.

**Acceptance Scenarios**:

1. **Given** my access token has expired, **When** I submit my refresh token to the token refresh endpoint, **Then** I receive a new access token and a new refresh token (rotation pattern), and the old refresh token is invalidated.

2. **Given** I am logged in, **When** I log out by submitting my refresh token, **Then** that refresh token is invalidated and cannot be used to obtain new access tokens.

3. **Given** I attempt to use a refresh token that has been invalidated (after logout or compromised), **When** I try to refresh, **Then** the request fails with 401 Unauthorized and I must log in again.

---

### User Story 3 - Password Reset (Priority: P3)

As a registered user who forgot my password, I want to securely reset my password via email so that I can regain access to my account.

**Why this priority**: Important for usability and account recovery, but not required for initial MVP. Can be implemented after core auth flows are stable.

**Independent Test**: Can be tested by requesting a password reset with a registered email, receiving a reset token (via email or test harness), and using it to set a new password.

**Acceptance Scenarios**:

1. **Given** I have an account but forgot my password, **When** I request a password reset with my email, **Then** the system generates a one-time reset token valid for 1 hour and triggers a password reset email (or returns token for testing).

2. **Given** I have a valid reset token, **When** I submit a new strong password, **Then** my password is updated, the reset token is invalidated, and all existing sessions are terminated.

3. **Given** I attempt to use an expired or invalid reset token, **When** I try to reset the password, **Then** the request fails with 400 Bad Request and I must request a new reset token.

---

### Edge Cases

- What happens when a user tries to register with an email that already exists? The system should return 409 Conflict with a clear error message suggesting login or password reset.

- What happens when a user enters their password incorrectly multiple times? The system should implement rate limiting (5 failed attempts per 15 minutes) and lock the account temporarily after repeated failures. Return 429 Too Many Requests when locked.

- What happens when an access token is tampered with or forged? The system must detect invalid signatures and reject the request with 401 Unauthorized.

- What happens when a refresh token is stolen and used by an attacker? Token rotation mitigates this: old refresh token is invalidated when new one is issued. Compromised sessions can be detected by examining token usage patterns.

- What happens when the system's clock is out of sync (token expiration issues)? Tokens use UTC timestamps and a small clock skew buffer (e.g., 30 seconds) to account for clock drift.

- What happens during database outage when validating credentials? The system should return an appropriate 503 Service Unavailable error and not expose internal details to the user.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow users to register by providing an email address and a strong password (minimum 12 characters, including uppercase, lowercase, numbers, and special characters).

- **FR-002**: The system MUST securely store user passwords using bcrypt (or passlib with bcrypt) with at least 12 salt rounds, never storing plaintext or reversibly encrypted passwords.

- **FR-003**: The system MUST authenticate users by verifying their credentials against stored hashed passwords and issuing JWT access tokens upon successful login using OAuth2 password grant.

- **FR-004**: The system MUST issue JWT access tokens with a short expiration (15 minutes) containing claims: `sub` (user ID), `email`, `role`, `vendor_id`, `iat`, `exp`, `iss` (issuer).

- **FR-005**: The system MUST issue refresh tokens with longer expiration (7 days) that can be exchanged for new access tokens, implementing refresh token rotation (old token invalidated upon use).

- **FR-006**: The system MUST validate access tokens on every request to protected endpoints by verifying signature, expiration, and issuer using OAuth2PasswordBearer.

- **FR-007**: The system MUST allow users to log out by invalidating their refresh token, preventing further token refreshes.

- **FR-008**: The system MUST implement rate limiting on authentication endpoints:
  - Login: 5 failed attempts per 15 minutes per email/IP combination
  - Registration: 10 attempts per hour per IP address
  - Token refresh: not rate-limited (but limited by token validity)

- **FR-009**: The system MUST allow users to request a password reset, generating a single-use time-limited reset token (expires in 1 hour) that can be used to set a new password.

- **FR-010**: The system MUST log all authentication events (registration, login, logout, failed attempts, password reset) with structured JSON for security auditing.

- **FR-011**: The system MUST protect against common security vulnerabilities: use parameterized queries (SQLAlchemy/SQLModel) to prevent SQL injection, validate all inputs with Pydantic, and configure CORS appropriately.

- **FR-012**: The system MUST use HTTPS for all authentication endpoints in production to prevent token interception.

- **FR-013**: The system MUST store tokens securely (access tokens in memory on client; refresh tokens in HTTP-only secure cookies or secure client storage with CSRF protection). Server-side, refresh tokens must be hashed before storage.

- **FR-014**: The system MUST implement OAuth2 password grant with `OAuth2PasswordRequestForm` supporting `username` (email) and `password` fields, returning `access_token`, `token_type`, `expires_in`, and `refresh_token` in the response.

### Key Entities

- **User**: Represents a registered user. Attributes: email (unique), password_hash (bcrypt), first_name, last_name, role (e.g., admin, user), is_active, email_verified, created_at, updated_at, last_login_at.

- **RefreshToken**: Represents a long-lived token that can be exchanged for new access tokens. Attributes: user_id (FK), token_hash (SHA-256), expires_at, revoked_at, created_at, updated_at. The actual token is randomly generated and hashed before storage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of login attempts (with correct credentials) succeed and issue tokens within 2 seconds.
- **SC-002**: 99% of access token validations complete in under 100 milliseconds.
- **SC-003**: User password reset emails are sent within 30 seconds of request (or token generated for testing).
- **SC-004**: The system supports at least 1,000 concurrent authenticated users without performance degradation.
- **SC-005**: 90% of users successfully complete registration or login on their first attempt.
- **SC-006**: Rate limiting effectively blocks brute force attacks: after 5 failed login attempts within 15 minutes, further attempts return 429 for the remainder of the window.
- **SC-007**: Zero successful unauthorized token forgery incidents in production over 3 months (measured via audit logs).

### User Satisfaction

- ≥4.5/5 rating for ease of login and account setup in user surveys.

### Business Impact

- Account takeover incidents reduced by ≥95% compared to baseline (session-based auth without JWT controls).
- Support tickets related to login issues ≤2% of total user base per month.

## Assumptions

- The user profile data (name, role, etc.) is managed separately; this spec focuses only on authentication, not profile management.
- Email delivery for password reset exists or will be implemented separately; this spec defines the backend token generation and validation only.
- The system will use SQLModel (SQLAlchemy + Pydantic) as the ORM, FastAPI as the web framework, and python-jose for JWT handling.
- JWT secrets are managed securely via environment variables and are at least 256 bits (32 characters) random.
- The system runs over HTTPS in production; local development may use HTTP.
- For rate limiting, the implementation uses a combination of IP address and email as identifiers; Redis is available for distributed rate limiting but in-memory fallback is acceptable for single-instance deployments.
- The OAuth2 password flow is intended for first-party clients (own frontend/mobile apps); client credentials flow for machine-to-machine is out of scope.
- The refresh token rotation strategy uses the "refresh token rotation" pattern where each use generates a new refresh token and invalidates the old one, limiting the window of compromise.
- CORS will be configured to allow specific frontend origins only (no wildcard in production).
- The user entity already exists in the database or will be created as part of this feature; this spec does not define the complete user data model beyond authentication fields.
