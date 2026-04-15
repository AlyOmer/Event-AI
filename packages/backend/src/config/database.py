import asyncio
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import structlog

from pydantic import field_validator, EmailStr, Field

log = structlog.get_logger()

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost/postgres"
    direct_url: str | None = None

    # JWT Authentication Settings
    jwt_secret_key: str = Field(..., min_length=32, description="JWT signing secret")
    jwt_algorithm: str = Field("HS256", description="JWT signature algorithm")
    access_token_expire_minutes: int = Field(15, description="Access token TTL in minutes")
    refresh_token_expire_days: int = Field(7, description="Refresh token TTL in days")

    # CORS origins (comma-separated in env)
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003"],
        description="Allowed CORS origins"
    )

    # Google OAuth 2.0
    google_client_id: Optional[str] = Field(default=None, description="Google OAuth2 client ID from Google Cloud Console")
    google_client_secret: Optional[str] = Field(default=None, description="Google OAuth2 client secret")
    google_redirect_uri: str = Field(
        default="http://localhost:5000/api/v1/auth/google/callback",
        description="Must exactly match the Authorized Redirect URI registered in Google Cloud Console",
    )

    # Frontend base URL — used for post-OAuth browser redirects
    frontend_url: str = Field(
        default="http://localhost:3003",
        description="User portal base URL; tokens are passed as query params after OAuth",
    )

    # Seed script settings
    seed_admin_email: Optional[str] = Field(default=None)
    seed_admin_password: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "?" in v:
                v = v.split("?")[0]
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v: list[str] | str | None) -> list[str]:
        """Parse comma-separated CORS_ORIGINS from environment."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or []

@lru_cache
def get_settings() -> Settings:
    return Settings()

# Global database resources config
engine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False
)

async_session_maker = sessionmaker(
    bind=engine, # type: ignore
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncSession: # type: ignore
    async with async_session_maker() as session:
        yield session

async def _cleanup_expired_locks() -> None:
    """Background task: release expired availability locks every 60 seconds."""
    from sqlalchemy import update as sa_update
    from datetime import datetime, timezone

    while True:
        await asyncio.sleep(60)
        try:
            async with async_session_maker() as session:
                now = datetime.now(timezone.utc)
                from src.models.availability import VendorAvailability, AvailabilityStatus
                stmt = (
                    sa_update(VendorAvailability)
                    .where(
                        VendorAvailability.status == AvailabilityStatus.LOCKED,
                        VendorAvailability.locked_until < now,
                    )
                    .values(
                        status=AvailabilityStatus.AVAILABLE,
                        locked_by=None,
                        locked_until=None,
                        locked_reason=None,
                        updated_at=now,
                    )
                )
                result = await session.execute(stmt)
                await session.commit()
                if result.rowcount > 0:
                    log.info("availability.locks_released", count=result.rowcount)
        except Exception as e:
            log.error("availability.lock_cleanup_failed", error=str(e))


@asynccontextmanager
async def lifespan(app):
    app.state.async_session = async_session_maker

    # Init SSE manager on app.state (constitution: no global mutable state outside app.state)
    from src.services.sse_manager import SSEConnectionManager
    app.state.connection_manager = SSEConnectionManager()

    # Register notification listeners in lifespan (constitution: init in lifespan, not at import)
    from src.services.event_bus_service import event_bus
    from src.services.notification_service import notification_service
    for _et in (
        "booking.created", "booking.confirmed", "booking.cancelled",
        "booking.completed", "booking.rejected", "booking.status_changed",
        # Event domain events
        "event.created", "event.status_changed", "event.cancelled",
        # Vendor domain events
        "vendor.approved", "vendor.rejected",
    ):
        event_bus.subscribe(_et, notification_service.handle)

    cleanup_task = asyncio.create_task(_cleanup_expired_locks())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
