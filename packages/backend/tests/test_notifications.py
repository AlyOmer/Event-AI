"""
Tests for Notification System (Module 010 gaps).

Run with: uv run pytest tests/test_notifications.py -v
"""
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.notification import Notification, NotificationType
from src.services.notification_service import NotificationService, _EVENT_MAP

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client, email=None):
    email = email or f"notif_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPass123!",
        "first_name": "Notif", "last_name": "User",
    })
    assert r.status_code == 201
    return r.json()["access_token"], email


def make_mock_session():
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    # Mock execute to return a result object with scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ── Service: handle() for booking events ─────────────────────────────────────

@pytest.mark.parametrize("event_type", [
    "booking.created", "booking.confirmed", "booking.cancelled",
    "booking.completed", "booking.rejected", "booking.status_changed",
])
async def test_handle_booking_events_creates_notification(event_type):
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            await svc.handle(
                event_type=event_type,
                payload={"booking_id": str(uuid.uuid4()), "new_status": "confirmed"},
                user_id=user_id,
                session=session,
            )

    session.add.assert_called()


# ── Service: handle() for event domain events ─────────────────────────────────

@pytest.mark.parametrize("event_type,payload_extra", [
    ("event.created",        {"name": "My Wedding"}),
    ("event.status_changed", {"name": "My Wedding", "new_status": "active"}),
    ("event.cancelled",      {"name": "My Wedding"}),
])
async def test_handle_event_domain_events(event_type, payload_extra):
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    payload = {"user_id": str(user_id), "event_id": str(uuid.uuid4()), **payload_extra}

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            await svc.handle(event_type=event_type, payload=payload, session=session)

    session.add.assert_called_once()


# ── Service: handle() for vendor domain events ────────────────────────────────

@pytest.mark.parametrize("event_type", ["vendor.approved", "vendor.rejected"])
async def test_handle_vendor_domain_events(event_type):
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    payload = {"user_id": str(user_id), "vendor_id": str(uuid.uuid4()), "business_name": "Test Vendor"}

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            await svc.handle(event_type=event_type, payload=payload, session=session)

    session.add.assert_called_once()


async def test_handle_unknown_event_type_is_noop():
    svc = NotificationService()
    session = make_mock_session()
    await svc.handle(event_type="unknown.event", payload={}, session=session)
    session.add.assert_not_called()


async def test_handle_missing_user_id_logs_warning():
    svc = NotificationService()
    session = make_mock_session()
    # event.created without user_id in payload
    await svc.handle(event_type="event.created", payload={"event_id": str(uuid.uuid4())}, session=session)
    session.add.assert_not_called()


async def test_handle_preference_disabled_skips_notification():
    svc = NotificationService()
    user_id = uuid.uuid4()
    session = make_mock_session()

    payload = {"user_id": str(user_id), "event_id": str(uuid.uuid4()), "name": "Test"}

    with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=False):
        await svc.handle(event_type="event.created", payload=payload, session=session)

    session.add.assert_not_called()


# ── Route: list notifications ─────────────────────────────────────────────────

