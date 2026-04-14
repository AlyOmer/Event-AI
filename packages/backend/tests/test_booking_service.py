import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, time
from fastapi import HTTPException

from src.models.booking import Booking, BookingStatus, BookingCreate
from src.models.availability import VendorAvailability, AvailabilityStatus
from src.services.booking_service import BookingService, VALID_TRANSITIONS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_booking_in(vendor_id=None, service_id=None):
    return BookingCreate(
        vendor_id=vendor_id or uuid.uuid4(),
        service_id=service_id or uuid.uuid4(),
        event_date=date(2027, 6, 1),
        unit_price=500.0,
        total_price=500.0,
    )


def _mock_vendor(vendor_id=None, user_id=None):
    v = MagicMock()
    v.id = vendor_id or uuid.uuid4()
    v.user_id = user_id or uuid.uuid4()
    return v


def _mock_service(vendor_id, service_id=None, is_active=True, price_min=500.0):
    s = MagicMock()
    s.id = service_id or uuid.uuid4()
    s.vendor_id = vendor_id
    s.is_active = is_active
    s.price_min = price_min
    return s


# ── create_booking ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_booking_past_date_raises_422():
    service = BookingService()
    session = AsyncMock()
    booking_in = BookingCreate(
        vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        event_date=date(2020, 1, 1), unit_price=100.0, total_price=100.0,
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_booking(session, booking_in, uuid.uuid4())
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "VALIDATION_PAST_DATE"


@pytest.mark.asyncio
async def test_create_booking_vendor_not_found_raises_404():
    service = BookingService()
    session = AsyncMock()
    session.get.return_value = None  # vendor not found
    booking_in = _make_booking_in()
    with pytest.raises(HTTPException) as exc:
        await service.create_booking(session, booking_in, uuid.uuid4())
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NOT_FOUND_VENDOR"


@pytest.mark.asyncio
async def test_create_booking_inactive_service_raises_422():
    service = BookingService()
    session = AsyncMock()
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    booking_in = _make_booking_in(vendor_id=vendor_id, service_id=service_id)
    # session.get: first call = vendor, second call = service (inactive)
    session.get.side_effect = [_mock_vendor(vendor_id), _mock_service(vendor_id, service_id, is_active=False)]
    with pytest.raises(HTTPException) as exc:
        await service.create_booking(session, booking_in, uuid.uuid4())
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "VALIDATION_SERVICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_booking_date_already_booked_raises_409():
    service = BookingService()
    session = AsyncMock()
    vendor_id = uuid.uuid4()
    service_id = uuid.uuid4()
    booking_in = _make_booking_in(vendor_id=vendor_id, service_id=service_id)
    session.get.side_effect = [_mock_vendor(vendor_id), _mock_service(vendor_id, service_id)]
    # availability row = BOOKED
    booked_row = VendorAvailability(
        vendor_id=vendor_id, service_id=service_id,
        date=booking_in.event_date, status=AvailabilityStatus.BOOKED,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = booked_row
    session.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc:
        await service.create_booking(session, booking_in, uuid.uuid4())
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_DATE_UNAVAILABLE"


# ── update_status state machine ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_status_invalid_transition_raises_409():
    service = BookingService()
    session = AsyncMock()
    booking = Booking(
        id=uuid.uuid4(), vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.pending, unit_price=100.0, total_price=100.0,
    )
    session.get.return_value = booking
    with pytest.raises(HTTPException) as exc:
        await service.update_status(session, booking.id, BookingStatus.completed, uuid.uuid4())
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "VALIDATION_INVALID_TRANSITION"


@pytest.mark.asyncio
async def test_update_status_terminal_raises_409():
    service = BookingService()
    session = AsyncMock()
    booking = Booking(
        id=uuid.uuid4(), vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.completed, unit_price=100.0, total_price=100.0,
    )
    session.get.return_value = booking
    with pytest.raises(HTTPException) as exc:
        await service.update_status(session, booking.id, BookingStatus.confirmed, uuid.uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_cancel_already_cancelled_raises_409():
    service = BookingService()
    session = AsyncMock()
    booking = Booking(
        id=uuid.uuid4(), vendor_id=uuid.uuid4(), service_id=uuid.uuid4(),
        user_id=uuid.uuid4(), event_date=date(2027, 6, 1),
        status=BookingStatus.cancelled, unit_price=100.0, total_price=100.0,
    )
    session.get.return_value = booking
    with pytest.raises(HTTPException) as exc:
        await service.cancel_booking(session, booking.id, uuid.uuid4())
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "CONFLICT_ALREADY_CANCELLED"


# ── state machine coverage ────────────────────────────────────────────────────

def test_valid_transitions_defined():
    assert BookingStatus.confirmed in VALID_TRANSITIONS[BookingStatus.pending]
    assert BookingStatus.rejected in VALID_TRANSITIONS[BookingStatus.pending]
    assert BookingStatus.cancelled in VALID_TRANSITIONS[BookingStatus.pending]
    assert BookingStatus.in_progress in VALID_TRANSITIONS[BookingStatus.confirmed]
    assert BookingStatus.completed in VALID_TRANSITIONS[BookingStatus.in_progress]
