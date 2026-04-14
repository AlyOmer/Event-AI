"""
Admin Category Management API
CRUD operations for marketplace categories (admin only)
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.config.database import get_session
from src.models.user import User
from src.models.category import Category
from src.schemas.category import CategoryCreate, CategoryUpdate, CategoryRead
from src.api.deps import get_current_user, require_admin
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["Admin Categories"])


@router.get("/", response_model=List[CategoryRead])
async def list_all_categories(
    include_inactive: bool = False,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Admin: List all categories (including inactive if requested)."""
    stmt = select(Category).order_by(Category.display_order)
    if not include_inactive:
        stmt = stmt.where(Category.is_active == True)
    
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Admin: Create a new marketplace category."""
    # Check for duplicate name
    existing = await session.execute(
        select(Category).where(Category.name.ilike(category_in.name))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{category_in.name}' already exists"
        )
    
    new_category = Category(**category_in.model_dump())
    session.add(new_category)
    await session.commit()
    await session.refresh(new_category)
    
    logger.info("category.created", category_id=str(new_category.id), name=new_category.name, admin_id=str(current_user.id))
    return new_category


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Admin: Get a specific category by ID."""
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: uuid.UUID,
    category_in: CategoryUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Admin: Update a category."""
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Check for name conflict if updating name
    if category_in.name and category_in.name != category.name:
        existing = await session.execute(
            select(Category).where(Category.name.ilike(category_in.name))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with name '{category_in.name}' already exists"
            )
    
    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    await session.commit()
    await session.refresh(category)
    
    logger.info("category.updated", category_id=str(category.id), admin_id=str(current_user.id))
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_category(
    category_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """Admin: Soft-delete (deactivate) a category. Cannot delete if vendors are assigned."""
    category = await session.execute(
        select(Category).where(Category.id == category_id).options(selectinload(Category.vendors))
    )
    category = category.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Check if category has assigned vendors
    if category.vendors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete category with assigned vendors. Deactivate instead."
        )
    
    # Soft delete by deactivating
    category.is_active = False
    await session.commit()
    
    logger.info("category.deactivated", category_id=str(category_id), admin_id=str(current_user.id))
    return None
