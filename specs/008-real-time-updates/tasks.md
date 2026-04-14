# Tasks: Real-Time Updates (008)

**Branch**: `feature/real-time-updates` | **Date**: 2026-04-10 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1 — SSE Infrastructure

- [x] 1.1 `SSEConnectionManager` class (asyncio.Queue per user)
- [x] 1.2 `connect`, `disconnect`, `push` methods
- [x] 1.3 Stored on `app.state`, initialized in `lifespan`
- [x] 1.4 `get_connection_manager(request)` FastAPI dependency

## Phase 2 — SSE Endpoint

- [x] 2.1 `GET /api/v1/sse/stream?token=<jwt>`
- [x] 2.2 JWT auth via `AuthService.verify_access_token`
- [x] 2.3 `event: connected`, `event: notification`, `event: ping` (30s keepalive)
- [x] 2.4 `StreamingResponse` with correct headers
- [x] 2.5 Queue cleanup on disconnect

## Phase 3 — Client Integration

- [x] 3.1 `notification-provider.tsx` EventSource with reconnect
- [x] 3.2 Cache invalidation on notification event

## Phase 4 — Remaining

- [ ] 4.1 WebSocket endpoint for bidirectional chat (`/api/v1/ws`)
- [ ] 4.2 Redis Streams adapter for horizontal scaling
- [ ] 4.3 Offline event queuing (Redis list, 5 min TTL)
- [ ] 4.4 Per-user connection limit (max 5 tabs)
- [ ] 4.5 Health check `GET /api/v1/sse/health`
- [ ] 4.6 Subscription authorization per resource
