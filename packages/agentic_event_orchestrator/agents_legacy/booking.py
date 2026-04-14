"""BookingAgent — manages booking requests."""
import sys, os as _os
_pkg = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_saved = list(sys.path)
sys.path = [p for p in sys.path if _os.path.abspath(p) != _pkg and p not in ('', '.')]
if 'agents' in sys.modules:
    _local = sys.modules.pop('agents')
else:
    _local = None
from agents import Agent
sys.path = _saved
if _local is not None:
    sys.modules['agents'] = _local

from agents.instructions import BOOKING_INSTRUCTIONS
from tools import create_booking_request, get_my_bookings, get_booking_details, cancel_booking


def build_booking_agent(model):
    return Agent(
        name="BookingAgent",
        model=model,
        instructions=BOOKING_INSTRUCTIONS,
        tools=[create_booking_request, get_my_bookings, get_booking_details, cancel_booking],
    )
