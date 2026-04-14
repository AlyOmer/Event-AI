"""
File Upload API
Endpoints for generating pre-signed URLs for direct CDN upload
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import uuid

from src.services.cdn_service import cdn_service
from src.models.user import User
from src.models.vendor import Vendor
from src.api.deps import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.database import get_session
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["File Uploads"])


class UploadURLRequest(BaseModel):
    content_type: str = Field(default="image/jpeg", pattern="^image/(jpeg|jpg|png|webp)$")
    file_size_mb: int = Field(default=1, le=5)


class UploadURLResponse(BaseModel):
    upload_url: str
    file_key: str
    public_url: str
    expires_in_seconds: int = 300


async def get_vendor_for_user(session, user: User) -> Optional[Vendor]:
    """Helper to get vendor profile for current user."""
    stmt = select(Vendor).where(Vendor.user_id == user.id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.post("/portfolio", response_model=UploadURLResponse)
async def get_portfolio_upload_url(
    request: UploadURLRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Generate a pre-signed URL for uploading a portfolio image.
    Client uploads directly to CDN, then sends the file_key to backend.
    Max 5 images per vendor enforced in vendor profile update.
    """
    vendor = await get_vendor_for_user(session, current_user)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor profile not found"
        )
    
    try:
        upload_url, file_key = cdn_service.generate_upload_url(
            file_type="image",
            content_type=request.content_type,
            max_size_mb=request.file_size_mb,
            vendor_id=vendor.id
        )
        
        public_url = cdn_service.get_public_url(file_key)
        
        logger.info("portfolio.upload_url_generated", vendor_id=str(vendor.id), file_key=file_key)
        
        return UploadURLResponse(
            upload_url=upload_url,
            file_key=file_key,
            public_url=public_url,
            expires_in_seconds=300
        )
        
    except RuntimeError as e:
        logger.error("portfolio.upload_url_failed", vendor_id=str(vendor.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
