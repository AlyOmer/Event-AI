"""
Login-specific rate limiting middleware to prevent brute force attacks.
Tracks failures by both IP address and email/username combination.
"""
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from fastapi import Request, HTTPException
import structlog

logger = structlog.get_logger()


class LoginRateLimiter:
    """Rate limiter for login attempts with separate tracking for IP and credentials."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # Track by IP address
        self.ip_attempts: Dict[str, List[float]] = defaultdict(list)
        # Track by email/username
        self.credential_attempts: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, identifier: str) -> bool:
        """Check if attempts are allowed for given identifier."""
        now = time.time()
        timestamps = self._get_timestamps(identifier)
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
            self._remove_empty_key(identifier)
        return True

    def record_failure(self, identifier: str):
        """Record a failed attempt for the identifier."""
        now = time.time()
        timestamps = self._get_timestamps(identifier)
        timestamps.append(now)
        # Optional: cleanup old entries periodically
        self._cleanup_old_entries(now)

    def _get_timestamps(self, identifier: str) -> List[float]:
        """Get timestamps list for identifier, creating if needed."""
        # This is a simplified version - in practice we'd have separate stores
        # For now, we'll use a combined approach or have caller specify store type
        # This method will be overridden or used differently in subclasses
        raise NotImplementedError

    def _remove_empty_key(self, identifier: str):
        """Remove empty key from appropriate store."""
        pass

    def _cleanup_old_entries(self, now: float):
        """Remove entries older than window from both stores."""
        cutoff = now - self.window_seconds

        # Clean IP attempts
        to_delete_ip = []
        for key, timestamps in self.ip_attempts.items():
            # Remove old timestamps
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            if not timestamps:
                to_delete_ip.append(key)
        for key in to_delete_ip:
            del self.ip_attempts[key]

        # Clean credential attempts
        to_delete_cred = []
        for key, timestamps in self.credential_attempts.items():
            # Remove old timestamps
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            if not timestamps:
                to_delete_cred.append(key)
        for key in to_delete_cred:
            del self.credential_attempts[key]


class IPLoginRateLimiter(LoginRateLimiter):
    """Tracks login failures by IP address."""

    def _get_timestamps(self, identifier: str) -> List[float]:
        return self.ip_attempts[identifier]

    def _remove_empty_key(self, identifier: str):
        if identifier in self.ip_attempts and not self.ip_attempts[identifier]:
            del self.ip_attempts[identifier]


class CredentialLoginRateLimiter(LoginRateLimiter):
    """Tracks login failures by email/username."""

    def _get_timestamps(self, identifier: str) -> List[float]:
        return self.credential_attempts[identifier]

    def _remove_empty_key(self, identifier: str):
        if identifier in self.credential_attempts and not self.credential_attempts[identifier]:
            del self.credential_attempts[identifier]


def create_login_rate_limit_dependency(max_attempts: int = 5, window_seconds: int = 300):
    """
    FastAPI dependency for login rate limiting by IP address.

    Args:
        max_attempts: Maximum attempts allowed in window (default: 5)
        window_seconds: Time window in seconds (default: 300 = 5 minutes)

    Usage:
        @app.post("/login", dependencies=[Depends(create_login_rate_limit_dependency())])
    """
    ip_limiter = IPLoginRateLimiter(max_attempts, window_seconds)

    async def dependency(request: Request):
        # Get client IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host or "unknown"

        if not ip_limiter.is_allowed(ip):
            logger.warning(
                "Login rate limit exceeded by IP",
                ip=ip,
                path=request.url.path
            )
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency


def create_credential_rate_limit_dependency(max_attempts: int = 3, window_seconds: int = 900):
    """
    FastAPI dependency for login rate limiting by email/username.
    More restrictive than IP-based locking to prevent targeted attacks.

    Args:
        max_attempts: Maximum attempts allowed in window (default: 3)
        window_seconds: Time window in seconds (default: 900 = 15 minutes)

    Usage:
        @app.post("/login", dependencies=[Depends(create_credential_rate_limit_dependency())])
    """
    credential_limiter = CredentialLoginRateLimiter(max_attempts, window_seconds)

    async def dependency(request: Request):
        # Extract email from request body (for POST requests)
        # This is a simplified version - in practice we'd parse the body properly
        # For now, we'll rely on the endpoint to extract and pass the email
        # In a real implementation, we might read the body or use a dependency that provides email
        email = getattr(request.state, 'login_email', None)
        if not email:
            # If we can't extract email, fall back to IP-based limiting only
            # or skip credential-based check for this request
            return

        if not credential_limiter.is_allowed(email):
            logger.warning(
                "Login rate limit exceeded by credential",
                email=email[:10] + "***",  # Partial email for privacy
                path=request.url.path
            )
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts for this account. Please try again later.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency