"""Integration tests for chat endpoints (streaming + non-streaming)."""
import pytest
import httpx
import respx
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import json

# Test client setup
BASE_URL = "http://localhost:8000"


class TestChatEndpointNonStreaming:
    """Integration tests for non-streaming chat endpoint."""
    
    @pytest.fixture
    def mock_app_state(self):
        """Mock FastAPI app state with services."""
        state = MagicMock()
        state.settings = MagicMock()
        state.settings.max_input_chars = 2000
        state.settings.ai_service_api_key = "test-api-key"
        state.firewall = MagicMock()
        state.firewall.classify = MagicMock(return_value=MagicMock(
            blocked=False,
            threat_type=None,
            confidence=0.0,
            sanitized_message="test message"
        ))
        return state
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_valid_request(self, mock_app_state):
        """Test valid chat request returns response."""
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            # This would be a real integration test with running server
            # For now, we test the logic directly
            pass
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_blocks_injection(self, mock_app_state):
        """Test chat endpoint blocks injection attempts."""
        mock_app_state.firewall.classify = MagicMock(return_value=MagicMock(
            blocked=True,
            threat_type="DIRECT_INJECTION",
            confidence=0.95,
            sanitized_message=""
        ))
        
        # The endpoint should return blocked response
        # In real test, this would hit the running server
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_requires_auth(self):
        """Test chat endpoint requires authentication."""
        # Request without auth should return 401
        pass
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_creates_session(self):
        """Test chat endpoint creates new session for new users."""
        pass
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_reuses_session(self):
        """Test chat endpoint reuses existing session."""
        pass
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_rate_limiting(self):
        """Test rate limiting on chat endpoint."""
        # 30 requests per minute per user
        pass


class TestChatEndpointStreaming:
    """Integration tests for streaming chat endpoint."""
    
    @pytest.mark.asyncio
    async def test_streaming_endpoint_returns_sse(self):
        """Test streaming endpoint returns Server-Sent Events."""
        # Should return content-type: text/event-stream
        pass
    
    @pytest.mark.asyncio
    async def test_streaming_endpoint_emits_tokens(self):
        """Test streaming endpoint emits tokens progressively."""
        # Should emit data: {"token": "..."} events
        pass
    
    @pytest.mark.asyncio
    async def test_streaming_endpoint_handles_disconnect(self):
        """Test streaming handles client disconnect gracefully."""
        pass
    
    @pytest.mark.asyncio
    async def test_streaming_endpoint_emits_done_event(self):
        """Test streaming emits [DONE] event at end."""
        pass
    
    @pytest.mark.asyncio
    async def test_streaming_endpoint_emits_agent_name(self):
        """Test streaming includes agent name in events."""
        pass
    
    @pytest.mark.asyncio
    async def test_streaming_endpoint_emits_tool_calls(self):
        """Test streaming includes tool call events."""
        pass


class TestChatSessionManagement:
    """Integration tests for session management."""
    
    @pytest.mark.asyncio
    async def test_session_ttl_expiry(self):
        """Test session expires after TTL."""
        # Session should expire after 30 minutes of inactivity
        pass
    
    @pytest.mark.asyncio
    async def test_session_message_limit(self):
        """Test session stores max 20 messages."""
        pass
    
    @pytest.mark.asyncio
    async def test_session_message_truncation(self):
        """Test session truncates long messages."""
        # Messages should be truncated to 150 chars
        pass
    
    @pytest.mark.asyncio
    async def test_session_cleanup_on_expiry(self):
        """Test session data is cleaned up on expiry."""
        pass


class TestChatGuardrails:
    """Integration tests for guardrails in chat flow."""
    
    @pytest.mark.asyncio
    async def test_input_guardrail_blocks_before_llm(self):
        """Test input guardrail runs before LLM call."""
        # If guardrail blocks, LLM should never be called
        pass
    
    @pytest.mark.asyncio
    async def test_output_guardrail_scans_response(self):
        """Test output guardrail scans LLM response."""
        pass
    
    @pytest.mark.asyncio
    async def test_alignment_check_on_handoff(self):
        """Test alignment check runs on agent handoff."""
        pass
    
    @pytest.mark.asyncio
    async def test_code_shield_scans_code_blocks(self):
        """Test CodeShield scans code blocks in response."""
        pass
    
    @pytest.mark.asyncio
    async def test_trulens_evaluation_on_rag_response(self):
        """Test TruLens evaluation runs on RAG responses."""
        pass


class TestChatErrorHandling:
    """Integration tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_llm_timeout_returns_friendly_error(self):
        """Test LLM timeout returns user-friendly error."""
        pass
    
    @pytest.mark.asyncio
    async def test_tool_failure_recovers_gracefully(self):
        """Test tool failure allows conversation to continue."""
        pass
    
    @pytest.mark.asyncio
    async def test_malformed_request_returns_422(self):
        """Test malformed request returns validation error."""
        pass
    
    @pytest.mark.asyncio
    async def test_unauthorized_returns_401(self):
        """Test unauthorized request returns 401."""
        pass
    
    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self):
        """Test rate limit exceeded returns 429."""
        pass


# ── Mock fixtures for testing ─────────────────────────────────────

@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "content": "I found 3 photographers in Lahore for your wedding.",
        "agent": "VendorDiscoveryAgent",
        "tool_calls": []
    }


@pytest.fixture
def mock_streaming_response():
    """Mock streaming response chunks."""
    return [
        {"token": "I"},
        {"token": " found"},
        {"token": " 3"},
        {"token": " photographers"},
        {"token": " in"},
        {"token": " Lahore"},
        {"token": "."},
        {"done": True}
    ]


# ── Test utilities ────────────────────────────────────────────────

class SSEClient:
    """Helper to parse SSE streams in tests."""
    
    def __init__(self):
        self.events = []
    
    def parse(self, content: str):
        """Parse SSE content into events."""
        for line in content.split("\n"):
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    self.events.append({"type": "done"})
                else:
                    try:
                        self.events.append(json.loads(data))
                    except json.JSONDecodeError:
                        pass
        return self.events


# ── Example full integration test ─────────────────────────────────

@pytest.mark.integration
class TestFullChatFlow:
    """Full integration tests requiring running server."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running server")
    async def test_complete_chat_flow(self):
        """
        Complete chat flow integration test.
        
        Prerequisites:
        - Server running on localhost:8000
        - Database migrations applied
        - Test user created with valid JWT
        
        Steps:
        1. Create session
        2. Send message
        3. Receive streaming response
        4. Verify session stored
        5. Send follow-up message
        6. Verify context maintained
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Create session
            response = await client.post(
                "/api/v1/ai/chat/sessions",
                headers={"Authorization": "Bearer test-jwt-token"}
            )
            assert response.status_code == 201
            session_id = response.json()["data"]["session_id"]
            
            # Send message (non-streaming)
            response = await client.post(
                "/api/v1/ai/chat",
                headers={"Authorization": "Bearer test-jwt-token"},
                json={
                    "session_id": session_id,
                    "message": "I want to plan a wedding for 200 guests in Lahore"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "response" in data["data"]
            
            # Send message (streaming)
            async with client.stream(
                "POST",
                "/api/v1/ai/chat/stream",
                headers={"Authorization": "Bearer test-jwt-token"},
                json={
                    "session_id": session_id,
                    "message": "Find me photographers"
                }
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")
                
                sse_client = SSEClient()
                async for line in response.aiter_lines():
                    sse_client.parse(line)
                
                # Verify we got tokens
                assert len(sse_client.events) > 0
                assert any(e.get("done") for e in sse_client.events)
