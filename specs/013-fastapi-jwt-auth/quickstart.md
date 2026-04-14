# Quickstart: Implementing JWT Authentication

**Feature**: 013-fastapi-jwt-auth  
**Package**: `packages/backend`  
**Target**: FastAPI service with SQLModel/SQLAlchemy

---

## Prerequisites

- Python 3.13+ (constitution requires ≥3.12)
- `uv` package manager (installed globally)
- Neon PostgreSQL database (or local Postgres) with connection URL
- `.env` file configured with `JWT_SECRET_KEY`

---

## Step 1: Generate JWT Secret

```bash
# Generate a 256-bit (32 byte) secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Output example: "dGhpcyBpcyBhIHNlY3VyZSBzZWNyZXQga2V5IGZvciBqd3Q"
```

Add this to your `.env` file:

```bash
JWT_SECRET_KEY="<paste-generated-secret>"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## Step 2: Create Settings Module

**File**: `packages/backend/src/config/settings.py`

```python
"""Application settings loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, EmailStr


class Settings(BaseSettings):
    """Application configuration via environment variables."""

    # Database
    database_url: str = Field(..., description="AsyncPG database URL")
    direct_url: str | None = Field(None, description="Direct URL for migrations")

    # JWT
    jwt_secret_key: str = Field(..., min_length=32, description="JWT signing secret")
    jwt_algorithm: str = Field("HS256", description="JWT signature algorithm")
    access_token_expire_minutes: int = Field(15, description="Access token TTL")
    refresh_token_expire_days: int = Field(7, description="Refresh token TTL")

    # CORS (dev only)
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
        description="Allowed CORS origins"
    )

    model_config = {
        "env_file": ".env",
        "json_schema_extra": {
            "example": {
                "database_url": "postgresql+asyncpg://user:pass@localhost/dbname",
                "jwt_secret_key": "generate-with-secrets.token_urlsafe(32)",
                "jwt_algorithm": "HS256",
            }
        },
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
```

---

## Step 3: Add Auth Schemas

**File**: `packages/backend/src/schemas/auth.py`

```python
"""Authentication request/response schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: str = Field("user", max_length=50)


