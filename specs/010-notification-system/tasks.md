# Tasks: Notification System (010)

**Branch**: `feature/notification-system` | **Date**: 2026-04-10 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1 — Database & Model

- [x] 1.1 Create `Notification` SQLModel with all fields
- [x] 1.2 Create `NotificationType` enum
- [x] 1.3 Alembic migration `20260410_notifications` (table + 3 indexes)

## Phase 2 — Service & Event Bus

- [x] 2.1 `NotificationService.handle()` event bus listener
- [x] 2.2 Atomic write in same DB session as booking transaction
- [x] 2.3 Register listeners in `lifespan` (not at import time)
- [x] 2.4 `list_notifications`, `unread_count`, `mark_read`, `mark_all_read` helpers

## Phase 3 — SSE Real-Time

- [x] 3.1 `SSEConnectionManager` on `app.state`
- [x] 3.2 `GET /api/v1/sse/stream?token=` endpoint
- [x] 3.3 `get_connection_manager` FastAPI dependency

## Phase 4 — REST API

- [x] 4.1 `GET /api/v1/notifications/`
- [x] 4.2 `GET /api/v1/notifications/unread-count`
- [x] 4.3 `PATCH /api/v1/notifications/read-all`
- [x] 4.4 `PATCH /api/v1/notifications/{id}/read`

## Phase 5 — Frontend

- [x] 5.1 `notification-provider.tsx` — React Query + SSE EventSource
- [x] 5.2 `notification-bell.tsx` — dropdown UI
- [x] 5.3 Fix SSE URL, data shape, optimistic updates

## Phase 6 — Tests

- [x] 6.1 Unit tests for `NotificationService`
- [x] 6.2 Integration tests for notification routes
- [x] 6.3 All 13 tests passing

## Phase 7 — Remaining

- [ ] 7.1 Email notifications (SMTP, fire-and-forget)
- [ ] 7.2 Notification deduplication by `eventId + userId` (5-min window)
- [ ] 7.3 Vendor-side notifications on new booking
- [ ] 7.4 SMS via Pakistani gateway — P3
- [ ] 7.5 Day-before reminder cron — P3
- [ ] 7.6 Notification preferences per user — P3
