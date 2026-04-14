from typing import Dict, Any, List
from vendor_integration.api_vendor_handler import ApiVendorHandler
from vendor_integration.manual_vendor_handler import ManualVendorHandler
from scheduler.optimizer import Optimizer
from nlp_processor.structured_output import EventRequirements, EventPlan, VendorSelection

# Try to import VendorDiscoveryAgent
try:
    from .vendor_discovery_agent import VendorDiscoveryAgent
    VENDOR_DISCOVERY_AVAILABLE = True
except ImportError:
    VENDOR_DISCOVERY_AVAILABLE = False
    print("VendorDiscoveryAgent not available. Using basic search only.")


class EventPlannerAgent:
    def __init__(self, api_handler: ApiVendorHandler, manual_handler: ManualVendorHandler):
        self.api_handler = api_handler
        self.manual_handler = manual_handler
        self.optimizer = Optimizer()
        
        # Initialize vendor discovery
        self.discovery_agent = None
        if VENDOR_DISCOVERY_AVAILABLE:
            try:
                self.discovery_agent = VendorDiscoveryAgent()
            except Exception as e:
                print(f"Could not initialize VendorDiscoveryAgent: {e}")

    def plan_event(self, event_details: EventRequirements) -> EventPlan:
        """
        Orchestrate the planning process: search vendors, optimize, and create a plan.
        """
        print(f"Planning event: {event_details.event_type} for {event_details.attendees} people.")
        print(f"Budget: PKR {event_details.budget:,.0f}, Location: {event_details.location}")
        
        vendors: List[VendorSelection] = []
        
        # 1. Use VendorDiscoveryAgent (keyword + scoring)
        if self.discovery_agent:
            print("Searching vendors...")
            vendor_results = self.discovery_agent.search_vendors(event_details, top_k=5)
            vendors.extend(vendor_results)
        
        # 2. Fallback to API and Manual handlers
        if len(vendors) < 3:
            print("Supplementing with API/manual vendor search...")
            api_vendors = self.api_handler.search_vendors(query=event_details.event_type)
            manual_vendors = self.manual_handler.search_vendors(query=event_details.event_type)
            vendors.extend(api_vendors)
            vendors.extend(manual_vendors)
        
        # 3. Optimize Schedule
        selected_vendors = self.optimizer.optimize_schedule(event_details, vendors) if vendors else []
        
        # 4. Calculate Total Cost (PKR)
        total_cost = sum([v.cost for v in selected_vendors]) if selected_vendors else 0.0
        
        # 5. Create Plan
        plan = EventPlan(
            event_details=event_details,
            selected_vendors=selected_vendors,
            total_cost=total_cost,
            schedule=[
                "10:00 AM - Venue Setup",
                "12:00 PM - Event Start", 
                "4:00 PM - Event End",
                "5:00 PM - Cleanup"
            ]
        )
        
        print(f"Plan created with {len(selected_vendors)} vendors, total cost: PKR {total_cost:,.0f}")
        
        return plan