class UserLogin(BaseModel):
    username: EmailStr  # OAuth2 username field
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=12)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
```

---

## Step 4: Create Auth Service

**File**: `packages/backend/src/services/auth_service.py`

```python
"""Authentication business logic: password hashing, JWT, token validation."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import get_settings
from ..models.user import User, RefreshToken, PasswordResetToken
from .schemas import UserRead, Token

logger = structlog.get_logger()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


class AuthService:
    """Core authentication operations."""

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password, rounds=12)

    @staticmethod
    def _generate_token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    async def create_access_token(cls, user: User) -> tuple[str, int]:
        """Create JWT access token for user."""
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "iat": datetime.now(timezone.utc),
            "exp": expire,
            "iss": "event-ai",
        }
        encoded = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded, int(expires_delta.total_seconds())

    @classmethod
    async def create_refresh_token(cls, session: AsyncSession, user: User) -> tuple[str, datetime]:
        """Create a new refresh token, persisting its hash."""
        raw_token = secrets.token_urlsafe(64)
        token_hash = cls._generate_token_hash(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(refresh_token)
        await session.commit()
        await session.refresh(refresh_token)

        return raw_token, expires_at

    @classmethod
    def create_tokens(cls, session: AsyncSession, user: User) -> Token:
        """Create both access and refresh tokens for a user."""
        access_token, expires_in = cls.create_access_token(user)
        refresh_token, _ = cls.create_refresh_token(session, user)
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token,
        )

    @classmethod
    async def verify_refresh_token(cls, session: AsyncSession, raw_token: str) -> User:
        """Validate refresh token and return associated user."""
        token_hash = cls._generate_token_hash(raw_token)

        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        result = await session.execute(stmt)
        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            logger.warning("auth.refresh.invalid", hash_prefix=token_hash[:8])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user = await session.get(User, refresh_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        return user

    @classmethod
    async def rotate_refresh_token(cls, session: AsyncSession, raw_token: str) -> Token:
        """Rotate refresh token: invalidate old, issue new access+refresh tokens."""
        token_hash = cls._generate_token_hash(raw_token)

        # Find and revoke the old token
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        result = await session.execute(stmt)
        old_token = result.scalar_one_or_none()

        if not old_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        old_token.revoked_at = datetime.now(timezone.utc)
        user = await session.get(User, old_token.user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Create new tokens
        tokens = cls.create_tokens(session, user)
        await session.commit()

        logger.info("auth.refresh.rotated", user_id=str(user.id))
        return tokens

    @classmethod
    async def revoke_refresh_token(cls, session: AsyncSession, raw_token: str) -> None:
        """Revoke a refresh token (logout)."""
        token_hash = cls._generate_token_hash(raw_token)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        result = await session.execute(stmt)
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        logger.info("auth.logout", token_revoked=True)

    @classmethod
    async def decode_token(cls, token: str) -> dict:
        """Decode and validate JWT access token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                issuer="event-ai",
            )
            return payload
        except JWTError as e:
            logger.warning("auth.token.decode_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
```

---

## Step 5: Create Auth Routes

**File**: `packages/backend/src/routes/auth.routes.py`

```python
"""JWT Authentication endpoints."""
from datetime import datetime, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config.settings import get_settings
from ...config.database import get_session
from ...models.user import User, RefreshToken, PasswordResetToken
from ...services.auth_service import AuthService
from ...services.email_service import EmailService
from ..schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserRead,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetTokenResponse,
    SuccessResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
auth_service = AuthService()
email_service = EmailService()  # Built per constitution (event bus + SMTP)


# Rate limiting is applied globally via slowapi middleware
# See: packages/backend/src/middleware/rate_limit.middleware.py


@router.post("/register", response_model=Token)
async def register(
    request: Request,
    user_in: UserRegister,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user account and issue tokens."""
    client_ip = request.client.host if request.client else "unknown"

    # Check existing user
    existing = await session.execute(
        select(User).where(User.email == user_in.email)
    )
    if existing.scalar_one_or_none():
        logger = structlog.get_logger()
        logger.info("auth.register.duplicate", email=user_in.email, ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_in.email,
        password_hash=auth_service.hash_password(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        role=user_in.role or "user",
    )
    session.add(user)
    await session.flush()  # Get user.id without commit

    # Issue tokens
    tokens = auth_service.create_tokens(session, user)
    await session.commit()

    logger = structlog.get_logger()
    logger.info(
        "auth.register.success",
        user_id=str(user.id),
        email=user.email,
        ip=client_ip,
    )

    return tokens


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    user_in: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    """OAuth2 password grant: authenticate and issue tokens."""
    client_ip = request.client.host if request.client else "unknown"

    # Find user
    result = await session.execute(
        select(User).where(User.email == user_in.username)
    )
    user = result.scalar_one_or_none()

    # Constant-time check prevents timing attacks
    if not user or not auth_service.verify_password(user_in.password, user.password_hash):
        logger = structlog.get_logger()
        logger.warning(
            "auth.login.failed",
            email=user_in.username,
            ip=client_ip,
            reason="invalid_credentials",
        )
        # Use constant-time response to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account lock
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        logger = structlog.get_logger()
        logger.warning(
            "auth.login.locked",
            user_id=str(user.id),
            ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked due to multiple failed login attempts. Try again later.",
        )

    # Reset failed counter, update last_login
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    # Issue tokens
    tokens = auth_service.create_tokens(session, user)
    await session.commit()

    logger = structlog.get_logger()
    logger.info("auth.login.success", user_id=str(user.id), ip=client_ip)

    return tokens


@router.post("/refresh", response_model=Token)
async def refresh(
    body: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
):
    """Rotate refresh token: exchange for new access + refresh tokens."""
    tokens = await auth_service.rotate_refresh_token(session, body.refresh_token)
    return tokens


@router.post("/logout")
async def logout(
    body: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
):
    """Revoke refresh token (invalidate session)."""
    await auth_service.revoke_refresh_token(session, body.refresh_token)
    return {"success": True, "message": "Logged out successfully"}


@router.post("/password-reset-request", response_model=PasswordResetTokenResponse)
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
):
    """Generate one-time password reset token."""
    client_ip = request.client.host if request.client else "unknown"

    # Find user (don't leak existence — always 200 response)
    result = await session.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Don't leak that email doesn't exist; return dummy 200
        return PasswordResetTokenResponse(
            token="dummy_token_for_security",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            user_email=body.email,
        )

    # Generate reset token
    raw_token = token_urlsafe(32)
    token_hash = sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(reset_token)
    await session.commit()

    # Send email (or return token for testing)
    await email_service.send_password_reset(user.email, raw_token)

    logger = structlog.get_logger()
    logger.info("auth.password_reset.requested", user_id=str(user.id), ip=client_ip)

    return PasswordResetTokenResponse(
        token=raw_token,
        expires_at=expires_at,
        user_email=user.email,
    )


@router.post("/password-reset-confirm", response_model=SuccessResponse)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    session: AsyncSession = Depends(get_session),
):
    """Validate reset token and update password."""
    token_hash = sha256(body.token.encode()).hexdigest()

    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    user = await session.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )

    # Update password
    user.password_hash = auth_service.hash_password(body.new_password)

    # Invalidate all refresh tokens (log out all sessions)
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await session.execute(stmt)

    # Mark token used
    reset_token.used_at = datetime.now(timezone.utc)

    await session.commit()

    logger = structlog.get_logger()
    logger.info("auth.password_reset.completed", user_id=str(user.id))

    return SuccessResponse(message="Password reset successfully")


@router.get("/me", response_model=UserRead)
async def get_current_user(
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's profile."""
    return current_user


# Dependency injection helper used by routes above
from jose import jwt, JWTError
from fastapi import Depends, Request

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Authenticate user via JWT access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer="event-ai",
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await session.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_exception

    return user

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
```

---

## Step 6: Mount Routes in FastAPI App

**File**: `packages/backend/src/main.py` or `packages/backend/src/api/main.py`

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as AS
from sqlmodel import SQLModel

from .config.settings import get_settings
from .config.database import get_session, async_session_maker
from .routes import auth as auth_routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    app.state.async_session = async_session_maker(engine)

    # Create tables if they don't exist (dev only)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Event-AI Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (development)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Auth routes
app.include_router(auth_routes.router, prefix="/api/v1")
```

---

## Step 7: Run Alembic Migration

```bash
cd packages/backend
# Review the SQL migration
cat specs/013-fastapi-jwt-auth/contracts/migration_001_refresh_tokens.sql

# Apply via direct SQL (dev skipping Alembic for now)
psql $DATABASE_URL -f specs/013-fastapi-jwt-auth/contracts/migration_001_refresh_tokens.sql

# OR use Alembic if configured:
uv run alembic upgrade head
```

---

## Step 8: Test the Flow

```bash
# Activate virtualenv
cd packages/backend
source .venv/bin/activate  # or use `uv run`

# Start server
uv run uvicorn src.main:app --reload --port 8000

# In another terminal, test endpoints
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Str0ng!Pass#123","first_name":"Test","last_name":"User"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=Str0ng!Pass#123"

# Access protected endpoint
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'

# Logout
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

---

## Step 9: Write Tests (TDD)

**File**: `packages/backend/src/tests/test_auth.py`

```python
"""Full test suite for JWT authentication."""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlmodel.ext.asyncio.session import AsyncSession

from src.main import app
from src.config.database import async_session_maker
from src.services.auth_service import AuthService
from src.models.user import User

@pytest.mark.asyncio
async def test_user_registration(ac: AsyncClient, db: AsyncSession):
    """Test user creates account and receives tokens."""
    response = await ac.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "ValidPass123!",
            "first_name": "New",
            "last_name": "User"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900  # 15 minutes


@pytest.mark.asyncio
async def test_duplicate_registration(ac: AsyncClient):
    """Test email uniqueness constraint."""
    # Register first user
    await ac.post("/api/v1/auth/register", json={...})

    # Attempt duplicate
    response = await ac.post("/api/v1/auth/register", json={...})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT_EMAIL_EXISTS"


@pytest.mark.asyncio
async def test_password_too_short(ac: AsyncClient):
    """Test password complexity validation."""
    response = await ac.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "short"}
    )
    assert response.status_code == 400
    assert "password" in response.json()["error"].get("field", "")


