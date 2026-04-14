from typing import List, Dict, Any
from nlp_processor.structured_output import EventRequirements, VendorSelection

class Optimizer:
    def __init__(self):
        pass

    def optimize_schedule(self, event_details: EventRequirements, available_vendors: List[Dict[str, Any]]) -> List[VendorSelection]:
        """
        Select the best vendors based on budget and preferences.
        This is a simplified greedy approach.
        """
        selected_vendors = []
        remaining_budget = event_details.budget

        # Group vendors by category
        vendors_by_category = {}
        for vendor in available_vendors:
            cat = vendor.get('category', 'other')
            if cat not in vendors_by_category:
                vendors_by_category[cat] = []
            vendors_by_category[cat].append(vendor)

        # For each required category (derived from preferences or defaults), pick best
        required_categories = ['venue', 'catering'] # Simplified defaults

        for category in required_categories:
            candidates = vendors_by_category.get(category, [])
            if not candidates:
                continue

            best_vendor_selection = None
            best_score = -1

            for vendor in candidates:
                if not vendor.get('services'):
                    continue

                for service in vendor['services']:
                    price = service.get('price', 0.0)
                    if price > remaining_budget:
                        continue

                    rating = vendor.get('rating', 3.0)
                    score = rating / price if price > 0 else 0

                    if score > best_score:
                        best_score = score
                        best_vendor_selection = VendorSelection(
                            vendor_id=vendor['id'],
                            service_id=service['id'],
                            cost=price,
                            reason=f"Best value for {category}"
                        )

            if best_vendor_selection:
                selected_vendors.append(best_vendor_selection)
                remaining_budget -= best_vendor_selection.cost

        return selected_vendors
