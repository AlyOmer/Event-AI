import asyncio
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from agents.event_planner_agent import EventPlannerAgent
from nlp_processor.structured_output import EventRequirements
from vendor_integration.api_vendor_handler import ApiVendorHandler
from vendor_integration.manual_vendor_handler import ManualVendorHandler
from vendor_integration.vendor_portal_client import VendorPortalClient

# Initialize the MCP server
mcp = FastMCP("Event Planner Agent")

# Initialize handlers and agent
client = VendorPortalClient(base_url="http://localhost:3000/api/v1")
api_handler = ApiVendorHandler(client)
manual_handler = ManualVendorHandler()
agent = EventPlannerAgent(api_handler, manual_handler)

@mcp.tool()
def plan_event(event_type: str, location: str, budget: float, attendees: int, date: str, preferences: list[str] = None) -> dict:
    """
    Plan an event by finding vendors and optimizing the schedule.
    Returns a complete event plan with selected vendors and costs.
    """
    reqs = EventRequirements(
        event_type=event_type,
        location=location,
        budget=budget,
        preferences=preferences or [],
        attendees=attendees,
        date=date
    )
    plan = agent.plan_event(reqs)
    return {
        "event_type": plan.event_details.event_type,
        "total_cost": plan.total_cost,
        "vendors": [v.name for v in plan.selected_vendors] if plan.selected_vendors else [],
        "schedule": plan.schedule
    }

@mcp.tool()
def search_vendors(query: str) -> list[dict]:
    """
    Search for vendors matching a query.
    """
    vendors = agent.api_handler.search_vendors(query)
    vendors.extend(agent.manual_handler.search_vendors(query))
    return [{"id": v.id, "name": v.name, "category": v.category} for v in vendors]

if __name__ == "__main__":
    mcp.run()
