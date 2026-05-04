"""
VendorAvailabilityService — manages vendor availability slots with upsert semantics.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from ..models.availability import VendorAvailability
from ..schemas.vendor_availability import AvailabilityUpsert

logger = structlog.get_logger()


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


class VendorAvailabilityService:

    async def list_availability(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        start_date: date,
        end_date: date,
        service_id: Optional[uuid.UUID] = None,
    ) -> List[VendorAvailability]:
        """Return all availability records for a vendor within an inclusive date range."""
        stmt = (
            select(VendorAvailability)
            .where(
                VendorAvailability.vendor_id == vendor_id,
                VendorAvailability.date >= start_date,
                VendorAvailability.date <= end_date,
            )
            .order_by(VendorAvailability.date)
        )
        if service_id is not None:
            stmt = stmt.where(VendorAvailability.service_id == service_id)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_availability(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        entry: AvailabilityUpsert,
    ) -> VendorAvailability:
        """
        Insert or update a single availability slot.
        Raises 422 if the date is in the past or status is 'booked'.

        Uses SELECT + INSERT/UPDATE instead of INSERT ... ON CONFLICT to handle
        NULL service_id correctly (NULL != NULL in unique indexes on all DBs).
        """
        self._validate_entry(entry)

        now = datetime.now(timezone.utc)

        # Look up existing record first (handles NULL service_id correctly)
        stmt = select(VendorAvailability).where(
            VendorAvailability.vendor_id == vendor_id,
            VendorAvailability.date == entry.date,
            VendorAvailability.service_id == entry.service_id
            if entry.service_id is not None
            else VendorAvailability.service_id.is_(None),
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            # Update in place
            existing.status = entry.status
            existing.notes = entry.notes
            existing.updated_at = now
            await session.commit()
            await session.refresh(existing)
            row = existing
        else:
            # Insert new record
            row = VendorAvailability(
                vendor_id=vendor_id,
                service_id=entry.service_id,
                date=entry.date,
                status=entry.status,
                notes=entry.notes,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)

        logger.info(
            "vendor.availability.upserted",
            vendor_id=str(vendor_id),
            date=str(entry.date),
            status=entry.status,
        )
        return row

    async def bulk_upsert_availability(
        self,
        session: AsyncSession,
        vendor_id: uuid.UUID,
        entries: List[AvailabilityUpsert],
    ) -> List[VendorAvailability]:
        """
        Upsert multiple availability slots in a single transaction.
        All entries are validated first; any failure rolls back the entire batch.
        """
        for entry in entries:
            self._validate_entry(entry)

        now = datetime.now(timezone.utc)
        results: List[VendorAvailability] = []

        for entry in entries:
            stmt = select(VendorAvailability).where(
                VendorAvailability.vendor_id == vendor_id,
                VendorAvailability.date == entry.date,
                VendorAvailability.service_id == entry.service_id
                if entry.service_id is not None
                else VendorAvailability.service_id.is_(None),
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is not None:
                existing.status = entry.status
                existing.notes = entry.notes
                existing.updated_at = now
                results.append(existing)
            else:
                row = VendorAvailability(
                    vendor_id=vendor_id,
                    service_id=entry.service_id,
                    date=entry.date,
                    status=entry.status,
                    notes=entry.notes,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                results.append(row)

        await session.commit()
        for row in results:
            await session.refresh(row)

        logger.info(
            "vendor.availability.bulk_upserted",
            vendor_id=str(vendor_id),
            count=len(results),
        )
        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_entry(entry: AvailabilityUpsert) -> None:
        """Raise HTTPException 422 for invalid entries."""
        today = datetime.now(timezone.utc).date()
        if entry.date < today:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err("VALIDATION_PAST_DATE", "Availability date cannot be in the past."),
            )
        # Guard against 'booked' being passed despite the Literal type (belt-and-suspenders)
        if entry.status == "booked":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_err(
                    "VALIDATION_INVALID_STATUS",
                    "Status 'booked' cannot be set manually; it is managed by the booking system.",
                ),
            )


vendor_availability_service = VendorAvailabilityService()
