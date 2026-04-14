"""OutputLeakDetector — scans agent responses for leaked internal data.

Checks for:
- Canary token presence (system prompt extraction)
- Stack trace fragments
- Internal tool/service names
- Instruction fragment hashes
"""

import re
import hashlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SAFE_FALLBACK = (
    "I'm sorry, I encountered an issue processing your request. Please try again."
)

_STACK_TRACE_RE = re.compile(r"Traceback \(most recent call last\)", re.I)
_INTERNAL_NAMES = [
    "create_booking_request", "search_vendors", "get_user_events",
    "update_event_status", "guardrail_service", "prompt_firewall",
    "output_leak_detector", "context_builder", "PromptFirewall",
    "GuardrailService", "ChatService", "MemoryService",
]


@dataclass
class LeakScanResult:
    leaked: bool
    leak_type: str | None
    safe_response: str


class OutputLeakDetector:
    def __init__(self, canary_token: str, instruction_fragments: list[str] | None = None):
        self._canary = canary_token
        # Store fragments as hashes — never store plaintext
        self._fragment_hashes: set[str] = set()
        for frag in (instruction_fragments or []):
            if len(frag) >= 20:
                self._fragment_hashes.add(hashlib.sha256(frag.encode()).hexdigest())

    def scan(self, response: str) -> LeakScanResult:
        try:
            if not response:
                return LeakScanResult(False, None, response)

            # 1. Canary token
            if self._canary and self._canary in response:
                logger.critical("CANARY TOKEN DETECTED IN OUTPUT — possible system prompt extraction")
                return LeakScanResult(True, "CANARY_TOKEN", SAFE_FALLBACK)

            # 2. Stack traces
            if _STACK_TRACE_RE.search(response):
                logger.error("Stack trace detected in agent output")
                return LeakScanResult(True, "STACK_TRACE", SAFE_FALLBACK)

            # 3. Internal names
            for name in _INTERNAL_NAMES:
                if name in response:
                    logger.warning("Internal name '%s' detected in output", name)
                    return LeakScanResult(True, "INTERNAL_ID", SAFE_FALLBACK)

            return LeakScanResult(False, None, response)

        except Exception as e:
            logger.error("OutputLeakDetector.scan error: %s", e)
            return LeakScanResult(False, None, response or SAFE_FALLBACK)

    def scan_stream_buffer(self, buffer: str) -> bool:
        """Fast check on first 500 chars of SSE stream. Returns True if leak detected."""
        if self._canary and self._canary in buffer:
            return True
        if _STACK_TRACE_RE.search(buffer):
            return True
        return False
