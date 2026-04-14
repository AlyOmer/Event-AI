"""
Unit tests for AuthService — targets the CURRENT API (not the old stale one).

AuthService API under test:
  - hash_password(password) -> str
  - verify_password(plain, hashed) -> bool
  - create_access_token(user) -> (jwt_str, expires_in_seconds)
  - verify_access_token(token, session) -> User
  - create_refresh_token(session, user) -> (raw_token, expires_at)
  - verify_refresh_token_raw(session, raw_token) -> User
  - rotate_refresh_token(session, raw_token) -> dict
  - revoke_refresh_token(session, raw_token) -> None
  - create_password_reset_token(session, user) -> (raw_token, expires_at)
  - verify_and_consume_password_reset_token(session, raw_token) -> User
  - reset_password(session, user, new_password) -> None
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from jose import jwt

from src.config.database import get_settings
from src.models.user import User, RefreshToken, PasswordResetToken
from src.services.auth_service import AuthService, _generate_token_hash

settings = get_settings()

_counter = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(**kwargs) -> User:
    global _counter
    _counter += 1
    defaults = dict(
        id=uuid.uuid4(),
        email=f"test{_counter}@example.com",
        password_hash=AuthService.hash_password("StrongPass123!"),
        first_name="Test",
        last_name="User",
        role="user",
        is_active=True,
        email_verified=False,
        failed_login_attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return User(**defaults)


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_bcrypt(self):
        h = AuthService.hash_password("MyPassword1!")
        assert h.startswith("$2b$")

    def test_verify_correct_password(self):
        h = AuthService.hash_password("MyPassword1!")
        assert AuthService.verify_password("MyPassword1!", h) is True

    def test_verify_wrong_password(self):
        h = AuthService.hash_password("MyPassword1!")
        assert AuthService.verify_password("WrongPass!", h) is False

    def test_verify_empty_password(self):
        h = AuthService.hash_password("MyPassword1!")
        assert AuthService.verify_password("", h) is False


# ── Access token ──────────────────────────────────────────────────────────────

class TestAccessToken:
    def test_returns_tuple(self):
        user = make_user()
        result = AuthService.create_access_token(user)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_token_is_string(self):
        user = make_user()
        token, expires_in = AuthService.create_access_token(user)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_expires_in_is_seconds(self):
        user = make_user()
        _, expires_in = AuthService.create_access_token(user)
        assert expires_in == settings.access_token_expire_minutes * 60

    def test_claims(self):
        user = make_user(role="admin")
        token, _ = AuthService.create_access_token(user)
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer="event-ai",
        )
        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email
        assert payload["role"] == "admin"
        assert payload["iss"] == "event-ai"

    def test_token_hash_helper(self):
        raw = "some_token_value"
        h = _generate_token_hash(raw)
        assert h == hashlib.sha256(raw.encode()).hexdigest()


# ── Refresh token ─────────────────────────────────────────────────────────────

class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_create_returns_tuple(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()

        raw_token, expires_at = await AuthService.create_refresh_token(db_session, user)
        assert isinstance(raw_token, str)
        assert len(raw_token) > 0
        assert isinstance(expires_at, datetime)

    @pytest.mark.asyncio
    async def test_token_stored_as_hash(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()

        raw_token, _ = await AuthService.create_refresh_token(db_session, user)
        expected_hash = _generate_token_hash(raw_token)

        from sqlalchemy import select
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == expected_hash)
        )
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.user_id == user.id

    @pytest.mark.asyncio
    async def test_verify_valid_token_returns_user(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()

        raw_token, _ = await AuthService.create_refresh_token(db_session, user)
        returned_user = await AuthService.verify_refresh_token_raw(db_session, raw_token)
        assert returned_user.id == user.id

    @pytest.mark.asyncio
    async def test_verify_invalid_token_raises_401(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.verify_refresh_token_raw(db_session, "totally_invalid_token")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rotate_revokes_old_and_returns_new(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()

        raw_token, _ = await AuthService.create_refresh_token(db_session, user)
        new_tokens = await AuthService.rotate_refresh_token(db_session, raw_token)

        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["refresh_token"] != raw_token

        # Old token should now be revoked
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.verify_refresh_token_raw(db_session, raw_token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_revoke_token(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()

        raw_token, _ = await AuthService.create_refresh_token(db_session, user)
        await AuthService.revoke_refresh_token(db_session, raw_token)

        with pytest.raises(HTTPException):
            await AuthService.verify_refresh_token_raw(db_session, raw_token)

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_raises_401(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.revoke_refresh_token(db_session, "nonexistent_token")
        assert exc_info.value.status_code == 401


# ── Password reset ────────────────────────────────────────────────────────────

class TestPasswordReset:
    @pytest.mark.asyncio
    async def test_create_reset_token(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()

        raw_token, expires_at = await AuthService.create_password_reset_token(db_session, user)
        assert isinstance(raw_token, str)
        assert expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_verify_and_consume_valid_token(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()

        raw_token, _ = await AuthService.create_password_reset_token(db_session, user)
        returned_user = await AuthService.verify_and_consume_password_reset_token(db_session, raw_token)
        assert returned_user.id == user.id

    @pytest.mark.asyncio
    async def test_token_single_use(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()

        raw_token, _ = await AuthService.create_password_reset_token(db_session, user)
        await AuthService.verify_and_consume_password_reset_token(db_session, raw_token)

        with pytest.raises(HTTPException) as exc_info:
            await AuthService.verify_and_consume_password_reset_token(db_session, raw_token)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_token_raises_400(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.verify_and_consume_password_reset_token(db_session, "bad_token")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_changes_hash(self, db_session):
        user = make_user()
        db_session.add(user)
        await db_session.flush()
        old_hash = user.password_hash

        await AuthService.reset_password(db_session, user, "NewStrongPass456!")
        assert user.password_hash != old_hash
        assert AuthService.verify_password("NewStrongPass456!", user.password_hash)
