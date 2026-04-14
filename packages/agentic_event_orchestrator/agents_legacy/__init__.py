"""Agents package — builds the full agent pipeline given a model instance.

Usage:
    from agents import build_pipeline
    triage = build_pipeline(model)
"""

from .instructions import (
    TRIAGE_INSTRUCTIONS, EVENT_PLANNER_INSTRUCTIONS,
    VENDOR_DISCOVERY_INSTRUCTIONS, BOOKING_INSTRUCTIONS, ORCHESTRATOR_INSTRUCTIONS,
)
from .event_planner import build_event_planner_agent
from .vendor_discovery import build_vendor_discovery_agent
from .booking import build_booking_agent
from .orchestrator import build_orchestrator_agent
from .triage import build_triage_agent


def build_pipeline(model):
    """Build the full agent pipeline. Returns the TriageAgent as entry point.

    Call this once in the FastAPI lifespan and store on app.state.triage_agent.
    """
    booking = build_booking_agent(model)
    vendor_discovery = build_vendor_discovery_agent(model, booking=booking)
    event_planner = build_event_planner_agent(model, vendor_discovery=vendor_discovery)
    orchestrator = build_orchestrator_agent(model, event_planner, vendor_discovery, booking)
    triage = build_triage_agent(model, event_planner, vendor_discovery, booking, orchestrator)
    return triage


__all__ = [
    "build_pipeline",
    "build_triage_agent",
    "build_event_planner_agent",
    "build_vendor_discovery_agent",
    "build_booking_agent",
    "build_orchestrator_agent",
]
