"""
Vendor Discovery Agent - Simplified

Simple vendor matching using keyword search and scoring.
Connects to PostgreSQL for real vendor data, falls back to samples.
"""

from typing import List, Dict, Any
from pydantic import BaseModel
from nlp_processor.structured_output import EventRequirements, VendorSelection

# Try to import database repository
try:
    from database import get_vendor_repository, VendorRecord
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Database module not available. Using sample data.")


class VendorProfile(BaseModel):
    """Vendor profile"""
    vendor_id: str
    business_name: str
    category: str
    description: str
    service_areas: List[str]
    pricing_min: float  # PKR
    pricing_max: float  # PKR
    rating: float = 0.0
    total_reviews: int = 0
    is_available: bool = True
    keywords: List[str] = []


# Sample Pakistani vendors (fallback)
SAMPLE_VENDORS = [
    VendorProfile(
        vendor_id="catering_001", business_name="Lahore Catering Excellence", category="catering",
        description="Premium Pakistani cuisine for weddings and events",
        service_areas=["Lahore", "Islamabad"], pricing_min=50000, pricing_max=500000,
        rating=4.5, total_reviews=120,
        keywords=["wedding", "mehndi", "walima", "catering", "food", "traditional"]
    ),
    VendorProfile(
        vendor_id="venue_001", business_name="Royal Marquee Lahore", category="venue",
        description="Luxury wedding venue with lawns and marquees",
        service_areas=["Lahore"], pricing_min=200000, pricing_max=800000,
        rating=4.8, total_reviews=85,
        keywords=["wedding", "venue", "marquee", "hall", "lawn", "mehndi", "baraat"]
    ),
    VendorProfile(
        vendor_id="photo_001", business_name="Moments Photography", category="photography",
        description="Wedding photography and videography",
        service_areas=["Lahore", "Islamabad", "Karachi"], pricing_min=100000, pricing_max=400000,
        rating=4.7, total_reviews=200,
        keywords=["photography", "video", "drone", "wedding", "photo", "album"]
    ),
    VendorProfile(
        vendor_id="decor_001", business_name="Floral Dreams Decoration", category="decoration",
        description="Event decoration and floral arrangements",
        service_areas=["Lahore", "Islamabad"], pricing_min=80000, pricing_max=350000,
        rating=4.6, total_reviews=95,
        keywords=["decoration", "flowers", "decor", "wedding", "theme", "stage"]
    ),
    VendorProfile(
        vendor_id="music_001", business_name="Beat Masters DJ", category="music",
        description="DJ services and live band entertainment",
        service_areas=["Lahore", "Karachi", "Islamabad"], pricing_min=40000, pricing_max=150000,
        rating=4.4, total_reviews=150,
        keywords=["dj", "music", "band", "entertainment", "sound", "party"]
    ),
    VendorProfile(
        vendor_id="catering_002", business_name="Karachi BBQ House", category="catering",
        description="BBQ and street food catering for casual events",
        service_areas=["Karachi"], pricing_min=25000, pricing_max=200000,
        rating=4.3, total_reviews=75,
        keywords=["bbq", "catering", "party", "birthday", "casual", "outdoor"]
    ),
]


