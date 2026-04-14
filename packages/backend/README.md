*# Event-AI Backend

FastAPI REST API for the Event-AI platform. Python 3.13 · uv · SQLModel · Neon PostgreSQL.

## Setup

```bash
uv sync
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET_KEY, etc.
uv run alembic upgrade head
uv run uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
```

## Tests

```bash
uv run pytest -v
uv run pytest tests/test_event_routes.py -v
uv run pytest --cov=src --cov-report=term
```

## Seed

```bash
SEED_ADMIN_EMAIL=admin@eventai.pk SEED_ADMIN_PASSWORD=AdminPass123! \
  uv run python -m src.scripts.seed
```

## Key directories

```
src/
├── api/v1/          # Route handlers (thin — call services only)
├── services/        # Business logic (EventService, BookingService, etc.)
├── models/          # SQLModel ORM entities
├── schemas/         # Pydantic request/response schemas
├── config/          # Settings (BaseSettings + @lru_cache), lifespan
├── middleware/       # Rate limiting, login rate limit
└── scripts/         # seed.py
alembic/versions/    # Database migrations
tests/               # pytest-asyncio + httpx + SQLite in-memory
```

See the [root README](../../README.md) for full API reference and architecture docs.
