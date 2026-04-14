"""
In-memory rate limiting middleware using sliding window.
Not suitable for multi-process deployments; use Redis for production.
"""
import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for given key."""
        now = time.time()
        timestamps = self.requests[key]
        # Remove old timestamps outside window
        cutoff = now - self.window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
        # Check count
        if len(timestamps) >= self.max_attempts:
            return False
        timestamps.append(now)
        # Cleanup empty keys occasionally
        if not timestamps:
            del self.requests[key]
        return True


def rate_limit_dependency(max_attempts: int, window_seconds: int, key_func=None):
    """
    FastAPI dependency for rate limiting.
    Usage: @app.post("/", dependencies=[Depends(rate_limit_dependency(5, 60))])
    """
    limiter = RateLimiter(max_attempts, window_seconds)

    async def dependency(request: Request):
        key = key_func(request) if key_func else request.client.host or "unknown"
        if not limiter.is_allowed(key):
            logger.warning("Rate limit exceeded", key=key, path=request.url.path)
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests",
                headers={"Retry-After": str(window_seconds)},
            )
    return dependency


# For use as middleware on entire router
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that applies rate limiting to all requests."""

    def __init__(self, app, max_attempts: int, window_seconds: int, key_func=None):
        super().__init__(app)
        self.limiter = RateLimiter(max_attempts, window_seconds)
        self.key_func = key_func or (lambda r: r.client.host or "unknown")

    async def dispatch(self, request: Request, call_next):
        key = self.key_func(request)
        if not self.limiter.is_allowed(key):
            logger.warning("Rate limit exceeded (middleware)", key=key, path=request.url.path)
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"error": "Too Many Requests", "message": "Rate limit exceeded"},
                headers={"Retry-After": str(self.window_seconds)},
            )
        response = await call_next(request)
        return response
