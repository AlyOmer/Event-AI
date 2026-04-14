"""
Vendor Service Management API
CRUD operations for vendor services
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.config.database import get_session
from src.models.user import User
from src.models.vendor import Vendor
from src.models.service import Service
from src.schemas.service import ServiceCreate, ServiceUpdate, ServiceRead
from src.api.deps import get_current_user
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["Vendor Services"])


async def get_vendor_for_user(session: AsyncSession, user: User) -> Vendor:
    """Helper to get the vendor profile for the current authenticated user."""
    stmt = select(Vendor).where(Vendor.user_id == user.id)
    result = await session.execute(stmt)
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor profile not found. Please register as a vendor first."
        )
    return vendor


@router.get("/my-services", response_model=List[ServiceRead])
async def list_my_services(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all services for the current vendor."""
    vendor = await get_vendor_for_user(session, current_user)
    
    stmt = select(Service).where(Service.vendor_id == vendor.id).order_by(Service.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_in: ServiceCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new service for the current vendor."""
    vendor = await get_vendor_for_user(session, current_user)
    
    new_service = Service(
        **service_in.model_dump(),
        vendor_id=vendor.id
    )
    session.add(new_service)
    await session.commit()
    await session.refresh(new_service)
    
    logger.info("service.created", service_id=str(new_service.id), vendor_id=str(vendor.id))
    return new_service


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific service by ID (must belong to current vendor)."""
    vendor = await get_vendor_for_user(session, current_user)
    
    service = await session.get(Service, service_id)
    if not service or service.vendor_id != vendor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or you don't have permission to access it"
        )
    return service


@router.put("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: uuid.UUID,
    service_in: ServiceUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a service (must belong to current vendor)."""
    vendor = await get_vendor_for_user(session, current_user)
    
    service = await session.get(Service, service_id)
    if not service or service.vendor_id != vendor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or you don't have permission to modify it"
        )
    
    update_data = service_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    
    await session.commit()
    await session.refresh(service)
    
    logger.info("service.updated", service_id=str(service.id), vendor_id=str(vendor.id))
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a service (must belong to current vendor)."""
    vendor = await get_vendor_for_user(session, current_user)
    
    service = await session.get(Service, service_id)
    if not service or service.vendor_id != vendor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or you don't have permission to delete it"
        )
    
    await session.delete(service)
    await session.commit()
    
    logger.info("service.deleted", service_id=str(service_id), vendor_id=str(vendor.id))
    return None
