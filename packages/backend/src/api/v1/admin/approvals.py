import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.config.database import get_session
from src.models.user import User
from src.models.vendor import Vendor
from src.models.approval import ApprovalRequest
from src.schemas.approval import ApprovalRequestRead, ApprovalRequestUpdate
from src.services.approval_service import approval_service

router = APIRouter(tags=["Admin Approvals"])

# TODO: Add role-based access control inside the endpoint or via dependency 
# e.g., current_admin: User = Depends(get_current_admin)

@router.get("/", response_model=List[ApprovalRequestRead])
async def list_pending_approvals(
    limit: int = 20, 
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Admin-only: List all pending approval requests."""
    # Ensure current_user is admin
    if current_user.role != "admin": # Replace with your actual user role check
        raise HTTPException(status_code=403, detail="Requires administrator privileges")
        
    return await approval_service.list_pending_approvals(session, limit, offset)

@router.post("/{approval_id}/process", response_model=ApprovalRequestRead)
async def process_approval(
    approval_id: uuid.UUID,
    decision_data: ApprovalRequestUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Admin-only: Approve, Reject or request more info on a vendor application."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Requires administrator privileges")
        
    approval = await approval_service.get_approval(session, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
        
    return await approval_service.process_approval(
        session, approval, current_user.id, decision_data
    )
