"""
Customer Inquiry API
Endpoints for customers to contact vendors and vendors to manage inquiries
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from src.config.database import get_session
from src.models.user import User
from src.models.vendor import Vendor
from src.models.inquiry import CustomerInquiry, InquiryStatus
from src.schemas.inquiry import CustomerInquiryCreate, CustomerInquiryUpdate, CustomerInquiryRead
from src.api.deps import get_current_user
from src.services.event_bus_service import event_bus
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["Customer Inquiries"])


async def get_vendor_for_user(session: AsyncSession, user: User) -> Vendor:
    """Helper to get the vendor profile for the current authenticated user."""
    stmt = select(Vendor).where(Vendor.user_id == user.id)
    result = await session.execute(stmt)
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor profile not found."
        )
    return vendor


# Public endpoint - no auth required
@router.post("/public/{vendor_id}", response_model=CustomerInquiryRead, status_code=status.HTTP_201_CREATED)
async def create_public_inquiry(
    vendor_id: uuid.UUID,
    inquiry_in: CustomerInquiryCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Public endpoint for customers to submit inquiries to a vendor.
    No authentication required.
    """
    # Verify vendor exists and is active
    from src.models.vendor import VendorStatus
    vendor = await session.get(Vendor, vendor_id)
    if not vendor or vendor.status != VendorStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found or not active"
        )
    
    new_inquiry = CustomerInquiry(
        **inquiry_in.model_dump(),
        vendor_id=vendor_id
    )
    session.add(new_inquiry)
    await session.commit()
    await session.refresh(new_inquiry)

    logger.info("inquiry.created", inquiry_id=str(new_inquiry.id), vendor_id=str(vendor_id))

    # Emit domain event
    await event_bus.emit(
        session,
        "inquiry.created",
        {"inquiry_id": str(new_inquiry.id), "vendor_id": str(vendor_id), "customer_email": new_inquiry.customer_email},
    )

    return new_inquiry


# Vendor endpoints - auth required
@router.get("/vendor/my-inquiries", response_model=List[CustomerInquiryRead])
async def list_vendor_inquiries(
    status: Optional[InquiryStatus] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all inquiries for the current vendor with optional status filter."""
    vendor = await get_vendor_for_user(session, current_user)
    
    stmt = select(CustomerInquiry).where(CustomerInquiry.vendor_id == vendor.id)
    if status:
        stmt = stmt.where(CustomerInquiry.status == status)
    
    stmt = stmt.order_by(desc(CustomerInquiry.created_at)).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/vendor/{inquiry_id}", response_model=CustomerInquiryRead)
async def get_vendor_inquiry(
    inquiry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific inquiry (must belong to current vendor)."""
    vendor = await get_vendor_for_user(session, current_user)
    
    inquiry = await session.get(CustomerInquiry, inquiry_id)
    if not inquiry or inquiry.vendor_id != vendor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inquiry not found or you don't have permission to access it"
        )
    return inquiry


@router.put("/vendor/{inquiry_id}", response_model=CustomerInquiryRead)
async def update_inquiry_status(
    inquiry_id: uuid.UUID,
    inquiry_in: CustomerInquiryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update an inquiry status and/or add vendor response.
    Only the vendor who owns the inquiry can update it.
    """
    vendor = await get_vendor_for_user(session, current_user)
    
    inquiry = await session.get(CustomerInquiry, inquiry_id)
    if not inquiry or inquiry.vendor_id != vendor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inquiry not found or you don't have permission to modify it"
        )
    
    update_data = inquiry_in.model_dump(exclude_unset=True)
    
    # If adding a response, set the responded_at timestamp
    if "vendor_response" in update_data and update_data["vendor_response"]:
        inquiry.vendor_responded_at = datetime.now(timezone.utc)
    
    for field, value in update_data.items():
        setattr(inquiry, field, value)
    
    await session.commit()
    await session.refresh(inquiry)
    
    logger.info("inquiry.updated", inquiry_id=str(inquiry.id), vendor_id=str(vendor.id), status=inquiry.status.value)
    return inquiry
