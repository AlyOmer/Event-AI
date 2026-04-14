from typing import List, Dict, Any

class ManualVendorHandler:
    def __init__(self):
        # In a real system, this might load from a local DB or CSV
        self.manual_vendors = [
            {
                "id": "manual_1",
                "name": "Grand Hall (Manual)",
                "category": "venue",
                "description": "A large hall for events.",
                "services": [{"id": "s1", "name": "Hall Rental", "price": 1500}]
            },
            {
                "id": "manual_2",
                "name": "Local Florist (Manual)",
                "category": "florist",
                "description": "Fresh flowers for all occasions.",
                "services": [{"id": "s2", "name": "Basic Decoration", "price": 500}]
            }
        ]

    def search_vendors(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """
        Search manual vendor entries.
        """
        results = []
        for vendor in self.manual_vendors:
            if category and vendor['category'] != category:
                continue
            if query and query.lower() not in vendor['name'].lower():
                continue
            results.append(vendor)
        return results

    def get_vendor_details(self, vendor_id: str) -> Dict[str, Any]:
        for vendor in self.manual_vendors:
            if vendor['id'] == vendor_id:
                return vendor
        return None
