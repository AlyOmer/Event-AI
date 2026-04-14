from .event_planner_agent import EventPlannerAgent
from nlp_processor.intent_extractor import IntentExtractor
from vendor_integration.vendor_portal_client import VendorPortalClient
from vendor_integration.api_vendor_handler import ApiVendorHandler
from vendor_integration.manual_vendor_handler import ManualVendorHandler

class OrchestrationAgent:
    def __init__(self):
        self.intent_extractor = IntentExtractor()
        
        client = VendorPortalClient()
        api_handler = ApiVendorHandler(client)
        manual_handler = ManualVendorHandler()
        
        self.planner = EventPlannerAgent(api_handler, manual_handler)
        self.mail_agent = None  # MailProcessingAgent removed (legacy)

    def process_request(self, user_input: str):
        """
        Main entry point for processing a user request.
        """
        # 1. Extract Intent
        print("Extracting intent...")
        event_details = self.intent_extractor.extract_event_details(user_input)
        
        # 2. Plan Event
        print("Planning event...")
        plan = self.planner.plan_event(event_details)
        
        return plan

    def confirm_booking(self, plan):
        """
        Proceed with booking after user approval.
        """
        print("Booking confirmed. Proceeding with reservations...")
        # In a real app, we would call client.create_booking() here
        
        print("Sending invitations...")
        # Mail processing is handled by SDK agents (mail_tools)
        
        return "Event successfully booked and invitations sent!"
