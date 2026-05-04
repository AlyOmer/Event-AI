"""
AlignmentCheck — Per-handoff validator to detect agent drift.

Research basis:
- LlamaFirewall (Meta, 2024) — alignment checking for agent handoffs
- "Agent Alignment: A Taxonomy of Misalignment" (arXiv 2025)
- Constitutional AI principles for agent behavior verification

Purpose:
When an agent hands off to another agent, validate that the handoff context
aligns with expected behavior patterns. Abort if drift exceeds threshold.

This prevents:
- Agent role confusion (BookingAgent acting as TriageAgent)
- Scope escape (vendor discovery agent attempting bookings)
- Instruction leakage between agents
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Alignment thresholds
ALIGNMENT_THRESHOLD_HIGH = 0.85  # High confidence required for handoff approval
ALIGNMENT_THRESHOLD_LOW = 0.50  # Below this = definite drift

# Expected scope keywords per agent type
AGENT_SCOPE_KEYWORDS = {
    "TriageAgent": ["event", "plan", "vendor", "book", "help", "assist", "welcome"],
    "EventPlannerAgent": ["event", "create", "date", "location", "guest", "budget", "type"],
    "VendorDiscoveryAgent": ["vendor", "search", "find", "recommend", "category", "price", "rating"],
    "BookingAgent": ["book", "confirm", "cancel", "inquiry", "vendor_id", "service", "date"],
    "OrchestratorAgent": ["coordinate", "delegate", "step", "workflow", "next"],
}

# Forbidden cross-scope patterns (e.g., vendor agent trying to book)
CROSS_SCOPE_VIOLATIONS = {
    "VendorDiscoveryAgent": [
        r"\b(create_booking|cancel_booking|confirm_booking)\b",
        r"\bbook\s+(this|the)\s+vendor\b",
    ],
    "EventPlannerAgent": [
        r"\bsearch_vendors\b",
        r"\bcreate_booking\b",
    ],
    "BookingAgent": [
        r"\bsearch_vendors\b",
        r"\bcreate_event\b",
    ],
}


@dataclass
class AlignmentResult:
    """Result of alignment check between agents."""
    aligned: bool
    confidence: float
    drift_type: Optional[str] = None
    details: Optional[str] = None
    should_abort: bool = False


class AlignmentChecker:
    """
    Validates agent handoffs for alignment with expected behavior.
    
    Usage:
        checker = AlignmentChecker()
        result = checker.check_handoff(
            from_agent="VendorDiscoveryAgent",
            to_agent="BookingAgent", 
            handoff_context="User wants to book vendor X"
        )
        if result.should_abort:
            # Block handoff, return error to user
    """
    
    def __init__(self, threshold: float = ALIGNMENT_THRESHOLD_HIGH):
        self._threshold = threshold
        self._violation_patterns = {
            agent: [re.compile(p, re.I) for p in patterns]
            for agent, patterns in CROSS_SCOPE_VIOLATIONS.items()
        }
    
    def check_handoff(
        self,
        from_agent: str,
        to_agent: str,
        handoff_context: str,
        conversation_history: Optional[list[str]] = None,
    ) -> AlignmentResult:
        """
        Check if a handoff from one agent to another is aligned.
        
        Args:
            from_agent: Name of the agent initiating handoff
            to_agent: Name of the target agent
            handoff_context: The message/context being passed
            conversation_history: Optional recent messages for context
        
        Returns:
            AlignmentResult with aligned status and confidence
        """
        try:
            # 1. Check for cross-scope violations from source agent
            violation = self._check_cross_scope(from_agent, handoff_context)
            if violation:
                logger.warning(
                    "ALIGNMENT VIOLATION: %s attempted cross-scope action: %s",
                    from_agent, violation
                )
                return AlignmentResult(
                    aligned=False,
                    confidence=0.9,
                    drift_type="cross_scope_violation",
                    details=f"Agent {from_agent} attempted action outside its scope: {violation}",
                    should_abort=True,
                )
            
            # 2. Check target agent scope alignment
            scope_confidence = self._check_scope_alignment(to_agent, handoff_context)
            
            # 3. Check for instruction leakage patterns
            leak_detected = self._check_instruction_leak(handoff_context)
            if leak_detected:
                return AlignmentResult(
                    aligned=False,
                    confidence=0.95,
                    drift_type="instruction_leak",
                    details="Potential instruction leakage detected in handoff context",
                    should_abort=True,
                )
            
            # 4. Determine final alignment
            aligned = scope_confidence >= self._threshold
            should_abort = scope_confidence < ALIGNMENT_THRESHOLD_LOW
            
            if not aligned:
                logger.warning(
                    "ALIGNMENT DRIFT: handoff to %s has confidence %.2f (threshold %.2f)",
                    to_agent, scope_confidence, self._threshold
                )
            
            return AlignmentResult(
                aligned=aligned,
                confidence=scope_confidence,
                drift_type=None if aligned else "low_scope_confidence",
                details=f"Scope alignment score: {scope_confidence:.2f}",
                should_abort=should_abort,
            )
            
        except Exception as e:
            logger.error("AlignmentCheck error: %s — blocking as fail-safe", e)
            return AlignmentResult(
                aligned=False,
                confidence=1.0,
                drift_type="check_error",
                details=str(e),
                should_abort=True,
            )
    
    def _check_cross_scope(self, agent: str, context: str) -> Optional[str]:
        """Check if agent is attempting actions outside its scope."""
        patterns = self._violation_patterns.get(agent, [])
        for pattern in patterns:
            match = pattern.search(context)
            if match:
                return match.group(0)
        return None
    
    def _check_scope_alignment(self, agent: str, context: str) -> float:
        """
        Calculate how well the context aligns with expected agent scope.
        Returns confidence score 0.0-1.0.
        """
        expected_keywords = AGENT_SCOPE_KEYWORDS.get(agent, [])
        if not expected_keywords:
            return 0.7  # Unknown agent — moderate confidence
        
        context_lower = context.lower()
        matches = sum(1 for kw in expected_keywords if kw in context_lower)
        
        # Normalize by expected keyword count
        confidence = matches / len(expected_keywords) if expected_keywords else 0.5
        
        # Boost if context is short (likely valid handoff)
        if len(context) < 200:
            confidence = min(1.0, confidence + 0.2)
        
        return min(1.0, confidence)
    
    def _check_instruction_leak(self, context: str) -> bool:
        """Check for instruction/system prompt leakage patterns."""
        leak_patterns = [
            r"your\s+instructions?\s+are",
            r"system\s+prompt",
            r"you\s+must\s+always",
            r"never\s+reveal",
            r"<\|im_start\|>",
            r"\[SYSTEM\]",
        ]
        for pattern in leak_patterns:
            if re.search(pattern, context, re.I):
                return True
        return False


# Singleton instance
alignment_checker = AlignmentChecker()
