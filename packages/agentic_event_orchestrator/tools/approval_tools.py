"""Approval workflow tools for the Agentic Event Orchestrator.

These tools handle approval requests, notifications, and decision tracking.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _agents_sdk import function_tool
from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """An approval request for an event plan."""
    request_id: str = Field(..., description="Unique request identifier")
    event_type: str = Field(..., description="Type of event")
    total_cost: float = Field(..., description="Total cost in PKR")
    vendor_count: int = Field(..., description="Number of vendors")
    requester: str = Field(..., description="Who requested the approval")
    requested_at: str = Field(..., description="When the request was made")
    status: str = Field(..., description="Current status: pending, approved, rejected")


class ApprovalDecision(BaseModel):
    """Result of an approval decision."""
    request_id: str = Field(..., description="Request identifier")
    approved: bool = Field(..., description="Whether approved or rejected")
    decision_by: Optional[str] = Field(None, description="Who made the decision")
    decided_at: Optional[str] = Field(None, description="When the decision was made")
    notes: Optional[str] = Field(None, description="Decision notes/comments")


class BudgetApprovalResult(BaseModel):
    """Result of budget approval check."""
    can_approve: bool = Field(..., description="Whether within approval limits")
    requires_additional_approval: bool = Field(..., description="Needs higher approval")
    approver_level: str = Field(..., description="Required approver level")
    reason: str = Field(..., description="Explanation for the result")


@function_tool
def request_approval(
    event_type: str,
    total_cost: float,
    vendor_count: int,
    plan_summary: str,
    requester: str = "event_coordinator",
    urgency: str = "normal"
) -> ApprovalRequest:
    """Create an approval request for an event plan.
    
    Args:
        event_type: Type of event being planned
        total_cost: Total cost in PKR
        vendor_count: Number of vendors in the plan
        plan_summary: Brief summary of the plan
        requester: Who is requesting approval
        urgency: Urgency level (low, normal, high, critical)
    
    Returns:
        The created approval request
    """
    request_id = f"APPROVAL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Determine approver level based on cost
    if total_cost < 100000:
        approver_level = "manager"
    elif total_cost < 500000:
        approver_level = "director"
    else:
        approver_level = "executive"
    
    logger = logging.getLogger("tools.approval")
    logger.info("Approval request %s created — Event: %s, Cost: PKR %s, Level: %s, Urgency: %s",
                request_id, event_type, f"{total_cost:,.0f}", approver_level, urgency)
    
    return ApprovalRequest(
        request_id=request_id,
        event_type=event_type,
        total_cost=total_cost,
        vendor_count=vendor_count,
        requester=requester,
        requested_at=datetime.now().isoformat(),
        status="pending"
    )


@function_tool
def check_budget_approval_limits(
    budget_amount: float,
    requester_role: str = "coordinator"
) -> BudgetApprovalResult:
    """Check if a budget amount requires additional approvals.
    
    Args:
        budget_amount: The budget to check in PKR
        requester_role: Role of the person requesting (coordinator, manager, director)
    
    Returns:
        Approval limit check result
    """
    # Define approval limits by role (in PKR)
    limits = {
        "coordinator": 50000,
        "manager": 200000,
        "director": 1000000,
        "executive": float('inf')
    }
    
    user_limit = limits.get(requester_role, 0)
    
    if budget_amount <= user_limit:
        return BudgetApprovalResult(
            can_approve=True,
            requires_additional_approval=False,
            approver_level=requester_role,
            reason=f"Budget within {requester_role} approval limit (PKR {user_limit:,.0f})"
        )
    
    # Find the required approver level
    for role, limit in sorted(limits.items(), key=lambda x: x[1]):
        if budget_amount <= limit:
            return BudgetApprovalResult(
                can_approve=False,
                requires_additional_approval=True,
                approver_level=role,
                reason=f"Budget PKR {budget_amount:,.0f} exceeds {requester_role} limit. Requires {role} approval."
            )
    
    return BudgetApprovalResult(
        can_approve=False,
        requires_additional_approval=True,
        approver_level="executive",
        reason=f"Budget PKR {budget_amount:,.0f} requires executive approval"
    )


@function_tool
def notify_stakeholders(
    event_type: str,
    event_date: str,
    stakeholders: List[str],
    notification_type: str = "plan_created",
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Notify stakeholders about event plan updates.
    
    Args:
        event_type: Type of event
        event_date: Event date
        stakeholders: List of stakeholder emails/identifiers
        notification_type: Type of notification (plan_created, approved, cancelled, updated)
        message: Optional custom message
    
    Returns:
        Notification result
    """
    # Default messages by type
    default_messages = {
        "plan_created": f"A new {event_type} plan has been created for {event_date} and is pending approval.",
        "approved": f"The {event_type} plan for {event_date} has been approved and booking is in progress.",
        "rejected": f"The {event_type} plan for {event_date} requires revisions. Please review feedback.",
        "cancelled": f"The {event_type} for {event_date} has been cancelled.",
        "updated": f"The {event_type} plan for {event_date} has been updated with new details.",
        "booking_confirmed": f"All vendors for the {event_type} on {event_date} have been confirmed."
    }
    
    final_message = message or default_messages.get(notification_type, "Event plan update.")
    
    # Simulate notifications
    notified = []
    failed = []
    
    for stakeholder in stakeholders:
        if "@" in stakeholder:
            notified.append(stakeholder)
            logging.getLogger("tools.approval").info("Notified %s: %s", stakeholder, notification_type)
        else:
            failed.append(stakeholder)
    
    return {
        "notification_type": notification_type,
        "stakeholders_notified": len(notified),
        "failed": failed,
        "message_sent": final_message,
        "timestamp": datetime.now().isoformat()
    }


