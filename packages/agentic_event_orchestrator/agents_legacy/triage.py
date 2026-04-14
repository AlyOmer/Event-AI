"""TriageAgent — sole entry point for all user messages."""
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

from agents.instructions import TRIAGE_INSTRUCTIONS


# Agents are imported lazily to avoid circular imports
def build_triage_agent(model, event_planner, vendor_discovery, booking, orchestrator):
    return Agent(
        name="TriageAgent",
        model=model,
        instructions=TRIAGE_INSTRUCTIONS,
        handoffs=[event_planner, vendor_discovery, booking, orchestrator],
    )