@pytest.mark.asyncio
async def test_successful_login_issues_tokens(ac: AsyncClient, db: AsyncSession):
    """Test login with valid credentials returns tokens."""
    # Arrange: create user
    user = User(
        email="login@example.com",
        password_hash=AuthService.hash_password("SecurePass123!"),
        is_active=True,
    )
    db.add(user)
    await db.commit()

    # Act
    response = await ac.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "SecurePass123!"}
    )

    # Assert
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


@pytest.mark.asyncio
async def test_invalid_login_returns_401(ac: AsyncClient):
    """Test wrong credentials rejected."""
    response = await ac.post(
        "/api/v1/auth/login",
        data={"username": "wrong@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_token_refresh_rotation_invalidates_old_token(ac: AsyncClient, db: AsyncSession):
    """Test refresh rotates token (old token becomes invalid)."""
    # Register/login to get initial tokens
    reg = await ac.post("/api/v1/auth/register", json={...})
    tokens = reg.json()
    old_refresh = tokens["refresh_token"]

    # Use refresh to get new tokens
    refresh_resp = await ac.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh}
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()

    # Old refresh token should now be rejected
    retry = await ac.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh}
    )
    assert retry.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(ac: AsyncClient, db: AsyncSession):
    """Test logout revokes token."""
    # Get tokens
    reg = await ac.post("/api/v1/auth/register", json={...})
    # ... test logout flow
