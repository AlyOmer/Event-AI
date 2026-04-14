"""Scheduler tools for the Agentic Event Orchestrator.

These tools handle event scheduling, optimization, and constraint checking.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _agents_sdk import function_tool
from pydantic import BaseModel, Field

# Import existing optimizer
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp_processor.structured_output import EventRequirements, VendorSelection
from scheduler.optimizer import Optimizer


class ScheduleItem(BaseModel):
    """A single schedule item."""
    time: str = Field(..., description="Time of the activity (e.g., '10:00 AM')")
    activity: str = Field(..., description="Description of the activity")
    duration_minutes: int = Field(..., description="Duration in minutes")
    vendor_id: Optional[str] = Field(None, description="Assigned vendor if applicable")


class OptimizedSchedule(BaseModel):
    """Complete optimized schedule."""
    event_date: str = Field(..., description="Event date")
    items: List[ScheduleItem] = Field(..., description="Schedule items in order")
    total_duration_hours: float = Field(..., description="Total event duration")


class BudgetBreakdown(BaseModel):
    """Budget breakdown by category."""
    category: str = Field(..., description="Spending category")
    allocated: float = Field(..., description="Budget allocated")
    spent: float = Field(..., description="Amount spent")
    remaining: float = Field(..., description="Remaining budget")


class ConstraintCheckResult(BaseModel):
    """Result of constraint validation."""
    valid: bool = Field(..., description="Whether constraints are satisfied")
    violations: List[str] = Field(default_factory=list, description="List of constraint violations")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for fixes")


# Initialize optimizer
_optimizer = None


def _get_optimizer():
    """Lazy initialization of optimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = Optimizer()
    return _optimizer


@function_tool
def optimize_schedule(
    event_type: str,
    event_date: str,
    start_time: str,
    duration_hours: float,
    attendees: int,
    selected_vendors: str
) -> OptimizedSchedule:
    """Create an optimized event schedule based on event details and vendors.
    
    Args:
        event_type: Type of event (wedding, birthday, corporate, etc.)
        event_date: Event date (YYYY-MM-DD)
        start_time: Start time (HH:MM format)
        duration_hours: Total event duration in hours
        attendees: Number of attendees
        selected_vendors: List of selected vendors with their services
    
    Returns:
        Optimized schedule with timing for all activities
    """
    # Parse start time
    start_dt = datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M")
    
    # Generate schedule based on event type
    schedule_items = []
    
    if "wedding" in event_type.lower() or "mehndi" in event_type.lower() or "baraat" in event_type.lower():
        # Pakistani wedding schedule
        schedule_items = [
            ScheduleItem(
                time=(start_dt - timedelta(hours=2)).strftime("%I:%M %p"),
                activity="Venue Setup & Decoration",
                duration_minutes=120,
                vendor_id=_find_vendor_by_category(selected_vendors, "decoration")
            ),
            ScheduleItem(
                time=start_dt.strftime("%I:%M %p"),
                activity="Guest Arrival & Photography",
                duration_minutes=60,
                vendor_id=_find_vendor_by_category(selected_vendors, "photography")
            ),
            ScheduleItem(
                time=(start_dt + timedelta(hours=1)).strftime("%I:%M %p"),
                activity="Event Begins - Main Ceremony",
                duration_minutes=180,
                vendor_id=None
            ),
            ScheduleItem(
                time=(start_dt + timedelta(hours=2)).strftime("%I:%M %p"),
                activity="Dinner Service",
                duration_minutes=90,
                vendor_id=_find_vendor_by_category(selected_vendors, "catering")
            ),
            ScheduleItem(
                time=(start_dt + timedelta(hours=4)).strftime("%I:%M %p"),
                activity="Event Conclusion & Cleanup",
                duration_minutes=60,
                vendor_id=None
            ),
        ]
    elif "birthday" in event_type.lower() or "party" in event_type.lower():
        # Birthday party schedule
        schedule_items = [
            ScheduleItem(
                time=(start_dt - timedelta(minutes=30)).strftime("%I:%M %p"),
                activity="Venue Setup",
                duration_minutes=30,
                vendor_id=_find_vendor_by_category(selected_vendors, "decoration")
            ),
            ScheduleItem(
                time=start_dt.strftime("%I:%M %p"),
                activity="Guest Arrival",
                duration_minutes=30,
                vendor_id=None
            ),
            ScheduleItem(
                time=(start_dt + timedelta(minutes=30)).strftime("%I:%M %p"),
                activity="Activities & Entertainment",
                duration_minutes=90,
                vendor_id=_find_vendor_by_category(selected_vendors, "entertainment")
            ),
            ScheduleItem(
                time=(start_dt + timedelta(hours=2)).strftime("%I:%M %p"),
                activity="Cake & Food Service",
                duration_minutes=60,
                vendor_id=_find_vendor_by_category(selected_vendors, "catering")
            ),
        ]
    else:
        # Default corporate/general event
        setup_time = 60 if attendees > 50 else 30
        schedule_items = [
            ScheduleItem(
                time=(start_dt - timedelta(minutes=setup_time)).strftime("%I:%M %p"),
                activity="Venue Setup & A/V Check",
                duration_minutes=setup_time,
                vendor_id=_find_vendor_by_category(selected_vendors, "av_equipment")
            ),
            ScheduleItem(
                time=start_dt.strftime("%I:%M %p"),
                activity="Guest Registration & Welcome",
                duration_minutes=30,
                vendor_id=None
            ),
            ScheduleItem(
                time=(start_dt + timedelta(minutes=30)).strftime("%I:%M %p"),
                activity="Main Event Activities",
                duration_minutes=int(duration_hours * 60) - 60,
                vendor_id=None
            ),
            ScheduleItem(
                time=(start_dt + timedelta(hours=duration_hours - 0.5)).strftime("%I:%M %p"),
                activity="Networking & Refreshments",
                duration_minutes=30,
                vendor_id=_find_vendor_by_category(selected_vendors, "catering")
            ),
        ]
    
    return OptimizedSchedule(
        event_date=event_date,
        items=schedule_items,
        total_duration_hours=duration_hours
    )


