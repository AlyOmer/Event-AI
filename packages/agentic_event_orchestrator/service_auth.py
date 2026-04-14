"""
service_auth.py — Service-to-Service Authentication

Fixes Gap #4: Agent tools calling the backend with no auth.
All requests.post/get/patch calls in booking_tools.py, event_tools.py etc.
must include a signed header so the backend can reject unauthenticated callers.

Approach: Shared secret (HMAC-SHA256 signed timestamp) — lightweight, no
dependency on a full JWT library for internal service calls.
"""

import os
import hmac
import hashlib
import time
import logging

logger = logging.getLogger("service_auth")

# ── Shared Secret ─────────────────────────────────────────────────────────────
# Set the same value in both:
#   packages/agentic_event_orchestrator/.env  →  SERVICE_SECRET
#   packages/backend/.env                     →  AGENT_SERVICE_SECRET
SERVICE_SECRET = os.getenv("SERVICE_SECRET", "").encode()

# Timestamp tolerance — reject requests older than this many seconds
TIMESTAMP_TOLERANCE = 30  # seconds


def _get_secret() -> bytes:
    """Return the shared secret, warning loudly if not set."""
    if not SERVICE_SECRET:
        logger.warning(
            "SERVICE_SECRET not set — service-to-service calls are unauthenticated! "
            "Set SERVICE_SECRET in .env for production."
        )
        return b"dev-insecure-secret"
    return SERVICE_SECRET


def make_service_headers(method: str = "POST", path: str = "/") -> dict:
    """
    Generate HMAC-signed headers for an inter-service request.

    The backend verifies:
      1. X-Service-Timestamp is recent (within TIMESTAMP_TOLERANCE seconds)
      2. X-Service-Signature matches HMAC-SHA256(secret, method+path+timestamp)

    Usage:
        response = requests.post(
            f"{BACKEND_URL}/bookings",
            json={...},
            headers=make_service_headers("POST", "/api/v1/bookings"),
            timeout=10,
        )
    """
    secret = _get_secret()
    ts = str(int(time.time()))
    payload = f"{method.upper()}:{path}:{ts}".encode()
    signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    return {
        "X-Service-Timestamp": ts,
        "X-Service-Signature": signature,
        "X-Service-Name": "agentic-orchestrator",
        "Content-Type": "application/json",
    }


def verify_service_request(
    method: str,
    path: str,
    timestamp_str: str,
    signature: str,
) -> tuple[bool, str]:
    """
    Verify an incoming service-to-service request on the backend side.

    Returns:
        (is_valid, error_reason)
    """
    secret = _get_secret()

    # 1. Check timestamp freshness
    try:
        ts = int(timestamp_str)
        age = abs(int(time.time()) - ts)
        if age > TIMESTAMP_TOLERANCE:
            return False, f"Request too old ({age}s). Possible replay attack."
    except (ValueError, TypeError):
        return False, "Invalid timestamp format."

    # 2. Recompute and compare signature
    payload = f"{method.upper()}:{path}:{timestamp_str}".encode()
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return False, "Invalid service signature."

    return True, ""


# ── Convenience: signed requests session ──────────────────────────────────────

import requests as _requests
from urllib.parse import urlparse as _urlparse


def signed_post(url: str, json: dict, timeout: int = 10) -> _requests.Response:
    """Authenticated POST to backend. Replaces bare requests.post() in tools."""
    path = _urlparse(url).path
    return _requests.post(url, json=json, headers=make_service_headers("POST", path), timeout=timeout)


def signed_get(url: str, params: dict = None, timeout: int = 10) -> _requests.Response:
    """Authenticated GET to backend."""
    path = _urlparse(url).path
    return _requests.get(url, params=params, headers=make_service_headers("GET", path), timeout=timeout)


def signed_patch(url: str, json: dict, timeout: int = 10) -> _requests.Response:
    """Authenticated PATCH to backend."""
    path = _urlparse(url).path
    return _requests.patch(url, json=json, headers=make_service_headers("PATCH", path), timeout=timeout)
