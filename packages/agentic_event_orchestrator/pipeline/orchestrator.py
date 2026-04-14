"""OrchestratorAgent — coordinates multi-step flows."""
from agents import Agent
from pipeline.instructions import ORCHESTRATOR_INSTRUCTIONS


def build_orchestrator_agent(model, event_planner, vendor_discovery, booking):
    return Agent(
        name="OrchestratorAgent",
        model=model,
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        handoffs=[event_planner, vendor_discovery, booking],
    )
