import pytest
from unittest.mock import patch, MagicMock

# Local import assuming agentic_event_orchestrator is in pythonpath, e.g. via pyproject.toml
from tools.booking_tools import create_booking, get_my_bookings, BookingResult

def test_get_my_bookings_success():
    """Verify get_my_bookings hits signed_get without LLMs."""
    with patch("tools.booking_tools.signed_get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "bookings": [
                    {"id": "b1", "vendor": {"name": "Test"}, "eventDate": "2030-01-01", "totalPrice": 500}
                ]
            }
        }
        mock_get.return_value = mock_resp

        results = get_my_bookings("test@example.com")
        
        mock_get.assert_called_once()
        assert len(results) == 1
        assert results[0].booking_id == "b1"
        assert results[0].total_price == 500

@patch("tools.booking_tools._get_session_id", return_value="sess-1")
@patch("tools.booking_tools.is_vendor_in_allowlist", return_value=True)
@patch("tools.booking_tools.is_session_confirmed", return_value=True)
@patch("tools.booking_tools.check_spending_limit", return_value=(True, ""))
@patch("tools.booking_tools.record_booking_spend")
@patch("tools.booking_tools.clear_session_confirmed")
@patch("tools.booking_tools.audit_event")
@patch("tools.booking_tools.signed_post")
def test_create_booking_success(mock_post, mock_audit, mock_clear, mock_record, mock_spend, mock_confirm, mock_allowlist, mock_session):
    """Verify create_booking makes expected backend call."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"data": {"id": "b2"}}
    mock_post.return_value = mock_resp

    result = create_booking(
        vendor_id="v1",
        service_id="s1",
        event_date="2030-01-01",
        client_name="Test",
        client_email="test@test.com",
        estimated_price_pkr=1000
    )

    assert isinstance(result, BookingResult)
    assert result.success is True
    assert result.booking_id == "b2"
    mock_post.assert_called_once()
