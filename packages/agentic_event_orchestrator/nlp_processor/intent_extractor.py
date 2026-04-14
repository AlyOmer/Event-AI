import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .structured_output import EventRequirements

# Load environment variables from .env file
load_dotenv()

class IntentExtractor:
    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")
        genai_client = genai.Client(api_key=api_key)
        self.client = genai_client
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    def extract_event_details(self, user_input: str) -> EventRequirements:
        """
        Extract structured event details from natural language input.
        """
        prompt = f"""
        Extract the following event details from the user's request and return JSON matching this schema:
        {{
            "event_type": "string",
            "attendees": "integer",
            "date": "YYYY-MM-DD",
            "budget": "float",
            "location": "string (optional)",
            "preferences": ["string"]
        }}

        User Input: "{user_input}"
        
        Return ONLY the JSON object.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            # Clean up response to ensure it's valid JSON
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            
            data = json.loads(text)
            return EventRequirements(**data)
        except Exception as e:
            print(f"Error extracting intent: {e}")
            raise e
