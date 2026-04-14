from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.database import get_session
from src.schemas.category import CategoryRead
from src.models.category import Category

router = APIRouter(tags=["Categories"])

@router.get("/")
async def list_active_categories(
    session: AsyncSession = Depends(get_session)
):
    """List all active marketplace categories for filtering/displaying."""
    stmt = select(Category).where(Category.is_active == True).order_by(Category.display_order)
    result = await session.execute(stmt)
    categories = result.scalars().all()
    return {
        "success": True,
        "data": [CategoryRead.model_validate(c) for c in categories],
        "meta": {"total": len(categories)},
    }
