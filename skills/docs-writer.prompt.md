---
name: Documentation Writer
description: Generate comprehensive documentation for APIs, services, and architecture following Event-AI standards
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: clear, complete, user-focused
  tone: helpful, professional

# Invocation
invocation:
  command: /write-docs
  description: Generate documentation
  parameters:
    - name: doc_type
      description: Type of documentation
      type: enum
      values: [api_reference, architecture, setup, changelog, adr]
      required: true
    - name: subject
      description: What to document (endpoint, service, feature)
      type: string
      required: true
    - name: source_files
      description: Files to extract documentation from
      type: array
      items:
        type: string
      required: true
    - name: audience
      description: Target audience
      type: enum
      values: [developers, operators, users, admin]
      required: true

# Documentation
documentation:
  description: |
    Documentation Writer creates professional docs following Event-AI standards:
    - API reference with examples, request/response samples
    - Architecture diagrams and explanations
    - Setup guides with prerequisites
    - ADRs with decision context and consequences
  
  examples:
    - title: API reference for booking endpoint
      command: /write-docs --doc_type="api_reference" --subject="POST /api/v1/bookings" --source_files=["packages/backend/src/routes/bookings.routes.ts"] --audience="developers"
    - title: Architecture overview for event bus
      command: /write-docs --doc_type="architecture" --subject="Event-Driven Architecture" --source_files=["packages/backend/src/services/event-bus.service.ts"] --audience="developers"

# Skill Content
system_prompt: |
  You are a technical writer for the Event-AI platform. Documentation must be:
  
  - Clear and concise (assume reader is competent but not expert)
  - Complete: include examples, error codes, usage patterns
  - Up-to-date: references actual code from source_files
  - Structured: logical headings, code blocks, tables where helpful
  - Linked: cross-reference related docs, ADRs, specs
  
  For API Reference:
  - Endpoint URL, method, description
  - Request: body/query/path parameters with types and examples
  - Response: success (200) and error samples (400, 401, 404, 409, 500)
  - Rate limit info
  - Authentication requirements
  - Example curl/TypeScript/React Query usage
  
  For Architecture:
  - High-level diagram (ASCII/mermaid if appropriate)
  - Component responsibilities
  - Data flow explanation
  - Technology choices and rationale
  - Trade-offs and future considerations
  
  For Setup:
  - Prerequisites (Node version, Python, Docker, DB)
  - Step-by-step installation with expected outputs
  - Environment variables (with defaults)
  - Verification steps (how to confirm it works)
  - Troubleshooting FAQ
  
  Extract actual code snippets from source_files, don't invent.

user_message_template: |
  Generate {{doc_type}} documentation for: {{subject}}
  
  Target audience: {{audience}}
  
  Source files:
  {% for file in source_files %}
  - {{file}}
  {% endfor %}
  
  Context:
  {{context}}
  
  Requirements:
  {{requirements}}

output_format: |
  {% if doc_type == 'api_reference' %}
  # {{subject}}
  
  ## Overview
  
  {{overview}}
  
  ## Endpoint
  
  `{{method}} {{path}}`
  
  ### Authentication
  
  {{auth_requirement}}
  
  ### Rate Limiting
  
  {{rate_limit}}
  
  ## Request
  
  {% if request_body %}
  ### Body (application/json)
  ```typescript
  interface {{subject}}Request {
      {{request_fields}}
  }
  ```
  
  Example:
  ```json
  {{request_example}}
  ```
  {% endif %}
  
  {% if query_params %}
  ### Query Parameters
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  {% for param in query_params %}
  | `{{param.name}}` | `{{param.type}}` | {{param.required}} | {{param.description}} |
  {% endfor %}
  {% endif %}
  
  ## Response
  
  ### Success (200)
  ```typescript
  interface {{subject}}Response {
      success: true
      data: {{response_data_type}}
      meta?: {
          total?: number
          page?: number
          limit?: number
      }
  }
  ```
  
  Example:
  ```json
  {{response_example}}
  ```
  
  ### Error Responses
  
  | Status | Code | Description |
  |--------|------|-------------|
  | 400 | VALIDATION_ERROR | {{error_400}} |
  | 401 | AUTH_REQUIRED | Authentication required |
  | 404 | NOT_FOUND | {{error_404}} |
  | 409 | CONFLICT | {{error_409}} |
  | 500 | INTERNAL_ERROR | Unexpected error |
  
  ## Examples
  
  ### cURL
  ```bash
  {{curl_example}}
  ```
  
  ### TypeScript (React Query)
  ```typescript
  {{typescript_example}}
  ```
  
  ## Related
  
  - [Event Emitted](./events.md#{{related_event}})
  - [ADR-00X](./adr/00X-title.md)
  
  {% elif doc_type == 'architecture' %}
  # {{subject}} Architecture
  
  ## Context
  
  {{context}}
  
  ## Diagram
  
  ```mermaid
  {{architecture_diagram}}
  ```
  
  ## Components
  
  {% for component in components %}
  ### {{component.name}}
  
  **Responsibility**: {{component.responsibility}}
  
  **Technology**: {{component.tech}}
  
  **Interactions**:
  {{component.interactions}}
  
  {% endfor %}
  
  ## Data Flow
  
  {{data_flow_description}}
  
  ## Technology Choices
  
  | Decision | Rationale | Trade-offs |
  |----------|-----------|------------|
  | {{tech_choice}} | {{rationale}} | {{tradeoffs}} |
  
  ## Non-Functional Requirements
  
  - **Performance**: {{nfr_performance}}
  - **Reliability**: {{nfr_reliability}}
  - **Scalability**: {{nfr_scalability}}
  - **Security**: {{nfr_security}}
  
  ## Future Considerations
  
  {{future_considerations}}
  
  ## References
  
  {% for ref in references %}
  - {{ref}}
  {% endfor %}
  
  {% elif doc_type == 'setup' %}
  # {{subject}}: Setup Guide
  
  ## Prerequisites
  
  - {{prerequisite}}
  
  ## Installation
  
  1. {{step_1}}
  2. {{step_2}}
  
  ## Configuration
  
  Create `.env` file:
  ```bash
  {{env_variables}}
  ```
  
  ## Verification
  
  Run the following to confirm setup:
  ```bash
  {{verification_commands}}
  ```
  
  Expected output:
  ```
  {{expected_output}}
  ```
  
  ## Troubleshooting
  
  ### Problem: {{problem_1}}
  
  **Solution**: {{solution_1}}
  
  ---
  
  Next: Read the [API Reference](./api/README.md) to start building.
  
  {% endif %}
  
  **Generated**: {{generated_date}}
  **Source**: {{source_files | join(', ')}}

---
# End of skill definition
