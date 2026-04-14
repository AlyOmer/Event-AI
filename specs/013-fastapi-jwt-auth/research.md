# Research Report: FastAPI JWT Authentication with OAuth2

**Feature**: 013-fastapi-jwt-auth  
**Date**: 2026-04-09  
**Scope**: JWT authentication for FastAPI backend using OAuth2 password grant flow

---

## 1. JWT Authentication Best Practices for FastAPI

### Decision
Use `python-jose[cryptography]` for JWT operations with HS256 algorithm, integrated with FastAPI's `OAuth2PasswordBearer` and `OAuth2PasswordRequestForm`.

### Rationale
- `python-jose` is the recommended library in the FastAPI/OAuth2 ecosystem (used in official docs)
- HS256 (HMAC with SHA-256) provides synchronous signing which is simpler than RSA for single-service auth
- FastAPI provides native `OAuth2PasswordBearer` token dependency and `OAuth2PasswordRequestForm` for password grant flow
- The constitution mandates `python-jose[cryptography]` explicitly

### Implementation Pattern

```python
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = settings.jwt_secret_key  # 256-bit random
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "iss": "event-ai"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload
```

### Token Decoding Middleware (Dependency)

```python
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user
```

### Alternatives Considered
- **`pyjwt`** — rejected; `python-jose` has better OAuth2 integration and is the FastAPI documentation standard
- **RSA asymmetric keys (RS256)** — rejected; adds complexity (key pair generation/management) without need for single-service auth; HS256 is sufficient
- **`authlib`** — rejected; overkill for simple JWT auth; introduces additional abstraction layer

---

## 2. Refresh Token Rotation Pattern

### Decision
Implement refresh token rotation with server-side token hashing and tracking.

### Rationale
- **Rotation mitigates token theft**: when a refresh token is used, it's immediately invalidated and a new one issued. If an attacker steals a token and uses it first, the legitimate user's subsequent refresh attempt fails, alerting to compromise.
- **Server-side invalidation**: Refresh tokens are stored hashed (SHA-256) in the database; actual token sent to client is one-time use
- **Pattern from OAuth 2.0 security best practices** (RFC 6819, OWASP)

### Token Storage Strategy

| Token Type | Client Storage | Server Storage |
|------------|---------------|----------------|
| Access token | In-memory only (never persistent) | Not stored; validated statelessly via signature |
| Refresh token | HTTP-only secure cookie OR secure localStorage with CSRF protection | `refresh_tokens` table with `token_hash` (SHA-256), `user_id`, `expires_at`, `revoked_at` |

### Rotation Flow

```python
# 1. Client sends refresh_token to /token/refresh endpoint
# 2. Server:
#    a. Hash the incoming token → lookup RefreshToken record
#    b. Verify: exists, not revoked, not expired
#    c. Generate NEW refresh token
#    d. Mark OLD token revoked_at = now
#    e. Create NEW token record
#    f. Issue new access token + new refresh token

@app.post("/api/v1/auth/refresh")
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_session)
):
    token_hash = sha256(refresh_token.encode()).hexdigest()
    
    # Find non-revoked, non-expired token
    result = await session.exec(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
    )
    stored_token = result.first()
    if not stored_token:
        raise HTTPException(401, "Invalid refresh token")
    
    # Revoke old token
    stored_token.revoked_at = datetime.now(timezone.utc)
    
    # Create new refresh token
    new_raw_token = secrets.token_urlsafe(64)
    new_hash = sha256(new_raw_token.encode()).hexdigest()
    new_expires = datetime.now(timezone.utc) + timedelta(days=7)
    
    new_token = RefreshToken(
        user_id=stored_token.user_id,
        token_hash=new_hash,
        expires_at=new_expires
    )
    session.add(new_token)
    await session.commit()
    
    # Issue new access token
    access_token = create_access_token(
        data={"sub": str(stored_token.user_id), "role": user.role}
    )
    
    return {"access_token": access_token, "refresh_token": new_raw_token}
```

### Edge Cases
- **Token used twice**: First use succeeds, second use finds revoked token → 401
- **Clock skew**: Use UTC; add 30-second leeway for token validation
- **Database down**: Return 503; don't fall back to accepting tokens without DB check

### Alternatives Considered
- **Stateless refresh tokens (no DB)** — rejected; cannot invalidate individual tokens; rotation impossible
- **Fixed refresh tokens (no rotation)** — rejected; compromised token valid until expiry; increases attack window

---

## 3. Rate Limiting for FastAPI Auth Endpoints

### Decision
**Primary**: In-memory rate limiting using `slowapi` library with `memcached` backend support for future scaling.

### Rationale
- Constitution mandates Redis is available for distributed rate limiting; in-memory is acceptable for single-instance deployments
- `slowapi` is the standard rate limiting library for FastAPI; uses leaky bucket algorithm with window-based limits
- Simple setup; minimal dependencies; supports both per-IP and per-user keying
- Can swap to Redis storage later without API changes

### Implementation with slowapi

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/auth/register")
@limiter.limit("10/hour")
async def register(request: Request, ...): ...