class VendorDiscoveryAgent:
    """
    Vendor discovery using keyword matching and scoring.
    Connects to PostgreSQL for real data, falls back to samples.
    """
    
    def __init__(self, use_database: bool = True):
        self.use_database = use_database and DB_AVAILABLE
        self.vendor_repo = get_vendor_repository() if self.use_database else None
        
        if self.use_database:
            print("VendorDiscoveryAgent initialized with PostgreSQL")
        else:
            print(f"VendorDiscoveryAgent initialized with {len(SAMPLE_VENDORS)} sample vendors")
    
    def search_vendors(
        self,
        event_requirements: EventRequirements,
        top_k: int = 5
    ) -> List[VendorSelection]:
        """
        Search vendors matching event requirements.
        Uses PostgreSQL if available, falls back to sample data.
        """
        print(f"Searching vendors for: {event_requirements.event_type} in {event_requirements.location}")
        
        # Get vendors from DB or use samples
        if self.use_database and self.vendor_repo:
            try:
                db_vendors = self.vendor_repo.search_vendors(
                    event_type=event_requirements.event_type,
                    location=event_requirements.location,
                    budget=event_requirements.budget,
                    limit=top_k * 2
                )
                vendors = [self._record_to_profile(v) for v in db_vendors]
                if not vendors:
                    vendors = SAMPLE_VENDORS
            except Exception as e:
                print(f"Database search failed: {e}, using samples")
                vendors = SAMPLE_VENDORS
        else:
            vendors = SAMPLE_VENDORS
        
        # Build search keywords from requirements
        search_keywords = self._extract_keywords(event_requirements)
        
        # Score all vendors
        scored_vendors = []
        for vendor in vendors:
            if not self._matches_filters(vendor, event_requirements):
                continue
            score = self._calculate_score(vendor, event_requirements, search_keywords)
            scored_vendors.append((vendor, score))
        
        # Sort by score descending
        scored_vendors.sort(key=lambda x: x[1], reverse=True)
        
        # Convert to VendorSelection
        results = []
        for vendor, score in scored_vendors[:top_k]:
            avg_price = (vendor.pricing_min + vendor.pricing_max) / 2
            results.append(VendorSelection(
                vendor_id=vendor.vendor_id,
                service_id=f"{vendor.category}_default",
                cost=avg_price,
                reason=f"{score:.0%} match - {vendor.business_name}"
            ))
        
        print(f"Found {len(results)} matching vendors")
        return results
    
    def _record_to_profile(self, record) -> VendorProfile:
        """Convert database VendorRecord to VendorProfile"""
        return VendorProfile(
            vendor_id=record.id,
            business_name=record.name,
            category=record.category,
            description=record.description,
            service_areas=record.service_areas,
            pricing_min=record.pricing_min,
            pricing_max=record.pricing_max,
            rating=record.rating,
            total_reviews=record.total_reviews,
            keywords=record.keywords,
            is_available=record.status == "ACTIVE"
        )
    
    def _extract_keywords(self, requirements: EventRequirements) -> List[str]:
        """Extract search keywords from requirements"""
        keywords = [requirements.event_type.lower()]
        
        # Add preferences as keywords
        keywords.extend([p.lower() for p in requirements.preferences])
        
        # Add common category mappings
        event_type = requirements.event_type.lower()
        if "wedding" in event_type:
            keywords.extend(["mehndi", "baraat", "walima", "venue", "catering", "photography"])
        elif "birthday" in event_type:
            keywords.extend(["party", "cake", "decoration", "entertainment"])
        elif "corporate" in event_type:
            keywords.extend(["conference", "meeting", "venue", "catering"])
        
        return list(set(keywords))
    
    def _matches_filters(self, vendor: VendorProfile, requirements: EventRequirements) -> bool:
        """Apply hard filters"""
        # Availability
        if not vendor.is_available:
            return False
        
        # Budget filter
        if requirements.budget and vendor.pricing_min > requirements.budget:
            return False
        
        # Location filter
        if requirements.location:
            location_lower = requirements.location.lower()
            areas_lower = [a.lower() for a in vendor.service_areas]
            if location_lower not in areas_lower and "all" not in areas_lower:
                return False
        
        return True
    
    def _calculate_score(
        self,
        vendor: VendorProfile,
        requirements: EventRequirements,
        search_keywords: List[str]
    ) -> float:
        """
        Calculate vendor score (0-1) based on:
        - Keyword matches (40%)
        - Rating (30%)
        - Price fit (20%)
        - Availability (10%)
        """
        # Keyword match score
        vendor_keywords = [k.lower() for k in vendor.keywords]
        vendor_text = f"{vendor.description} {vendor.category} {vendor.business_name}".lower()
        
        matches = 0
        for keyword in search_keywords:
            if keyword in vendor_keywords or keyword in vendor_text:
                matches += 1
        
        keyword_score = min(1.0, matches / max(len(search_keywords), 1)) * 0.4
        
        # Rating score
        rating_score = (vendor.rating / 5.0) * 0.3
        
        # Price fit score
        avg_price = (vendor.pricing_min + vendor.pricing_max) / 2
        if requirements.budget:
            if avg_price <= requirements.budget:
                price_score = 0.2
            else:
                # Penalize over-budget
                price_score = max(0, 0.2 * (1 - (avg_price - requirements.budget) / requirements.budget))
        else:
            price_score = 0.1
        
        # Availability bonus
        availability_score = 0.1 if vendor.is_available else 0
        
        return keyword_score + rating_score + price_score + availability_score


# Quick test
if __name__ == "__main__":
    agent = VendorDiscoveryAgent()
    
    requirements = EventRequirements(
        event_type="wedding",
        attendees=200,
        date="2026-03-15",
        budget=500000,
        location="Lahore",
        preferences=["traditional", "mehndi"]
    )
    
    results = agent.search_vendors(requirements, top_k=5)
    
    print("\n=== Vendor Search Results ===")
    for r in results:
        print(f"- {r.vendor_id}: PKR {r.cost:,.0f} - {r.reason}")


