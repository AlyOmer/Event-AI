import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from fastapi import HTTPException

from ..models.approval import ApprovalRequest, ApprovalStatus, ApprovalType
from ..models.vendor import Vendor, VendorStatus
from ..schemas.approval import ApprovalRequestUpdate
import structlog

logger = structlog.get_logger()


class ApprovalService:

    @classmethod
    async def list_pending_approvals(
        cls, session: AsyncSession, limit: int = 20, offset: int = 0
    ) -> List[ApprovalRequest]:
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.status == ApprovalStatus.PENDING)
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_approval(
        cls, session: AsyncSession, approval_id: uuid.UUID
    ) -> Optional[ApprovalRequest]:
        return await session.get(ApprovalRequest, approval_id)

    @classmethod
    async def process_approval(
        cls,
        session: AsyncSession,
        approval: ApprovalRequest,
        admin_id: uuid.UUID,
        data_in: ApprovalRequestUpdate,
    ) -> ApprovalRequest:
        # Update approval record
        approval.status = data_in.status
        approval.decision_notes = data_in.decision_notes
        approval.reviewed_by = admin_id
        approval.reviewed_date = datetime.now(timezone.utc)

        # Update vendor status BEFORE commit
        vendor = await session.get(Vendor, approval.vendor_id)
        if vendor:
            if data_in.status == ApprovalStatus.APPROVED:
                vendor.status = VendorStatus.ACTIVE
            elif data_in.status == ApprovalStatus.REJECTED:
                vendor.status = VendorStatus.REJECTED
        else:
            logger.warning(
                "approval.vendor_not_found",
                approval_id=str(approval.id),
                vendor_id=str(approval.vendor_id),
            )

        await session.commit()
        await session.refresh(approval)

        logger.info(
            "approval.processed",
            approval_id=str(approval.id),
            status=data_in.status.value,
            admin_id=str(admin_id),
            vendor_id=str(approval.vendor_id),
        )

        # Emit domain events AFTER commit (fire-and-forget via background task)
        # Using a fresh emit that doesn't depend on the now-committed session
        if vendor:
            from ..services.event_bus_service import event_bus
            try:
                if data_in.status == ApprovalStatus.APPROVED:
                    await event_bus.emit(
                        session,
                        "vendor.approved",
                        {
                            "vendor_id": str(vendor.id),
                            "business_name": vendor.business_name,
                            "approved_by": str(admin_id),
                        },
                    )
                elif data_in.status == ApprovalStatus.REJECTED:
                    await event_bus.emit(
                        session,
                        "vendor.rejected",
                        {
                            "vendor_id": str(vendor.id),
                            "business_name": vendor.business_name,
                            "rejected_by": str(admin_id),
                            "reason": data_in.decision_notes or "No reason provided",
                        },
                    )
            except Exception as e:
                logger.error("approval.event_emit_failed", error=str(e))

        return approval


approval_service = ApprovalService()
