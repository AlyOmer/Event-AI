# Implementation Plan: Notification System

**Branch**: `feature/notification-system` | **Date**: 2026-04-10 | **Spec**: [spec.md](spec.md)

## Summary

Persistent in-app notifications driven by booking domain events, with real-time SSE push to the user portal. Email and SMS are Phase 2.

## Technical Context

**Language**: Python 3.13
**Framework**: FastAPI + SQLModel + asyncpg
**Database**: Neon PostgreSQL (Alembic migrations)
**Testing**: pytest-asyncio + httpx
**Frontend**: Next.js 15 + React Query + native EventSource

## Constitution Check

- [x] Event-Driven: NotificationService subscribes to EventBus — never inline in routes
- [x] Real-time: SSE push via `GET /api/v1/sse/stream?token=` — no polling
- [x] Atomicity: Notification row written in same DB session as booking (Outbox Pattern lite)
- [x] app.state: SSEConnectionManager stored on app.state, initialized in lifespan
- [x] JWT auth on all notification endpoints
- [x] Pydantic models for all inputs/outputs

## Phase 1: Database & Model ✅ Done

- [x] `Notification` SQLModel with `user_id`, `type`, `title`, `body`, `data` (JSON), `is_read`, `read_at`, `created_at`
- [x] Alembic migration `20260410_notifications` — table + 3 indexes
- [x] `NotificationType` enum: booking_created, booking_confirmed, booking_cancelled, booking_completed, booking_rejected, booking_status_changed, system

## Phase 2: Service & Event Bus ✅ Done

- [x] `NotificationService.handle(event_type, payload, user_id, session)` — event bus listener
- [x] Writes `Notification` row atomically in same session as booking transaction
- [x] Registered for all 6 booking events in `lifespan`
- [x] `list_notifications`, `unread_count`, `mark_read`, `mark_all_read` REST helpers

## Phase 3: SSE Real-Time ✅ Done

- [x] `SSEConnectionManager` — asyncio.Queue per user connection, stored on `app.state`
- [x] `GET /api/v1/sse/stream?token=<jwt>` — persistent SSE stream
- [x] Events: `connected`, `notification`, `ping` (30s keepalive)
- [x] `get_connection_manager(request)` FastAPI dependency

## Phase 4: REST API ✅ Done

- [x] `GET /api/v1/notifications/` — paginated list
- [x] `GET /api/v1/notifications/unread-count`
- [x] `PATCH /api/v1/notifications/read-all`
- [x] `PATCH /api/v1/notifications/{id}/read`

## Phase 5: Frontend ✅ Done

- [x] `notification-provider.tsx` — React Query fetch + SSE EventSource reconnection
- [x] `notification-bell.tsx` — dropdown UI with unread badge
- [x] Fixed SSE URL, data shape (`is_read`, `body`, `created_at`), optimistic updates

## Phase 6: Tests ✅ Done

- [x] 13 pytest tests — unit + integration
- [x] SQLite in-memory test DB
- [x] All passing: `pytest tests/test_notifications.py`

## Remaining (Phase 2 — not yet started)

- [ ] Email notifications via SMTP (fire-and-forget on booking events)
- [ ] Notification deduplication by `eventId + userId` within 5-minute window
- [ ] Vendor-side notifications (vendor receives alert on new booking)
- [ ] SMS via Pakistani gateway (Jazz/Zong) — P3
- [ ] Day-before event reminder cron — P3
- [ ] Notification preferences per user — P3
