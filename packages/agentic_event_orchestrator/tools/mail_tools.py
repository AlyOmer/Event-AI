"""Mail and communication tools for the Agentic Event Orchestrator.

These tools handle email invitations, RSVP tracking, and guest communication.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _agents_sdk import function_tool
from pydantic import BaseModel, Field


class EmailResult(BaseModel):
    """Result of an email operation."""
    success: bool = Field(..., description="Whether the operation succeeded")
    recipients_sent: int = Field(..., description="Number of recipients who received the email")
    failed_recipients: List[str] = Field(default_factory=list, description="Emails that failed")
    message_id: Optional[str] = Field(None, description="Message identifier for tracking")


class RSVPStatus(BaseModel):
    """RSVP tracking information."""
    email: str = Field(..., description="Guest email")
    status: str = Field(..., description="RSVP status: accepted, declined, pending")
    guests_count: int = Field(1, description="Number of guests attending")
    dietary_restrictions: Optional[str] = Field(None, description="Any dietary notes")
    responded_at: Optional[str] = Field(None, description="When they responded")


class GuestListSummary(BaseModel):
    """Summary of guest list status."""
    total_invited: int = Field(..., description="Total guests invited")
    accepted: int = Field(..., description="Number who accepted")
    declined: int = Field(..., description="Number who declined")
    pending: int = Field(..., description="Number who haven't responded")
    total_attending: int = Field(..., description="Total confirmed attendees")


@function_tool
def send_invitations(
    event_type: str,
    event_date: str,
    event_time: str,
    location: str,
    guest_emails: List[str],
    custom_message: Optional[str] = None,
    rsvp_deadline: Optional[str] = None
) -> EmailResult:
    """Send email invitations to guests for an event.
    
    Args:
        event_type: Type of event (wedding, birthday, corporate, etc.)
        event_date: Event date (YYYY-MM-DD)
        event_time: Event time (e.g., "7:00 PM")
        location: Event venue/location
        guest_emails: List of guest email addresses
        custom_message: Optional custom message to include
        rsvp_deadline: Optional RSVP deadline date
    
    Returns:
        Result of the email sending operation
    """
    # In production, this would integrate with an email service
    # For now, we simulate the operation
    
    failed = []
    sent_count = 0
    
    for email in guest_emails:
        # Validate email format (simple check)
        if "@" in email and "." in email:
            sent_count += 1
            logging.getLogger("tools.mail").info("Invitation sent to %s for %s on %s", email, event_type, event_date)
        else:
            failed.append(email)
    
    message_id = f"invite_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return EmailResult(
        success=len(failed) == 0,
        recipients_sent=sent_count,
        failed_recipients=failed,
        message_id=message_id
    )


@function_tool
def track_rsvps(
    event_id: str,
    guest_list: Optional[List[str]] = None
) -> GuestListSummary:
    """Track RSVP responses for an event.
    
    Args:
        event_id: Unique event identifier
        guest_list: Optional list of invited guests to track
    
    Returns:
        Summary of RSVP status
    """
    # In production, this would query a database
    # For now, return a simulated response
    
    # Simulate realistic RSVP data
    if guest_list:
        total = len(guest_list)
        accepted = int(total * 0.65)  # 65% acceptance rate
        declined = int(total * 0.15)  # 15% decline
        pending = total - accepted - declined
    else:
        total = 50
        accepted = 32
        declined = 8
        pending = 10
    
    return GuestListSummary(
        total_invited=total,
        accepted=accepted,
        declined=declined,
        pending=pending,
        total_attending=accepted + (pending // 2)  # Assume half of pending will attend
    )


@function_tool
def get_detailed_rsvps(
    event_id: str
) -> List[RSVPStatus]:
    """Get detailed RSVP status for each guest.
    
    Args:
        event_id: Unique event identifier
    
    Returns:
        List of individual RSVP statuses
    """
    # In production, this would query from a database
    # For now, return sample data
    
    sample_rsvps = [
        RSVPStatus(
            email="guest1@example.com",
            status="accepted",
            guests_count=2,
            dietary_restrictions="Vegetarian",
            responded_at="2026-01-15T10:30:00"
        ),
        RSVPStatus(
            email="guest2@example.com",
            status="accepted",
            guests_count=1,
            responded_at="2026-01-16T14:20:00"
        ),
        RSVPStatus(
            email="guest3@example.com",
            status="declined",
            guests_count=0,
            responded_at="2026-01-14T09:15:00"
        ),
        RSVPStatus(
            email="guest4@example.com",
            status="pending",
            guests_count=1
        ),
    ]
    
    return sample_rsvps


@function_tool
def send_reminders(
    event_type: str,
    event_date: str,
    event_time: str,
    location: str,
    guest_emails: List[str],
    reminder_type: str = "week_before"
) -> EmailResult:
    """Send reminder emails to guests.
    
    Args:
        event_type: Type of event
        event_date: Event date
        event_time: Event time
        location: Event location
        guest_emails: List of guest emails to remind
        reminder_type: Type of reminder ('week_before', 'day_before', 'day_of')
    
    Returns:
        Result of the reminder sending operation
    """
    # Map reminder type to message
    messages = {
        "week_before": f"One week until the {event_type}! We look forward to seeing you on {event_date} at {event_time}.",
        "day_before": f"Tomorrow is the big day! Don't forget the {event_type} at {event_time} at {location}.",
        "day_of": f"Today's the {event_type}! See you at {event_time} at {location}."
    }
    
    message = messages.get(reminder_type, messages["week_before"])
    
    # Simulate sending
    sent_count = 0
    failed = []
    
    for email in guest_emails:
        if "@" in email and "." in email:
            sent_count += 1
            logging.getLogger("tools.mail").info("%s reminder sent to %s", reminder_type, email)
        else:
            failed.append(email)
    
    return EmailResult(
        success=len(failed) == 0,
        recipients_sent=sent_count,
        failed_recipients=failed,
        message_id=f"reminder_{reminder_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )


@function_tool
def generate_invitation_text(
    event_type: str,
    event_date: str,
    event_time: str,
    location: str,
    host_name: Optional[str] = None,
    dress_code: Optional[str] = None,
    additional_notes: Optional[str] = None
) -> str:
    """Generate elegant invitation text for an event.
    
    Args:
        event_type: Type of event
        event_date: Event date
        event_time: Event time
        location: Event location
        host_name: Optional host name
        dress_code: Optional dress code
        additional_notes: Optional additional information
    
    Returns:
        Formatted invitation text
    """
    # Format date nicely
    try:
        dt = datetime.strptime(event_date, "%Y-%m-%d")
        formatted_date = dt.strftime("%A, %B %d, %Y")
    except:
        formatted_date = event_date
    
    # Build invitation
    lines = []
    
    if event_type.lower() == "wedding":
        lines.extend([
            "You're Invited!",
            "",
            f"Join us in celebrating the wedding of",
            "",
            f"{host_name or 'our beloved couple'}",
            "",
            f"📅 Date: {formatted_date}",
            f"🕒 Time: {event_time}",
            f"📍 Location: {location}",
        ])
    elif event_type.lower() == "birthday":
        lines.extend([
            "You're Invited to a Birthday Celebration!",
            "",
            f"Join us to celebrate {host_name or 'a special birthday'}!",
            "",
            f"📅 Date: {formatted_date}",
            f"🕒 Time: {event_time}",
            f"📍 Location: {location}",
        ])
    else:
        lines.extend([
            f"You're Invited: {event_type.title()}",
            "",
            f"📅 Date: {formatted_date}",
            f"🕒 Time: {event_time}",
            f"📍 Location: {location}",
        ])
    
    if dress_code:
        lines.extend(["", f"👔 Dress Code: {dress_code}"])
    
    if additional_notes:
        lines.extend(["", f"📝 Note: {additional_notes}"])
    
    lines.extend(["", "We look forward to seeing you there!"])
    lines.extend(["", "Please RSVP at your earliest convenience."])
    
    return "\n".join(lines)
