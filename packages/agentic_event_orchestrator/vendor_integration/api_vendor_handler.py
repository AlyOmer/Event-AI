from typing import List, Dict, Any
from .vendor_portal_client import VendorPortalClient

class ApiVendorHandler:
    def __init__(self, client: VendorPortalClient):
        self.client = client

    def search_vendors(self, query: str, category: str = None, budget: float = None) -> List[Dict[str, Any]]:
        """
        Search for vendors using the API.
        """
        filters = {}
        if category:
            filters['category'] = category
        
        # Get all vendors (or filtered by category if API supports it)
        vendors = self.client.list_vendors(filters=filters)
        
        # Client-side filtering if API doesn't support complex queries
        filtered_vendors = []
        for vendor in vendors:
            # Simple keyword matching if query is provided
            if query and query.lower() not in vendor.get('name', '').lower():
                continue
                
            # Budget filtering would require checking service pricing
            # This is a simplified check
            filtered_vendors.append(vendor)
            
        return filtered_vendors

    def check_availability(self, vendor_id: str, date: str) -> bool:
        """
        Check if a vendor is available on a specific date.
        This would likely require a specific API call.
        For now, we'll assume they are available if the API call succeeds.
        """
        # In a real system, we'd query /availability or similar
        return True

    def get_quote(self, vendor_id: str, service_id: str) -> float:
        """
        Get a price quote.
        """
        pricing = self.client.get_pricing(vendor_id, service_id)
        if pricing:
            return pricing.get('amount', 0.0)
        return 0.0
