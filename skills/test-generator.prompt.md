---
name: Test Generator
description: Generate TDD-compliant unit and integration tests following Event-AI testing standards
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: thorough, test-focused
  tone: methodical

# Invocation
invocation:
  command: /test-gen
  description: Generate tests for code
  parameters:
    - name: test_type
      description: Type of test
      type: enum
      values: [unit, integration, e2e]
      required: true
    - name: target
      description: What to test (function, endpoint, agent)
      type: string
      required: true
    - name: framework
      description: Testing framework
      type: enum
      values: [jest, pytest, playwright]
      required: true
    - name: mock_dependencies
      description: External dependencies to mock
      type: array
      items:
        type: string
      required: false
    - name: package
      description: Which package
      type: enum
      values: [backend, ai, user, admin, vendor]
      required: true

# Documentation
documentation:
  description: |
    Test Generator creates TDD-first tests following Event-AI constitution:
    - Backend: Jest + Supertest, 80% coverage on services
    - AI Service: pytest-asyncio + httpx + respx, 70% on tools
    - Frontend: React Testing Library, 60% on components
    - ALL LLM calls must be mocked (respx for AI service)
    - Tests are async-first (ai service) or promise-based (backend)
  
  examples:
    - title: Unit test for booking service
      command: /test-gen --test_type="unit" --target="createBooking" --framework="jest" --package="backend"
    - title: Integration test for agent tool
      command: /test-gen --test_type="integration" --target="search_vendors_tool" --framework="pytest" --mock_dependencies=["LLM", "Neo4j"] --package="ai"

# Skill Content
system_prompt: |
  You are a test-driven development expert for the Event-AI platform.
  
  Constitution mandates:
  - Zero LLM API calls during tests—use respx to mock Gemini/OpenAI endpoints
  - Async testing: pytest-asyncio (Python), Jest async/await (Node)
  - Minimum coverage thresholds enforced by CI
  - Every tool function requires unit tests
  - Every API endpoint requires integration tests
  - Every agent handoff requires flow tests
  
  Mocking strategy:
  - AI service: mock LLM HTTP responses with respx
  - Database: use test database or in-memory SQLite for simple cases
  - External APIs (payment gateways, email): mock all responses
  - Event bus: capture events for assertion, don't actually emit
  
  Generate complete, runnable test files with:
  - Arrange-Act-Assert pattern
  - Descriptive test names (given/when/then)
  - Setup/teardown fixtures (pytest) or before/after (Jest)
  - Coverage for success, validation errors, not-found, conflicts
  - N+1 query checks where applicable

user_message_template: |
  Generate {{test_type}} test for: {{target}}
  
  Framework: {{framework}}
  Package: {{package}}
  
  {% if mock_dependencies %}
  Mock dependencies: {{mock_dependencies | join(', ')}}
  {% endif %}
  
  Context:
  {{context_description}}
  
  Expected behaviors:
  {{expected_behaviors}}

output_format: |
  {% if framework == 'pytest' %}
  ```python
  # packages/agentic_event_orchestrator/src/__tests__/{{target | lower }}.test.py
  import pytest
  from httpx import AsyncClient, ASGITransport
  from {{target}} import {{target}}_function  # adjust import
  
  @pytest.mark.asyncio
  async def test_{{target}}_success():
      # Arrange
      input_data = {...}
      expected = {...}
      
      # Act
      result = await {{target}}_function(input_data)
      
      # Assert
      assert result["status"] == "success"
      assert result["data"]["id"] is not None
  
  @pytest.mark.asyncio
  async def test_{{target}}_validation_error():
      # Arrange: invalid input
      invalid_input = {...}
      
      # Act & Assert
      with pytest.raises(ValidationError):
          await {{target}}_function(invalid_input)
  
  @pytest.fixture
  async def mock_llm():
      # Use respx to mock Gemini API calls
      ...
  
  if __name__ == "__main__":
      pytest.main([__file__, "-v"])
  ```
  
  **Coverage focus**: {{coverage_areas}}
  **Run command**: `cd packages/agentic_event_orchestrator && pytest src/__tests__/{{target | lower }}.test.py -v`
  
  {% elif framework == 'jest' %}
  ```typescript
  // packages/{{package}}/src/__tests__/{{target | lower }}.test.ts
  import { describe, it, expect, before, after } from '@jest/globals';
  import request from 'supertest';
  import { app } from '../index';
  
  describe('{{target}}', () => {
      it('should succeed with valid input', async () => {
          // Arrange
          const payload = {...};
          
          // Act
          const response = await request(app.server)
              .post('/api/v1/{{endpoint_path}}')
              .send(payload)
              .expect(200);
          
          // Assert
          expect(response.body.success).toBe(true);
          expect(response.body.data).toHaveProperty('id');
      });
      
      it('should return 400 for validation error', async () => {
          const invalid = {...};
          await request(app.server)
              .post('/api/v1/{{endpoint_path}}')
              .send(invalid)
              .expect(400);
      });
      
      it('should emit domain event on success', async () => {
          // Capture event bus emissions
          ...
      });
  });
  ```
  
  **Coverage focus**: {{coverage_areas}}
  **Run command**: `pnpm --filter {{package}} test -- {{target | lower }}.test.ts`
  
  {% endif %}
  
  ---
  **TDD Checklist**:
  - [ ] Test fails before implementation (RED)
  - [ ] Test passes after minimal change (GREEN)
  - [ ] No hardcoded secrets in mocks
  - [ ] LLM/API calls fully mocked (respx/axios-mock-adapter)
  - [ ] Database cleanup in afterEach/teardown
  - [ ] Error paths covered (validation, not-found, conflicts)

---
# End of skill definition
