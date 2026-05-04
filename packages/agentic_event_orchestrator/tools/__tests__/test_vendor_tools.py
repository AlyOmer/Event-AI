"""Unit tests for vendor tools with respx mocks."""
import pytest
import respx
import httpx
from unittest.mock import patch, AsyncMock

from tools.vendor_tools import search_vendors, get_vendor_details


class TestSearchVendors:
    """Tests for search_vendors tool."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_search_vendors_success(self):
        """Test successful vendor search."""
        # Mock the backend API response
        mock_response = {
            "success": True,
            "data": {
                "vendors": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "business_name": "Elite Caterers",
                        "category": "Catering",
                        "city": "Lahore",
                        "rating": 4.8,
                        "price_range": "PKR 500-1000 per head"
                    },
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174001",
                        "business_name": "Wedding Photography Co",
                        "category": "Photography",
                        "city": "Karachi",
                        "rating": 4.5,
                        "price_range": "PKR 50,000-100,000"
                    }
                ],
                "total": 2
            }
        }
        
        respx.get("http://localhost:5000/api/v1/public_vendors/").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        result = await search_vendors(
            event_type="wedding",
            location="Lahore",
            budget_pkr=500000
        )
        
        assert result is not None
        assert "vendors" in result
        assert len(result["vendors"]) == 2
        assert result["vendors"][0]["business_name"] == "Elite Caterers"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_search_vendors_no_results(self):
        """Test search with no results."""
        mock_response = {
            "success": True,
            "data": {
                "vendors": [],
                "total": 0
            }
        }
        
        respx.get("http://localhost:5000/api/v1/public_vendors/").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        result = await search_vendors(
            event_type="birthday",
            location="Remote City",
            budget_pkr=10000
        )
        
        assert result["vendors"] == []
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_search_vendors_api_error(self):
        """Test handling of API errors."""
        respx.get("http://localhost:5000/api/v1/public_vendors/").mock(
            return_value=httpx.Response(500, json={"error": "Internal server error"})
        )
        
        result = await search_vendors(
            event_type="wedding",
            location="Lahore",
            budget_pkr=500000
        )
        
        # Should return error message, not crash
        assert "error" in result or result.get("vendors") == []
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_search_vendors_timeout(self):
        """Test handling of request timeout."""
        respx.get("http://localhost:5000/api/v1/public_vendors/").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )
        
        result = await search_vendors(
            event_type="wedding",
            location="Lahore",
            budget_pkr=500000
        )
        
        assert "error" in result


class TestGetVendorDetails:
    """Tests for get_vendor_details tool."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_vendor_details_success(self):
        """Test successful vendor detail retrieval."""
        vendor_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_response = {
            "success": True,
            "data": {
                "id": vendor_id,
                "business_name": "Elite Caterers",
                "description": "Premium catering services for weddings and events",
                "category": "Catering",
                "city": "Lahore",
                "rating": 4.8,
                "total_reviews": 150,
                "price_range": "PKR 500-1000 per head",
                "services": ["Full Service Catering", "Buffet", "Live Cooking"],
                "contact_email": "info@elitecaterers.pk"
            }
        }
        
        respx.get(f"http://localhost:5000/api/v1/public_vendors/{vendor_id}").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        result = await get_vendor_details(vendor_id)
        
        assert result["id"] == vendor_id
        assert result["business_name"] == "Elite Caterers"
        assert len(result["services"]) == 3
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_vendor_details_not_found(self):
        """Test vendor not found."""
        vendor_id = "123e4567-e89b-12d3-a456-426614174999"
        
        respx.get(f"http://localhost:5000/api/v1/public_vendors/{vendor_id}").mock(
            return_value=httpx.Response(404, json={"error": "Vendor not found"})
        )
        
        result = await get_vendor_details(vendor_id)
        
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_vendor_details_invalid_id(self):
        """Test with invalid vendor ID format."""
        result = await get_vendor_details("invalid-uuid")
        
        assert "error" in result