def _find_vendor_by_category(vendors: List[Dict[str, Any]], category: str) -> Optional[str]:
    """Find a vendor ID by category."""
    for vendor in vendors:
        if vendor.get('category', '').lower() == category.lower():
            return vendor.get('vendor_id') or vendor.get('id')
    return None


@function_tool
def check_constraints(
    event_date: str,
    start_time: str,
    duration_hours: float,
    location: str,
    attendees: int,
    budget: float,
    vendor_costs: List[float]
) -> ConstraintCheckResult:
    """Validate event constraints and provide feedback.
    
    Args:
        event_date: Proposed event date
        start_time: Proposed start time
        duration_hours: Event duration
        location: Event location
        attendees: Number of attendees
        budget: Total budget in PKR
        vendor_costs: List of individual vendor costs
    
    Returns:
        Validation result with any violations and suggestions
    """
    violations = []
    suggestions = []
    
    # Check date validity
    try:
        event_dt = datetime.strptime(event_date, "%Y-%m-%d")
        if event_dt < datetime.now():
            violations.append("Event date is in the past")
            suggestions.append("Select a future date for the event")
    except ValueError:
        violations.append("Invalid date format")
        suggestions.append("Use YYYY-MM-DD format for dates")
    
    # Check budget
    total_vendor_cost = sum(vendor_costs)
    if total_vendor_cost > budget:
        violations.append(f"Vendor costs (PKR {total_vendor_cost:,.0f}) exceed budget (PKR {budget:,.0f})")
        suggestions.append("Reduce number of vendors or negotiate lower prices")
        suggestions.append("Consider increasing the budget")
    
    # Check if budget has reasonable buffer (20%)
    if total_vendor_cost > budget * 0.8:
        suggestions.append("Consider keeping 20% buffer for unexpected expenses")
    
    # Check venue capacity (rough estimate)
    if attendees > 500 and duration_hours > 8:
        suggestions.append("Large events may require additional staff and security")
    
    # Check timing
    if duration_hours < 2:
        suggestions.append("Events shorter than 2 hours may feel rushed")
    if duration_hours > 8:
        suggestions.append("Events longer than 8 hours may require meal breaks")
    
    return ConstraintCheckResult(
        valid=len(violations) == 0,
        violations=violations,
        suggestions=suggestions
    )


@function_tool
def calculate_budget(
    vendor_costs: List[float],
    include_contingency: bool = True
) -> Dict[str, Any]:
    """Calculate total budget with breakdown.
    
    Args:
        vendor_costs: List of vendor costs
        include_contingency: Whether to add 15% contingency
    
    Returns:
        Complete budget breakdown
    """
    subtotal = sum(vendor_costs)
    contingency = subtotal * 0.15 if include_contingency else 0
    total = subtotal + contingency
    
    return {
        "subtotal": subtotal,
        "contingency": contingency,
        "contingency_percentage": 15 if include_contingency else 0,
        "total": total,
        "currency": "PKR",
        "vendor_count": len(vendor_costs),
        "average_cost": subtotal / len(vendor_costs) if vendor_costs else 0
    }


@function_tool
def suggest_event_timing(
    event_type: str,
    season: Optional[str] = None
) -> Dict[str, Any]:
    """Suggest optimal timing for an event based on type and season.
    
    Args:
        event_type: Type of event
        season: Optional season preference (spring, summer, fall, winter)
    
    Returns:
        Timing recommendations
    """
    # Default recommendations
    recommendations = {
        "wedding": {
            "best_days": ["Friday evening", "Sunday afternoon"],
            "best_times": ["7:00 PM - 11:00 PM (evening)", "12:00 PM - 4:00 PM (afternoon)"],
            "duration_hours": 4,
            "notes": "Evening weddings are most popular in Pakistan"
        },
        "birthday": {
            "best_days": ["Saturday", "Sunday"],
            "best_times": ["4:00 PM - 7:00 PM", "11:00 AM - 2:00 PM"],
            "duration_hours": 3,
            "notes": "Afternoon parties work well for families"
        },
        "corporate": {
            "best_days": ["Tuesday", "Wednesday", "Thursday"],
            "best_times": ["9:00 AM - 5:00 PM", "2:00 PM - 6:00 PM (half-day)"],
            "duration_hours": 4,
            "notes": "Mid-week events typically have better attendance"
        },
        "mehndi": {
            "best_days": ["Thursday evening", "Friday evening"],
            "best_times": ["6:00 PM - 11:00 PM"],
            "duration_hours": 5,
            "notes": "Evening events allow for decorative lighting effects"
        }
    }
    
    event_key = event_type.lower()
    if event_key in recommendations:
        return recommendations[event_key]
    
    return {
        "best_days": ["Saturday"],
        "best_times": ["10:00 AM - 4:00 PM"],
        "duration_hours": 4,
        "notes": "General recommendation - customize based on your needs"
    }
