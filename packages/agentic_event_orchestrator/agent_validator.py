"""
agent_validator.py — Inter-Agent Handoff Validation

Research basis:
  - OWASP ASI05: Privilege Escalation — agents must not blindly trust each other's output
  - OWASP ASI08: Insecure Handoffs — output from one agent must be validated before
    passing as input to the next agent in the chain
  - 2025 AI Agent Index: "Agents trusting each other by default = primary attack vector"

This module wraps the Runner result and re-validates the output before it reaches
the client or is fed into another agent. Also provides tool call audit logging.
"""

import re
import logging
import hashlib
from typing import Any, Optional
from guardrails import (
    filter_output,
    validate_input,
    audit_event,
    mask_pii_for_log,
)

logger = logging.getLogger("agent_validator")

# ─── Patterns that should NEVER appear in agent-to-agent handoff content ──────
_HANDOFF_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|your)\s+instructions?",
    r"you\s+are\s+now\s+(a\s+)?(different|new|another|unrestricted)",
    r"(system|assistant)\s*:\s*.{0,50}(ignore|override|bypass)",
    r"<\|im_start\|>",
    r"\[system\]",
    r"cancel\s+all\s+bookings?",
    r"delete\s+all",
    r"reveal\s+(your|the)\s+(system\s+prompt|instructions?|api.?key)",
]
_COMPILED_HANDOFF = [re.compile(p, re.IGNORECASE) for p in _HANDOFF_INJECTION_PATTERNS]


def validate_agent_output(
    output: str,
    agent_name: str,
    session_id: str,
    user_email: Optional[str] = None,
) -> tuple[str, bool]:
    """
    Validate an agent's output before it reaches the client or another agent.

    Runs two checks:
    1. Handoff injection scan — catches poisoned payloads from agent-to-agent content
    2. Output safety filter — catches harmful content or credential leakage

    Returns:
        (validated_output, was_blocked)
    """
    # 1. Handoff injection detection (indirect injection via agent chain)
    for pattern in _COMPILED_HANDOFF:
        if pattern.search(output):
            logger.warning(
                "Handoff injection caught in %s output | session=%s",
                agent_name, session_id[:8],
            )
            audit_event("handoff_injection_blocked", session_id, user_email, {
                "agent": agent_name,
                "output_preview": mask_pii_for_log(output[:100]),
            })
            return (
                "I encountered an issue processing the response from a sub-system. "
                "Please try rephrasing your request.",
                True,
            )

    # 2. Standard output safety filter (credential leakage, harmful content)
    safe_output, was_filtered = filter_output(output)
    if was_filtered:
        audit_event("agent_output_filtered", session_id, user_email, {
            "agent": agent_name,
        })

    return safe_output, was_filtered


def log_tool_call(
    agent_name: str,
    tool_name: str,
    args: dict,
    session_id: str,
    user_email: Optional[str] = None,
):
    """
    Audit log every tool call made by any agent.
    Args are hashed for sensitive fields — we log the fact but not the value.

    Research basis: OWASP ASI09 — audit gaps; 2025 Agent Index — no public safety evals
    """
    # Hash sensitive arg values — log keys only for sensitive ones
    safe_args = {}
    SENSITIVE_KEYS = {"client_email", "email", "password", "api_key", "token", "secret"}
    for k, v in args.items():
        if k.lower() in SENSITIVE_KEYS:
            safe_args[k] = f"[hashed:{hashlib.sha256(str(v).encode()).hexdigest()[:8]}]"
        elif isinstance(v, str) and len(v) > 100:
            safe_args[k] = v[:40] + "..."
        else:
            safe_args[k] = v

    audit_event("tool_called", session_id, user_email, {
        "agent": agent_name,
        "tool": tool_name,
        "args": safe_args,
    })
    logger.info(
        "[TOOL] %s → %s | session=%s | args=%s",
        agent_name, tool_name, session_id[:8], safe_args,
    )


def validate_inter_agent_input(
    content: str,
    from_agent: str,
    to_agent: str,
    session_id: str,
) -> tuple[str, bool]:
    """
    Validate content being passed from one agent to another.
    Implements the Zero Trust principle between agents.

    Research basis:
    - OWASP ASI05: agents can be used as stepping stones for privilege escalation
    - 2025 AI Agent Index: most deployed multi-agent systems have no inter-agent validation
    """
    # Reuse handoff validation
    validated, blocked = validate_agent_output(content, from_agent, session_id)

    if blocked:
        logger.warning(
            "Inter-agent content blocked: %s → %s | session=%s",
            from_agent, to_agent, session_id[:8],
        )

    return validated, blocked