async def test_list_notifications_returns_envelope(client):
    token, _ = await register_and_login(client)
    r = await client.get("/api/v1/notifications/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "data" in body
    assert "meta" in body
    assert "total" in body["meta"]


async def test_list_notifications_unread_only(client, db_session):
    token, _ = await register_and_login(client)
    r = await client.get(
        "/api/v1/notifications/?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True


async def test_unread_count_returns_envelope(client):
    token, _ = await register_and_login(client)
    r = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["count"] == 0


async def test_mark_all_read(client):
    token, _ = await register_and_login(client)
    r = await client.patch("/api/v1/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["success"] is True


# ── Route: mark single read ───────────────────────────────────────────────────

async def test_mark_read_returns_envelope(client, db_session):
    token, _ = await register_and_login(client)

    # Get user_id from /me
    me_r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me_r.json()["id"])

    # Insert a notification directly
    notif = Notification(
        user_id=user_id,
        type=NotificationType.system,
        title="Test",
        body="Test body",
        data={},
    )
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)

    r = await client.patch(
        f"/api/v1/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["is_read"] is True


# ── Route: delete single notification ────────────────────────────────────────

async def test_delete_notification_success(client, db_session):
    token, _ = await register_and_login(client)
    me_r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me_r.json()["id"])

    notif = Notification(user_id=user_id, type=NotificationType.system, title="Del", body="body", data={})
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)

    r = await client.delete(f"/api/v1/notifications/{notif.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["success"] is True


async def test_delete_notification_not_found(client):
    token, _ = await register_and_login(client)
    r = await client.delete(
        f"/api/v1/notifications/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND_NOTIFICATION"


async def test_delete_notification_forbidden(client, db_session):
    token1, _ = await register_and_login(client)
    token2, _ = await register_and_login(client)

    me_r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    user_id = uuid.UUID(me_r.json()["id"])

    notif = Notification(user_id=user_id, type=NotificationType.system, title="Private", body="body", data={})
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)

    r = await client.delete(f"/api/v1/notifications/{notif.id}", headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "AUTH_FORBIDDEN"


# ── Route: delete read notifications ─────────────────────────────────────────

async def test_delete_read_notifications(client, db_session):
    token, _ = await register_and_login(client)
    me_r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me_r.json()["id"])

    # Insert 2 read + 1 unread
    for i in range(2):
        n = Notification(user_id=user_id, type=NotificationType.system, title=f"Read {i}", body="b", data={}, is_read=True)
        db_session.add(n)
    n_unread = Notification(user_id=user_id, type=NotificationType.system, title="Unread", body="b", data={}, is_read=False)
    db_session.add(n_unread)
    await db_session.commit()

    r = await client.delete("/api/v1/notifications/read", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] == 2


async def test_delete_read_notifications_zero(client):
    token, _ = await register_and_login(client)
    r = await client.delete("/api/v1/notifications/read", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] == 0


# ── Route: preferences ────────────────────────────────────────────────────────

async def test_get_preferences_empty(client):
    token, _ = await register_and_login(client)
    r = await client.get("/api/v1/notifications/preferences", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"] == []


async def test_put_preference(client):
    token, _ = await register_and_login(client)
    r = await client.put(
        "/api/v1/notifications/preferences/booking_created",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["enabled"] is False
    assert r.json()["data"]["notification_type"] == "booking_created"


async def test_put_preference_invalid_type_422(client):
    token, _ = await register_and_login(client)
    r = await client.put(
        "/api/v1/notifications/preferences/invalid_type_xyz",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_unauthenticated_401(client):
    r = await client.get("/api/v1/notifications/")
    assert r.status_code == 401


# ── Deduplication tests (7.2) ─────────────────────────────────────────────────

async def test_deduplication_skips_duplicate_within_window():
    """Test that duplicate notifications are skipped within 5-minute window."""
    svc = NotificationService()
    user_id = uuid.uuid4()
    booking_id = str(uuid.uuid4())
    session = make_mock_session()

    # Mock existing notification with same booking_id
    existing_notif = Notification(
        user_id=user_id,
        type=NotificationType.booking_confirmed,
        title="Test",
        body="Body",
        data={"booking_id": booking_id},
    )

    with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
        with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=True):
            await svc.handle(
                event_type="booking.confirmed",
                payload={"booking_id": booking_id},
                user_id=user_id,
                session=session,
            )

    session.add.assert_not_called()


async def test_deduplication_allows_after_window():
    """Test that notifications are allowed after dedup window expires."""
    svc = NotificationService()
    user_id = uuid.uuid4()
    booking_id = str(uuid.uuid4())
    session = make_mock_session()

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock):
                    await svc.handle(
                        event_type="booking.confirmed",
                        payload={"booking_id": booking_id},
                        user_id=user_id,
                        session=session,
                    )

    session.add.assert_called()


# ── Email integration tests (7.1) ────────────────────────────────────────────

async def test_email_sent_on_booking_event():
    """Test that email is queued when booking event fires."""
    svc = NotificationService()
    user_id = uuid.uuid4()
    booking_id = str(uuid.uuid4())
    session = make_mock_session()

    # Mock booking with user
    mock_booking = MagicMock()
    mock_booking.user_id = user_id
    mock_booking.vendor_id = None
    mock_booking.event_name = "Test Event"
    mock_booking.event_date = "2026-05-15"
    session.get = AsyncMock(return_value=mock_booking)

    with patch("src.services.notification_service.NotificationService._push_sse", new_callable=AsyncMock):
        with patch("src.services.notification_service.NotificationService._is_enabled_for_user", new_callable=AsyncMock, return_value=True):
            with patch("src.services.notification_service.NotificationService._is_duplicate", new_callable=AsyncMock, return_value=False):
                with patch("src.services.notification_service.NotificationService._send_email", new_callable=AsyncMock) as mock_email:
                    await svc.handle(
                        event_type="booking.confirmed",
                        payload={"booking_id": booking_id},
                        user_id=user_id,
                        session=session,
                    )

    mock_email.assert_called_once()