@function_tool
def record_approval_decision(
    request_id: str,
    approved: bool,
    decision_by: str,
    notes: Optional[str] = None
) -> ApprovalDecision:
    """Record an approval decision.
    
    Args:
        request_id: The approval request ID
        approved: Whether approved (True) or rejected (False)
        decision_by: Who made the decision
        notes: Optional decision notes
    
    Returns:
        Recorded decision
    """
    status = "approved" if approved else "rejected"
    
    logger = logging.getLogger("tools.approval")
    logger.info("Approval decision recorded for %s — %s by %s%s",
                request_id, status.upper(), decision_by, f" ({notes})" if notes else "")
    
    return ApprovalDecision(
        request_id=request_id,
        approved=approved,
        decision_by=decision_by,
        decided_at=datetime.now().isoformat(),
        notes=notes
    )


@function_tool
def get_approval_history(
    event_type: Optional[str] = None,
    status: Optional[str] = None
) -> List[ApprovalRequest]:
    """Get approval request history.
    
    Args:
        event_type: Optional filter by event type
        status: Optional filter by status (pending, approved, rejected)
    
    Returns:
        List of approval requests
    """
    # In production, this would query a database
    # For now, return sample data
    
    sample_requests = [
        ApprovalRequest(
            request_id="APPROVAL_20260101120000",
            event_type="wedding",
            total_cost=500000,
            vendor_count=5,
            requester="coordinator_1",
            requested_at="2026-01-01T12:00:00",
            status="approved"
        ),
        ApprovalRequest(
            request_id="APPROVAL_20260102150000",
            event_type="birthday",
            total_cost=75000,
            vendor_count=3,
            requester="coordinator_2",
            requested_at="2026-01-02T15:00:00",
            status="pending"
        ),
    ]
    
    # Apply filters
    filtered = sample_requests
    if event_type:
        filtered = [r for r in filtered if r.event_type == event_type]
    if status:
        filtered = [r for r in filtered if r.status == status]
    
    return filtered