```

---

## Step 10: Configure Rate Limiting Middleware

**File**: `packages/backend/src/middleware/rate_limit.middleware.py` (likely already exists)

Ensure it wraps auth routes with appropriate limits:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# In auth routes, decorate endpoints:
@router.post("/register")
@limiter.limit("10/hour")
async def register(...): ...

@router.post("/login")
@limiter.limit("5/15minutes", key_func=get_remote_address)  # or composite key
async def login(...): ...

# Or globally configure in main.py app
```

---

## Step 11: Configure Structlog

**File**: `packages/backend/src/config/logging.py`

```python
import structlog

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

Call in `main.py` startup:

```python
from .config.logging import configure_logging
configure_logging()
```

---

## Environment Variables (.env)

```bash
# Database
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/event_ai"
DIRECT_URL="postgresql://user:pass@localhost/event_ai"

# JWT (generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))')
JWT_SECRET_KEY="your-secret-key-here"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (SMTP - required for password reset emails)
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="your-app@gmail.com"
SMTP_PASSWORD="app-password"
EMAIL_FROM="noreply@event-ai.com"

# CORS (dev)
CORS_ORIGINS="http://localhost:3000,http://localhost:3001,http://localhost:3002"
```

---

## Checklist

- [ ] `.env` configured with `JWT_SECRET_KEY` (32+ chars)
- [ ] Auth schemas in `packages/backend/src/schemas/auth.py`
- [ ] `AuthService` in `packages/backend/src/services/auth_service.py`
- [ ] Auth routes in `packages/backend/src/routes/auth.routes.py`
- [ ] `app.include_router(auth_routes.router)` in main app
- [ ] FastAPI dependency `get_current_user` defined and used
- [ ] Migration `migration_001_refresh_tokens.sql` applied to DB
- [ ] Rate limiting middleware active on auth endpoints
- [ ] Structlog configured; auth events logging
- [ ] All auth endpoints return standardized response envelope `{success, data/error}`
- [ ] Tests written following TDD (Red-Green-Refactor)
- [ ] All tests pass: `uv run pytest src/tests/`

---

## Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 on every endpoint | Missing `Authorization: Bearer {token}` header | Include token in request |
| Token decode fails | `JWT_SECRET_KEY` mismatch between issuer & validator | Ensure same secret across instances |
| Refresh token reuse succeeds | Forgetting to mark `revoked_at` before commit | Set `revoked_at` then commit in same transaction |
| Registration slow | Missing index on `email` column | Add `CREATE INDEX idx_users_email ON users(email)` or Field(index=True) |
| 403 locked account after failed login | `locked_until` not in UTC | Always use UTC timestamps |
| Password reset token always invalid | SHA-256 hex vs base64 mismatch | Store as hex digest, compare using hex |

---

## References

- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- OAuth2 Password Flow: RFC 6749 §4.3
- python-jose docs: https://python-jose.readthedocs.io/
- Constitution: `.specify/memory/constitution.md` (Security section, Layer II)
- Anti-pattern checklist: don't use `nest_asyncio`, `load_dotenv` path hacks, sync DB calls in async code