@app.post("/api/v1/auth/login")
@limiter.limit("5/15minutes", key_func=lambda: f"{get_remote_address(request)}:{form.email}")
async def login(request: Request, ...): ...
```

**Key function strategy**:
- Registration: limit by IP only (`10/hour`)
- Login: composite key `IP:email` (`5/15minutes`)
- Token refresh: not rate-limited (limited by token validity)
- Password reset: `5/hour` per email

### Alternatives Considered
- **`fastapi-limiter`** — rejected; unmaintained; slower
- **Custom in-memory dict with asyncio.Lock** — rejected; re-inventing the wheel; `slowapi` is battle-tested
- **Redis-backed from start** — postponed; adds Redis dependency complexity; in-memory sufficient for MVP

---

## 4. Password Hashing with Bcrypt

### Decision
Use `passlib[bcrypt]` with 12 salt rounds for password hashing.

### Rationale
- Constitution explicitly mandates bcrypt with ≥12 salt rounds
- `passlib` provides convenient `Context` API with built-in salt generation
- Bcrypt is computationally expensive, resistant to rainbow table attacks

### Implementation

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed: str) -> bool:
    return pwd_context.verify(plain_password, hashed)

def hash_password(password: str) -> str:
    return pwd_context.hash(password, rounds=12)
```

### Alternatives Considered
- **Argon2** — rejected; constitution mandates bcrypt; can upgrade via migration later
- **PBKDF2** — rejected; slower and less memory-hard than bcrypt for same cost factor

---

## 5. Structured Event Logging with Structlog

### Decision
Use `structlog` configured for JSON structured logging to stdout.

### Rationale
- Constitution mandates `structlog` for structured JSON logging
- All auth events log with consistent fields: `event`, `user_id`, `email`, `ip_address`, `user_agent`, `timestamp`, `outcome`

### Implementation

```python
import structlog

logger = structlog.get_logger()

# Log examples:
logger.info("auth.register.attempt", email=email, ip=client_ip)
logger.info("auth.register.success", user_id=str(user.id))
logger.warning("auth.login.failed", email=email, ip=client_ip, reason="invalid_password")
logger.info("auth.login.success", user_id=str(user.id))
logger.info("auth.logout", user_id=str(user.id), token_revoked=True)
```

### Alternatives Considered
- **Python standard logging** — rejected; no structured JSON out of box; manual formatting required
- **loguru** — rejected; not standard in FastAPI ecosystem; less integration with middleware

---

## 6. CORS Configuration

### Decision
Use whitelist-based CORS; no wildcard in production.

### Rationale
- Constitution explicitly forbids wildcard `*` in production
- Frontend portals live in separate Next.js apps with known origins

### Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # user portal dev
        "http://localhost:3001",  # admin portal dev
        "http://localhost:3002",  # vendor portal dev
        "https://event-ai.com",  # production (example)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Alternatives Considered
- **Wildcard CORS** — rejected; security vulnerability; allows any origin to make authenticated requests

---

## 7. Password Reset Token Implementation

### Decision
Store password reset tokens in a dedicated table with SHA-256 hash, expiry (1 hour), single-use.

### Rationale
- Stateless JWT-style tokens rejected because need invalidation after use
- Token hashing prevents token leakage from DB compromise
- Single-use ensures replay attacks fail

### Schema

```python
class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    token_hash: str = Field(max_length=255)  # SHA-256 hash
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Flow
1. `POST /api/v1/auth/password-reset-request` → generate token, store hash, return token (for testing) / send email (production)
2. `POST /api/v1/auth/password-reset-confirm` → verify token hash, not used, not expired → update password → mark token used

### Alternatives Considered
- **Magic link via email with JWT** — rejected; link sharing risk; single token cannot be revoked without DB check anyway
- **No DB storage** — rejected; cannot enforce single-use or expiry

---

## 8. Settings Configuration

### Decision
Pydantic `BaseSettings` with `@lru_cache` and `.env` file support.

### Implementation

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str
    direct_url: str | None = None
    
    # JWT
    jwt_secret_key: str  # Must be 32+ chars, generated with secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # OAuth2
    oauth2_scheme_token_url: str = "/api/v1/auth/login"
    
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### `.env.example`

```bash
DATABASE_URL="postgresql+asyncpg://..."
DIRECT_URL="postgresql://..."

JWT_SECRET_KEY="generate-with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Alternatives Considered
- **Raw `os.environ.get()`** — rejected; violates constitution; no type safety
- **`python-dotenv` with path hacks** — rejected; constitution mandates `pydantic-settings`

---

## Summary of Architecture Decisions

| Decision | Choice | Reason |
|----------|-------|--------|
| JWT library | `python-jose[cryptography]` | FastAPI standard |
| JWT algorithm | HS256 | Simpler; single service |
| Token storage (refresh) | DB with hash + rotation | Revocable, secure |
| Password hashing | bcrypt (passlib), 12 rounds | Constitution mandate |
| Rate limiting | `slowapi` in-memory | Standard, minimal deps |
| Structured logging | `structlog` | Constitution mandate |
| Settings | Pydantic `BaseSettings` | Constitution mandate |
| CORS | Whitelist | Security requirement |
| Password reset | DB token + hash | Single-use, revocable |

All decisions align with the constitution's technology mandate and security requirements.
