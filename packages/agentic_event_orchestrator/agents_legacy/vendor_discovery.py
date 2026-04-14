"""VendorDiscoveryAgent — searches vendor marketplace."""
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

from agents.instructions import VENDOR_DISCOVERY_INSTRUCTIONS
from tools import search_vendors, get_vendor_details, get_vendor_recommendations


def build_vendor_discovery_agent(model, booking=None):
    return Agent(
        name="VendorDiscoveryAgent",
        model=model,
        instructions=VENDOR_DISCOVERY_INSTRUCTIONS,
        tools=[search_vendors, get_vendor_details, get_vendor_recommendations],
        handoffs=[booking] if booking else [],
    )
