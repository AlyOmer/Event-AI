"""
Idempotent seed script for Event-AI backend.

Usage (from packages/backend/):
    uv run python -m src.scripts.seed

Creates:
  - Admin user (from SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD env vars)
  - Default event categories
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config.database import get_settings
from src.models.user import User
from src.models.category import Category
from src.services.auth_service import AuthService

# Import all models so SQLAlchemy can resolve relationships
import src.models.vendor  # noqa: F401
import src.models.service  # noqa: F401
import src.models.booking  # noqa: F401
import src.models.availability  # noqa: F401
import src.models.inquiry  # noqa: F401
import src.models.approval  # noqa: F401

log = structlog.get_logger()

DEFAULT_CATEGORIES = [
    {"name": "Wedding",    "display_order": 1},
    {"name": "Mehndi",     "display_order": 2},
    {"name": "Baraat",     "display_order": 3},
    {"name": "Walima",     "display_order": 4},
    {"name": "Corporate",  "display_order": 5},
    {"name": "Conference", "display_order": 6},
    {"name": "Birthday",   "display_order": 7},
    {"name": "Party",      "display_order": 8},
]


def _validate_settings(settings) -> None:
    """Validate required seed env vars before touching the DB."""
    if not settings.seed_admin_email:
        log.error("seed.error", message="SEED_ADMIN_EMAIL env var is not set")
        sys.exit(1)
    if not settings.seed_admin_password:
        log.error("seed.error", message="SEED_ADMIN_PASSWORD env var is not set")
        sys.exit(1)
    if len(settings.seed_admin_password) < 12:
        log.error(
            "seed.error",
            message="SEED_ADMIN_PASSWORD must be at least 12 characters",
        )
        sys.exit(1)


async def seed_admin(session: AsyncSession, email: str, password: str) -> bool:
    """Create admin user if not exists. Returns True if created, False if skipped."""
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing:
        log.info("seed.admin.skipped", email=email, reason="already exists")
        return False

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=AuthService.hash_password(password),
        first_name="Admin",
        last_name="User",
        role="admin",
        is_active=True,
        email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.flush()
    log.info("seed.admin.created", email=email, user_id=str(user.id))
    return True


async def seed_categories(session: AsyncSession) -> dict:
    """Create default categories if not exists. Returns counts."""
    created = 0
    skipped = 0

    for cat_data in DEFAULT_CATEGORIES:
        result = await session.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            log.info("seed.category.skipped", name=cat_data["name"], reason="already exists")
            skipped += 1
            continue

        category = Category(
            id=uuid.uuid4(),
            name=cat_data["name"],
            display_order=cat_data["display_order"],
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(category)
        await session.flush()
        log.info("seed.category.created", name=cat_data["name"])
        created += 1

    return {"created": created, "skipped": skipped}


async def run_seed() -> None:
    settings = get_settings()
    _validate_settings(settings)

    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"ssl": "require"},
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            admin_created = await seed_admin(
                session,
                settings.seed_admin_email,
                settings.seed_admin_password,
            )
            cat_counts = await seed_categories(session)

    await engine.dispose()

    log.info(
        "seed.complete",
        admin_created=admin_created,
        categories_created=cat_counts["created"],
        categories_skipped=cat_counts["skipped"],
    )


if __name__ == "__main__":
    asyncio.run(run_seed())
