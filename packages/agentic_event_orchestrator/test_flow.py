import sys
import os
from unittest.mock import MagicMock

# Mock Gemini to avoid API keys requirement for testing
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nlp_processor.structured_output import EventRequirements
from agents.orchestration_agent import OrchestrationAgent

def test_flow():
    print("Starting test flow...")
    
    # Initialize agent
    agent = OrchestrationAgent()
    
    # Mock the IntentExtractor instance on the agent
    # We need to mock the model.generate_content method
    
    # Re-import to get the real class
    from nlp_processor.intent_extractor import IntentExtractor
    extractor = IntentExtractor()
    # Create mock client with models.generate_content method
    mock_client = MagicMock()
    mock_models = MagicMock()
    mock_client.models = mock_models
    extractor.client = mock_client
    
    # Mock the generate_content response
    mock_response = MagicMock()
    mock_response.text = """
    {
        "event_type": "wedding",
        "attendees": 200,
        "date": "2025-03-15",
        "budget": 10000.0,
        "location": "Lahore",
        "preferences": ["outdoor"]
    }
    """
    mock_models.generate_content.return_value = mock_response
    
    agent.intent_extractor = extractor
    
    # Simulate user input
    user_input = "I need a wedding for 200 people in Lahore on March 15, 2025, budget $10k."
    print(f"User Input: {user_input}")
    
    # Run process
    plan = agent.process_request(user_input)
    
    print("\nGenerated Plan:")
    print(f"Type: {plan.event_details.event_type}")
    print(f"Cost: ${plan.total_cost}")
    print(f"Vendors: {len(plan.selected_vendors)}")
    
    # Confirm booking
    result = agent.confirm_booking(plan)
    print(f"\nResult: {result}")

if __name__ == "__main__":
    test_flow()
