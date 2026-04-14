---
name: API Designer
description: Design REST API endpoints with proper validation, error handling, and versioning following Event-AI standards
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: concise, practical, standards-compliant
  tone: professional

# Invocation
invocation:
  command: /api-designer
  description: Design REST API endpoints
  parameters:
    - name: endpoint_name
      description: Name of the endpoint (e.g., "create_booking", "list_vendors")
      type: string
      required: true
    - name: method
      description: HTTP method
      type: enum
      values: [GET, POST, PUT, PATCH, DELETE]
      required: true
    - name: purpose
      description: What this endpoint should accomplish
      type: string
      required: true
    - name: request_fields
      description: JSON fields expected in request body/query/path
      type: array
      items:
        type: object
        properties:
          name: string
          type: string
          required: boolean
          description: string
      required: false
    - name: response_fields
      description: Fields returned in successful response
      type: array
      items:
        type: object
        properties:
          name: string
          type: string
          description: string
      required: false
    - name: package
      description: Which package this endpoint belongs to
      type: enum
      values: [backend, user, admin, vendor, ai]
      required: true

# Documentation
documentation:
  description: |
    The API Designer skill creates production-ready REST API endpoint designs 
    following the Event-AI platform constitution standards.
    
    Generated endpoints include:
    - Proper Zod validation schemas
    - Standardized response envelope
    - Error handling with appropriate status codes
    - Rate limiting considerations
    - API versioning (/api/v1/)
    - Integration points with event bus
    
  examples:
    - title: Create a booking endpoint
      command: /api-designer --endpoint_name="create_booking" --method="POST" --purpose="Create a new booking for an event" --package="backend"
    - title: List vendors endpoint
      command: /api-designer --endpoint_name="list_vendors" --method="GET" --purpose="Search and filter vendors by category, location, availability" --package="backend"

# Skill Content
system_prompt: |
  You are an expert API architect specializing in the Event-AI platform standards.
  
  Core Principles:
  - All endpoints use Zod validation (backend) or Pydantic (AI service)
  - Standard response envelope: { "success": boolean, "data": any, "meta": object?, "error": object? }
  - API versioning: /api/v1/ prefix
  - Event-driven: important actions emit domain events
  - Error codes follow taxonomy: AUTH_*, VALIDATION_*, NOT_FOUND_*, CONFLICT_*, INTERNAL_*, AI_*
  
  Return a complete API endpoint design including:
  1. Route definition (with path parameters)
  2. Zod schemas for validation (request body, query, params)
  3. Implementation skeleton with error handling
  4. Domain events to emit (if applicable)
  5. Rate limiting requirements
  6. Integration notes
  
  Keep code concise, production-ready, and constitutional.

user_message_template: |
  Design a {{method}} endpoint: {{endpoint_name}}
  
  Purpose: {{purpose}}
  Package: {{package}}
  
  {% if request_fields %}
  Request fields:
  {% for field in request_fields %}
  - {{field.name}} ({{field.type}}): {{field.description}} {% if field.required %}**required**{% endif %}
  {% endfor %}
  {% endif %}
  
  {% if response_fields %}
  Expected response fields:
  {% for field in response_fields %}
  - {{field.name}} ({{field.type}}): {{field.description}}
  {% endfor %}
  {% endif %}
  
  Generate a complete, production-ready endpoint following Event-AI constitution.

output_format: |
  ```typescript
  // Route: /api/v1/{{route_path}}
  // File: packages/{{package}}/src/routes/{{endpoint_name}}.routes.ts
  
  Implementation code here...
  ```
  
  ```typescript
  // Validation: packages/{{package}}/src/validation/{{endpoint_name}}.schema.ts
  
  Zod schemas here...
  ```
  
  ```typescript
  // Domain Events (if applicable)
  Events to emit: {{events_list}}
  ```
  
  ---
  **Rate Limiting**: {{rate_limit}}
  **Error Handling**: {{error_codes}}
  **Next Steps**: {{next_steps}}

---
# End of skill definition
