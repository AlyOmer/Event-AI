#!/usr/bin/env python3
"""
Test script for the Vendor Discovery Agent with ChromaDB.
Run: python test_vendor_discovery.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nlp_processor.structured_output import EventRequirements

def test_vendor_discovery():
    """Test the VendorDiscoveryAgent with ChromaDB"""
    
    print("=" * 60)
    print("Testing Vendor Discovery Agent with ChromaDB")
    print("=" * 60)
    
    try:
        from agents.vendor_discovery_agent import VendorDiscoveryAgent, VendorProfile
        print("✅ Successfully imported VendorDiscoveryAgent")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("\nPlease install dependencies:")
        print("  pip install chromadb sentence-transformers")
        return False
    
    # Initialize agent
    print("\n1. Initializing VendorDiscoveryAgent...")
    agent = VendorDiscoveryAgent(persist_directory="./test_chroma_db")
    print(f"   Collection count: {agent.collection.count()}")
    
    # Seed sample vendors if empty
    if agent.collection.count() == 0:
        print("\n2. Seeding sample Pakistani vendors...")
        agent.seed_sample_vendors()
    else:
        print(f"\n2. Using existing {agent.collection.count()} vendors")
    
    # Test search 1: Wedding in Lahore
    print("\n3. Test Search: Wedding in Lahore, PKR 500,000 budget")
    requirements1 = EventRequirements(
        event_type="wedding",
        attendees=200,
        date="2026-03-15",
        budget=500000,
        location="Lahore",
        preferences=["traditional", "mehndi"]
    )
    
    results1 = agent.search_vendors(requirements1, top_k=5)
    
    print("\n   Results:")
    for r in results1:
        print(f"   - {r.vendor_id}: PKR {r.cost:,.0f} - {r.reason}")
    
    # Test search 2: Birthday in Karachi
    print("\n4. Test Search: Birthday party in Karachi, PKR 100,000 budget")
    requirements2 = EventRequirements(
        event_type="birthday",
        attendees=50,
        date="2026-04-20",
        budget=100000,
        location="Karachi",
        preferences=["casual", "bbq"]
    )
    
    results2 = agent.search_vendors(requirements2, top_k=5)
    
    print("\n   Results:")
    for r in results2:
        print(f"   - {r.vendor_id}: PKR {r.cost:,.0f} - {r.reason}")
    
    # Test search 3: Corporate event in Islamabad
    print("\n5. Test Search: Corporate conference in Islamabad, PKR 800,000 budget")
    requirements3 = EventRequirements(
        event_type="corporate conference",
        attendees=100,
        date="2026-05-10",
        budget=800000,
        location="Islamabad",
        preferences=["professional", "luxury"]
    )
    
    results3 = agent.search_vendors(requirements3, top_k=5)
    
    print("\n   Results:")
    for r in results3:
        print(f"   - {r.vendor_id}: PKR {r.cost:,.0f} - {r.reason}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = test_vendor_discovery()
    sys.exit(0 if success else 1)
