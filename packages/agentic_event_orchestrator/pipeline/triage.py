"""TriageAgent — sole entry point with SDK-native input/output guardrails."""
from agents import Agent
from pipeline.instructions import TRIAGE_INSTRUCTIONS
from services.guardrail_hooks import injection_guardrail, leak_detection_guardrail


def build_triage_agent(model, event_planner, vendor_discovery, booking, orchestrator):
    return Agent(
        name="TriageAgent",
        model=model,
        instructions=TRIAGE_INSTRUCTIONS,
        handoffs=[event_planner, vendor_discovery, booking, orchestrator],
        # SDK-native guardrails:
        # - injection_guardrail runs BEFORE LLM (blocking) — zero tokens on blocked input
        # - leak_detection_guardrail runs AFTER final output
        input_guardrails=[injection_guardrail],
        output_guardrails=[leak_detection_guardrail],
    )
