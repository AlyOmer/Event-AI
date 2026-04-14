import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import selectinload

from ..models.vendor import Vendor, VendorStatus
from ..models.category import Category, VendorCategoryLink
from ..models.approval import ApprovalRequest, ApprovalType, ApprovalStatus
from ..models.user import User
from ..schemas.vendor import VendorCreate, VendorUpdate
import structlog

logger = structlog.get_logger()

# Fields that require re-approval when changed
CRITICAL_VENDOR_FIELDS = {"business_name", "contact_email"}


class VendorService:

    @classmethod
    async def _validate_category_ids(
        cls, session: AsyncSession, category_ids: List[uuid.UUID]
    ) -> None:
        """Raise ValueError if any category_id doesn't exist."""
        if not category_ids:
            return
        result = await session.execute(
            select(Category.id).where(Category.id.in_(category_ids))
        )
        found = {row[0] for row in result}
        missing = set(category_ids) - found
        if missing:
            raise ValueError(f"Invalid category IDs: {[str(m) for m in missing]}")

    @classmethod
    async def _set_categories(
        cls, session: AsyncSession, vendor_id: uuid.UUID, category_ids: List[uuid.UUID]
    ) -> None:
        """Replace all category links for a vendor."""
        # Delete existing links
        await session.execute(
            delete(VendorCategoryLink).where(VendorCategoryLink.vendor_id == vendor_id)
        )
        # Insert new links
        for cat_id in category_ids:
            session.add(VendorCategoryLink(vendor_id=vendor_id, category_id=cat_id))

    @classmethod
    async def create_vendor(
        cls, session: AsyncSession, user: User, vendor_in: VendorCreate
    ) -> Vendor:
        # Check user doesn't already have a vendor profile
        existing_for_user = await session.execute(
            select(Vendor).where(Vendor.user_id == user.id)
        )
        if existing_for_user.scalar_one_or_none():
            raise ValueError("CONFLICT_VENDOR_EXISTS")

        # Check for duplicate business name + location
        existing = await cls._check_duplicate_vendor(
            session, vendor_in.business_name, vendor_in.city, vendor_in.region
        )
        if existing:
            raise ValueError("CONFLICT_DUPLICATE_VENDOR")

        # Validate categories before touching DB
        await cls._validate_category_ids(session, vendor_in.category_ids)

        create_data = vendor_in.model_dump(exclude={"category_ids"})
        new_vendor = Vendor(**create_data, user_id=user.id, status=VendorStatus.PENDING)
        session.add(new_vendor)
        await session.flush()  # get vendor.id

        # Assign categories
        await cls._set_categories(session, new_vendor.id, vendor_in.category_ids)

        # Create approval request
        approval = ApprovalRequest(
            vendor_id=new_vendor.id,
            type=ApprovalType.NEW_REGISTRATION,
            status=ApprovalStatus.PENDING,
            data_snapshot=vendor_in.model_dump(mode="json"),
        )
        session.add(approval)

        await session.commit()

        # Reload with categories
        result = await session.execute(
            select(Vendor)
            .where(Vendor.id == new_vendor.id)
            .options(selectinload(Vendor.categories))
        )
        vendor = result.scalar_one()

        logger.info(
            "vendor.created",
            vendor_id=str(vendor.id),
            user_id=str(user.id),
            approval_id=str(approval.id),
        )
        return vendor

    @classmethod
    async def _check_duplicate_vendor(
        cls,
        session: AsyncSession,
        business_name: str,
        city: Optional[str],
        region: Optional[str],
    ) -> Optional[Vendor]:
        stmt = select(Vendor).where(
            and_(
                func.lower(Vendor.business_name) == func.lower(business_name),
                Vendor.status != VendorStatus.REJECTED,
            )
        )
        if city:
            stmt = stmt.where(func.lower(Vendor.city) == func.lower(city))
        if region:
            stmt = stmt.where(func.lower(Vendor.region) == func.lower(region))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    def _detect_critical_changes(cls, original: Vendor, update_data: dict) -> bool:
        for field in CRITICAL_VENDOR_FIELDS:
            if field in update_data and getattr(original, field) != update_data[field]:
                return True
        return False

    @classmethod
    async def get_by_id(
        cls, session: AsyncSession, vendor_id: uuid.UUID
    ) -> Optional[Vendor]:
        result = await session.execute(
            select(Vendor)
            .where(Vendor.id == vendor_id)
            .options(selectinload(Vendor.categories))
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_user_id(
        cls, session: AsyncSession, user_id: uuid.UUID
    ) -> Optional[Vendor]:
        result = await session.execute(
            select(Vendor)
            .where(Vendor.user_id == user_id)
            .options(selectinload(Vendor.categories))
        )
        return result.scalar_one_or_none()

    @classmethod
    async def update_vendor(
        cls, session: AsyncSession, vendor: Vendor, vendor_in: VendorUpdate
    ) -> Vendor:
        update_data = vendor_in.model_dump(exclude_unset=True)
        category_ids = update_data.pop("category_ids", None)

        # Validate categories if provided
        if category_ids is not None:
            await cls._validate_category_ids(session, category_ids)

        # Check if critical fields changed
        needs_approval = cls._detect_critical_changes(vendor, update_data)

        if needs_approval:
            approval = ApprovalRequest(
                vendor_id=vendor.id,
                type=ApprovalType.PROFILE_EDIT,
                status=ApprovalStatus.PENDING,
                data_snapshot={
                    "previous": {k: str(getattr(vendor, k)) for k in update_data},
                    "proposed": {k: str(v) for k, v in update_data.items()},
                },
            )
            session.add(approval)
            vendor.status = VendorStatus.PENDING
            logger.info(
                "vendor.update_pending_approval",
                vendor_id=str(vendor.id),
                approval_id=str(approval.id),
            )

        # Apply field updates
        for field, value in update_data.items():
            setattr(vendor, field, value)

        # Update categories if provided
        if category_ids is not None:
            await cls._set_categories(session, vendor.id, category_ids)

        await session.commit()

        # Reload with categories
        result = await session.execute(
            select(Vendor)
            .where(Vendor.id == vendor.id)
            .options(selectinload(Vendor.categories))
        )
        vendor = result.scalar_one()

        logger.info("vendor.updated", vendor_id=str(vendor.id))
        return vendor


vendor_service = VendorService()
