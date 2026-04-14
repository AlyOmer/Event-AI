# Implementation Plan: Real-Time Updates

**Branch**: `feature/real-time-updates` | **Date**: 2026-04-10 | **Spec**: [spec.md](spec.md)

## Summary

Server-Sent Events (SSE) for unidirectional server→client push of booking and notification events. WebSocket for bidirectional chat is Phase 2.

## Technical Context

**Language**: Python 3.13
**Framework**: FastAPI + asyncio
**Transport**: SSE (`text/event-stream`) — native browser `EventSource` API
**Auth**: JWT via `?token=` query param (EventSource does not support custom headers)
**Scaling**: Single-instance asyncio.Queue (Phase 1); Redis Streams upgrade path (Phase 2)
**Testing**: pytest-asyncio + httpx

## Constitution Check

- [x] No frontend polling — backend pushes via SSE (§III.7)
- [x] No socket.io — native EventSource API
- [x] JWT auth on connection establishment (§VIII.5)
- [x] SSEConnectionManager on app.state — no global mutable state (Anti-Patterns)
- [x] Initialized in lifespan, not at import time

## Phase 1: SSE Infrastructure ✅ Done

- [x] `SSEConnectionManager` — `Dict[UUID, List[asyncio.Queue]]` (multiple tabs per user)
- [x] `connect(user_id)` → returns `asyncio.Queue(maxsize=50)`
- [x] `disconnect(user_id, queue)` — cleans up on client disconnect
- [x] `push(user_id, event_type, data)` — fire-and-forget, no-op if no connections
- [x] Stored on `app.state.connection_manager`, initialized in `lifespan`
- [x] `get_connection_manager(request)` FastAPI `Depends()` getter

## Phase 2: SSE Endpoint ✅ Done

- [x] `GET /api/v1/sse/stream?token=<jwt>`
- [x] JWT validated via `AuthService.verify_access_token(token, session)`
- [x] Streams: `event: connected`, `event: notification`, `event: ping` (30s)
- [x] `StreamingResponse` with `Cache-Control: no-cache`, `X-Accel-Buffering: no`
- [x] Queue cleaned up in `finally` block on disconnect

## Phase 3: Client Integration ✅ Done

- [x] `notification-provider.tsx` — `EventSource` with 5s reconnect on error
- [x] On `notification` event → `queryClient.invalidateQueries(["notifications"])`
- [x] Token passed as `?token=` query param from `localStorage`

## Remaining (Phase 2 — not yet started)

- [ ] WebSocket endpoint for bidirectional vendor-client booking chat (`/api/v1/ws`)
- [ ] Redis Streams adapter for horizontal scaling (multiple FastAPI instances)
- [ ] Offline event queuing — store missed events in Redis list (5 min TTL), deliver on reconnect
- [ ] Per-user connection limit enforcement (max 5 concurrent tabs)
- [ ] Health check endpoint `GET /api/v1/sse/health` — active connection count
- [ ] Subscription authorization — verify user owns resource before pushing channel events
