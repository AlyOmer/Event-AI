"""EventPlannerAgent — helps users create and manage events."""
from agents import Agent
from pipeline.instructions import EVENT_PLANNER_INSTRUCTIONS
from tools import get_user_events, create_event, get_event_details, update_event_status, query_event_types


def build_event_planner_agent(model, vendor_discovery=None):
    return Agent(
        name="EventPlannerAgent",
        model=model,
        instructions=EVENT_PLANNER_INSTRUCTIONS,
        tools=[get_user_events, create_event, get_event_details, update_event_status, query_event_types],
        handoffs=[vendor_discovery] if vendor_discovery else [],
    )
