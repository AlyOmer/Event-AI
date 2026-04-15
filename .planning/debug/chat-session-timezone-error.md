---
status: resolved
trigger: "POST /api/v1/ai/chat/stream returns 500 — asyncpg DataError: can't subtract offset-naive and offset-aware datetimes"
created: 2026-04-15
updated: 2026-04-15
---

## Symptoms
- expected: chat stream endpoint creates session and streams response
- actual: 500 Internal Server Error on every POST /api/v1/ai/chat/stream
- error: asyncpg.exceptions.DataError — invalid input for query argument $3
- root_error: can't subtract offset-naive and offset-aware datetimes
- sql: INSERT INTO ai.chat_sessions (..., started_at, last_activity_at, ...) VALUES ($3::TIMESTAMP WITHOUT TIME ZONE, ...)
- parameter: datetime.datetime(2026, 4, 15, 18, 49, 55, tzinfo=datetime.timezone.utc)

## Current Focus
- hypothesis: ChatSession and Message models declare datetime columns without timezone=True, so SQLAlchemy maps them to TIMESTAMP WITHOUT TIME ZONE. The default_factory uses datetime.now(timezone.utc) which produces timezone-aware datetimes. asyncpg rejects the mismatch.
- next_action: Fix both models to use DateTime(timezone=True) columns so PostgreSQL stores TIMESTAMPTZ
- reasoning_checkpoint: Root cause confirmed by reading models/chat_session.py and models/message.py

## Evidence
- timestamp: 2026-04-15T18:49:55Z
  file: models/chat_session.py
  finding: started_at and last_activity_at use Field(default_factory=lambda: datetime.now(timezone.utc)) but no sa_column with timezone=True
- timestamp: 2026-04-15T18:49:55Z
  file: models/message.py
  finding: created_at has same pattern — timezone-aware default, no timezone=True column

## Eliminated
- hypothesis: Bug in asyncpg version
  reason: Error is a data type mismatch, not a library bug

## Resolution
- root_cause: TIMESTAMP WITHOUT TIME ZONE columns receiving timezone-aware datetime objects
- fix: Add sa_column=Column(DateTime(timezone=True)) to started_at, last_activity_at in ChatSession and created_at in Message
- files_changed: models/chat_session.py, models/message.py
