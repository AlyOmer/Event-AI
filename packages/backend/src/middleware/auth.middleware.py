"""
Authentication middleware for verifying JWT tokens and attaching user to request.
"""
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from src.services.auth_service import auth_service
from src.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# Security scheme for extracting Bearer token
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    """
    Extract and verify JWT token from Authorization header.
    Attaches user information to request state if valid.

    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        session: Database session

    Returns:
        User object if token valid, raises HTTPException otherwise
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        # Verify and decode the access token
        payload = auth_service.verify_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch user from database
        from src.models import User
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("User not found for token", user_id=user_id)
            raise HTTPException(
                status_code=401,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning("Inactive user attempted access", user_id=user_id)
            raise HTTPException(
                status_code=401,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Attach user to request state for easy access in routes
        request.state.user = user
        return user

    except Exception as e:
        logger.warning("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Optional: Dependency that returns None if no auth (for public endpoints that can use auth)
async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> Optional[object]:
    """
    Similar to get_current_user but returns None instead of raising exception
    when no or invalid token is provided.

    Useful for endpoints that work both with and without authentication.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, session)
    except HTTPException:
        return None