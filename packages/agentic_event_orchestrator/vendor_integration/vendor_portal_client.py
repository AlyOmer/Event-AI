import requests
import os
from typing import List, Dict, Optional, Any

class VendorPortalClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("VENDOR_PORTAL_API_URL", "http://localhost:3000/api/v1")
        self.api_key = api_key or os.getenv("VENDOR_PORTAL_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

    def list_vendors(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Fetch list of vendors from the portal.
        Assumes GET /vendors endpoint exists as per requirements.
        """
        url = f"{self.base_url}/vendors"
        try:
            response = requests.get(url, params=filters, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching vendors: {e}")
            return []

    def get_vendor_details(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch public details for a specific vendor.
        Matches GET /vendors/:id/public
        """
        url = f"{self.base_url}/vendors/{vendor_id}/public"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching vendor details for {vendor_id}: {e}")
            return None

    def get_vendor_services(self, vendor_id: str) -> List[Dict[str, Any]]:
        """
        Fetch services for a specific vendor.
        """
        details = self.get_vendor_details(vendor_id)
        if details and 'services' in details:
            return details['services']
        return []

    def create_booking(self, booking_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a booking.
        Assumes POST /bookings endpoint exists as per requirements.
        """
        url = f"{self.base_url}/bookings"
        try:
            response = requests.post(url, json=booking_data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating booking: {e}")
            return None

    def get_pricing(self, vendor_id: str, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pricing for a specific service.
        Assumes GET /pricing endpoint or similar.
        """
        # This might be part of the service details or a separate endpoint
        # The prompt says GET /pricing
        url = f"{self.base_url}/pricing"
        params = {"vendor_id": vendor_id, "service_id": service_id}
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching pricing: {e}")
            return None
