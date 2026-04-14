"""EventPlannerAgent — helps users create and manage events."""
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

from agents.instructions import EVENT_PLANNER_INSTRUCTIONS
from tools import get_user_events, create_event, get_event_details, update_event_status, query_event_types


def build_event_planner_agent(model, vendor_discovery=None):
    return Agent(
        name="EventPlannerAgent",
        model=model,
        instructions=EVENT_PLANNER_INSTRUCTIONS,
        tools=[get_user_events, create_event, get_event_details, update_event_status, query_event_types],
        handoffs=[vendor_discovery] if vendor_discovery else [],
    )
