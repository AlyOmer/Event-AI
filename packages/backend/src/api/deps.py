"""
Dependency injection helpers for API routes.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.services.auth_service import auth_service
from src.services.event_bus_service import event_bus, EventBusService
from src.models.user import User

# OAuth2 scheme — token endpoint is /api/v1/auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    FastAPI dependency that extracts JWT from Authorization header,
    validates it, and returns the authenticated User.
    Raises HTTPException(401) on failure.
    """
    return await auth_service.verify_access_token(token, session)


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the current user has admin role.
    Raises HTTPException(403) if user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires administrator privileges"
        )
    return current_user

def get_event_bus() -> EventBusService:
    """Dependency injection for the domain event bus."""
    return event_bus
