"""
Authentication service: password hashing, JWT access tokens, DB-backed refresh tokens with rotation.
"""
import hashlib
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_settings
from ..models.user import User, RefreshToken, PasswordResetToken

logger = structlog.get_logger()
settings = get_settings()


def _generate_token_hash(token: str) -> str:
    """SHA-256 hash of token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """Core authentication operations."""

    # ============ Password Hashing ============

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt (rounds=12)."""
        # Truncate password to 72 bytes to avoid bcrypt error if it's too long
        encoded = password.encode('utf-8')[:72]
        return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a hash."""
        encoded = plain_password.encode('utf-8')[:72]
        try:
            return bcrypt.checkpw(encoded, hashed_password.encode('utf-8'))
        except ValueError:
            return False

    # ============ JWT Access Token ============

    @classmethod
    def create_access_token(cls, user: User) -> tuple[str, int]:
        """
        Create a signed JWT access token.

        Claims: sub (user_id), email, role, iat, exp, iss="event-ai".
        Expiry: 15 minutes (configurable).
        """
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "iat": datetime.now(timezone.utc),
            "exp": expire,
            "iss": "event-ai",
        }
        encoded = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded, int(timedelta(minutes=settings.access_token_expire_minutes).total_seconds())

    @classmethod
    async def verify_access_token(cls, token: str, session: AsyncSession) -> User:
        """
        Decode and validate JWT access token, then fetch the user.
        Raises HTTPException(401) on failure with WWW-Authenticate header.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_CREDENTIALS_INVALID", "message": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                issuer="event-ai",
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError as e:
            logger.warning("auth.token.decode_failed", error=str(e))
            raise credentials_exception from e

        import uuid
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError:
            raise credentials_exception
            
        user = await session.get(User, parsed_id)
        if not user or not user.is_active:
            raise credentials_exception
        return user

    # ============ Refresh Token (DB-Backed, Rotation) ============

    @classmethod
    async def create_refresh_token(cls, session: AsyncSession, user: User) -> tuple[str, datetime]:
        """
        Generate a new refresh token, store its hash in the DB.
        Returns (raw_token, expires_at).
        """
        raw_token = secrets.token_urlsafe(64)
        token_hash = _generate_token_hash(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(refresh_record)
        await session.commit()
        await session.refresh(refresh_record)

        logger.info("auth.refresh.created", user_id=str(user.id), token_id=str(refresh_record.id))
        return raw_token, expires_at

    @classmethod
    async def create_tokens(cls, session: AsyncSession, user: User) -> dict:
        """
        Convenience: generate both access and refresh tokens.
        Returns dict matching Token Pydantic schema.
        """
        access_token, expires_in = cls.create_access_token(user)
        refresh_token, _ = await cls.create_refresh_token(session, user)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "refresh_token": refresh_token,
        }

    @classmethod
    async def verify_refresh_token_raw(cls, session: AsyncSession, raw_token: str) -> User:
        """
        Validate a raw refresh token string: hash it, look up in DB,
        check not revoked and not expired. Return associated user.
        Raises HTTPException(401) if invalid.
        """
        token_hash = _generate_token_hash(raw_token)

        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        result = await session.execute(stmt)
        refresh_record = result.scalar_one_or_none()

        if not refresh_record:
            logger.warning("auth.refresh.invalid", hash_prefix=token_hash[:8])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user = await session.get(User, refresh_record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        return user

    @classmethod
    async def rotate_refresh_token(cls, session: AsyncSession, raw_token: str) -> dict:
        """
        Token rotation: invalidate the provided refresh token and issue a new pair.
        Returns new Token dict.
        """
        token_hash = _generate_token_hash(raw_token)

        # Find and validate old token
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        result = await session.execute(stmt)
        old_record = result.scalar_one_or_none()

        if not old_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Revoke old token
        old_record.revoked_at = datetime.now(timezone.utc)
        user = await session.get(User, old_record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Issue new tokens
        new_tokens = await cls.create_tokens(session, user)
        await session.commit()

        logger.info("auth.refresh.rotated", user_id=str(user.id), old_token_id=str(old_record.id))
        return new_tokens

    @classmethod
    async def revoke_refresh_token(cls, session: AsyncSession, raw_token: str) -> None:
        """
        Revoke a single refresh token (logout). Does NOT require user_id
        — token hash uniquely identifies it.
        """
        token_hash = _generate_token_hash(raw_token)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        result = await session.execute(stmt)
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        logger.info("auth.logout", token_revoked=True)

    @classmethod
    async def revoke_all_refresh_tokens(cls, session: AsyncSession, user_id: str) -> None:
        """
        Revoke ALL refresh tokens for a user (e.g., after password reset).
        """
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await session.execute(stmt)
        await session.commit()
        logger.info("auth.revoke_all", user_id=user_id)

    # ============ Password Reset ============

    @classmethod
    async def create_password_reset_token(cls, session: AsyncSession, user: User) -> tuple[str, datetime]:
        """
        Generate a one-time password reset token.
        Returns (raw_token, expires_at).
        """
        raw_token = secrets.token_urlsafe(32)
        token_hash = _generate_token_hash(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(reset_token)
        await session.commit()
        await session.refresh(reset_token)

        logger.info("auth.password_reset.created", user_id=str(user.id), token_id=str(reset_token.id))
        return raw_token, expires_at

    @classmethod
    async def verify_and_consume_password_reset_token(
        cls, session: AsyncSession, raw_token: str
    ) -> User:
        """
        Validate a password reset token (hash, not expired, not used),
        mark it as used, and return the associated user.
        """
        token_hash = _generate_token_hash(raw_token)

        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
        result = await session.execute(stmt)
        reset_record = result.scalar_one_or_none()

        if not reset_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        user = await session.get(User, reset_record.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token",
            )

        # Mark token used
        reset_record.used_at = datetime.now(timezone.utc)
        await session.commit()

        return user

    @classmethod
    async def reset_password(cls, session: AsyncSession, user: User, new_password: str) -> None:
        """
        Update user's password and invalidate all existing refresh tokens.
        """
        user.password_hash = cls.hash_password(new_password)
        await cls.revoke_all_refresh_tokens(session, user.id)
        await session.commit()
        logger.info("auth.password_reset.completed", user_id=str(user.id))


# Global singleton
auth_service = AuthService()
