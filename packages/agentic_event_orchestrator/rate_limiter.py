"""
rate_limiter.py — Per-session and per-IP rate limiting for the agent service.

Priority 1: Prevents API abuse and flooding the LLM with requests.
Uses in-memory sliding window — replace with Redis for multi-instance deploys.
"""

import time
import logging
from collections import defaultdict, deque
from typing import Optional
from fastapi import Request, HTTPException

logger = logging.getLogger("rate_limiter")

# ─── Config ──────────────────────────────────────────────────────
CHAT_RATE_LIMIT   = 15   # max requests
CHAT_RATE_WINDOW  = 60   # per N seconds (per session)

IP_RATE_LIMIT     = 30   # max requests
IP_RATE_WINDOW    = 60   # per N seconds (per IP)

GLOBAL_RATE_LIMIT = 200  # max total requests
GLOBAL_RATE_WINDOW = 60  # across all sessions per minute

# ─── Stores (timestamps of recent requests) ───────────────────────
_session_windows: dict[str, deque] = defaultdict(deque)
_ip_windows: dict[str, deque]      = defaultdict(deque)
_global_window: deque              = deque()


def _clean_window(window: deque, now: float, duration: int) -> deque:
    """Remove timestamps older than the window duration."""
    while window and window[0] < now - duration:
        window.popleft()
    return window


def check_rate_limit(session_id: Optional[str], client_ip: str) -> tuple[bool, Optional[str]]:
    """
    Check all rate limits for a request.
    
    Returns:
        (allowed, error_message_or_None)
    """
    now = time.monotonic()

    # 1. Global limit
    _clean_window(_global_window, now, GLOBAL_RATE_WINDOW)
    if len(_global_window) >= GLOBAL_RATE_LIMIT:
        logger.warning("Global rate limit hit from IP=%s", client_ip)
        return False, "The service is temporarily busy. Please try again in a moment."

    # 2. Per-IP limit
    ip_window = _ip_windows[client_ip]
    _clean_window(ip_window, now, IP_RATE_WINDOW)
    if len(ip_window) >= IP_RATE_LIMIT:
        logger.warning("IP rate limit hit: %s", client_ip)
        return False, (
            f"Too many requests from your connection. "
            f"Please wait {IP_RATE_WINDOW} seconds before trying again."
        )

    # 3. Per-session limit
    if session_id:
        sess_window = _session_windows[session_id]
        _clean_window(sess_window, now, CHAT_RATE_WINDOW)
        if len(sess_window) >= CHAT_RATE_LIMIT:
            logger.info("Session rate limit hit: %s", session_id[:8])
            return False, (
                f"You're sending messages too quickly. "
                f"Please wait a moment — limit is {CHAT_RATE_LIMIT} messages per {CHAT_RATE_WINDOW}s."
            )

    return True, None


def record_request(session_id: Optional[str], client_ip: str):
    """Record a new request in all windows. Call after check_rate_limit passes."""
    now = time.monotonic()
    _global_window.append(now)
    _ip_windows[client_ip].append(now)
    if session_id:
        _session_windows[session_id].append(now)


def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For (behind proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, session_id: Optional[str] = None):
    """
    FastAPI dependency — raises 429 if rate limits are exceeded.
    
    Usage:
        @app.post("/api/chat", dependencies=[Depends(rate_limit_middleware)])
    """
    client_ip = get_client_ip(request)
    allowed, msg = check_rate_limit(session_id, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=msg or "Rate limit exceeded",
            headers={"Retry-After": "60"},
        )
    record_request(session_id, client_ip)
