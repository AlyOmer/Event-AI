---
name: Event Modeler
description: Design domain events following Event-AI's event-driven architecture patterns
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: structured, comprehensive
  tone: authoritative

# Invocation
invocation:
  command: /event-model
  description: Design domain events for event-driven architecture
  parameters:
    - name: event_name
      description: Event name in snake_case (e.g., booking_created)
      type: string
      required: true
    - name: event_type
      description: Category/prefix (booking, payment, vendor, event, review, ai)
      type: string
      required: true
    - name: description
      description: What happened and why
      type: string
      required: true
    - name: producer
      description: Service that emits this event
      type: enum
      values: [backend, ai, user, admin, vendor]
      required: true
    - name: payload_fields
      description: Data included in the event
      type: array
      items:
        type: object
        properties:
          name: string
          type: string
          required: boolean
          description: string
      required: true
    - name: consumers
      description: Services/components that should react
      type: array
      items:
        type: string
      required: true

# Documentation
documentation:
  description: |
    Event Modeler designs domain events following Event-AI's event-driven architecture.
    
    Event Envelope Standard (ALL events):
    ```json
    {
      "eventId": "uuid",
      "eventType": "booking.created",
      "timestamp": "2025-04-07T10:30:00Z",
      "version": 1,
      "source": "backend",
      "correlationId": "trace-id",
      "data": { ...payload fields... }
    }
    ```
    
    Principles:
    - Events are FACTS, not commands (booking.created, not create.booking)
    - At-least-once delivery with idempotent consumers
    - Events persisted to domain_events table for audit
    - Real-time to frontends via SSE/WebSocket
  
  examples:
    - title: Create booking.created event
      command: /event-model --event_name="booking_created" --event_type="booking" --description="Customer created a new booking" --producer="backend" --payload=[{...}] --consumers=["AI Service","Email Service","Vendor Portal"]

# Skill Content
system_prompt: |
  You are an event modeling expert for Event-AI's event-driven architecture.
  
  Critical Rules:
  1. Event names are PAST TENSE facts: resource.action (e.g., booking.confirmed)
  2. Include eventId, eventType, timestamp, version, source, correlationId in envelope
  3. Producers emit events AFTER transaction commit (eventual consistency)
  4. Consumers MUST be idempotent—use eventId for deduplication
  5. Critical events go to domain_events table (bookings, payments, events)
  6. Real-time frontend updates via SSE/WebSocket subscriptions
  
  Event Design Checklist:
  - ✅ Name follows resource.action pattern
  - ✅ Includes correlationId for tracing
  - ✅ Payload includes all data consumers need (no secondary fetch)
  - ✅ Versioned (start at 1, increment on breaking changes)
  - ✅ Producer/consumers documented
  - ✅ Idempotency strategy defined (which fields prevent duplicate processing?)
  
  Generate complete event definition including:
  - Event envelope schema (Prisma model)
  - Payload data model (Pydantic/Prisma)
  - Consumer registration (which services subscribe)
  - SSE channel mapping

user_message_template: |
  Design domain event: {{event_name}}
  
  Type: {{event_type}}
  Description: {{description}}
  
  Producer: {{producer}}
  Consumers: {{consumers | join(', ')}}
  
  Payload fields:
  {% for field in payload_fields %}
  - {{field.name}} ({{field.type}}): {{field.description}} {% if field.required %}**required**{% endif %}
  {% endfor %}

output_format: |
  ```prisma
  // packages/backend/prisma/models/DomainEvent.prisma (new table entry)
  model DomainEvent {
    eventId        String   @id @map("event_id")
    eventType      String   @map("event_type") @index
    timestamp      DateTime @default(now()) @map("timestamp") @db.Timestamptz()
    version        Int      @default(1) @map("version")
    source         String   @map("source")
    correlationId  String   @map("correlation_id") @index
    payload        Json     @map("payload") @db.JsonB
    processedAt    DateTime? @map("processed_at")
    deadLetter     Boolean  @default(false) @map("dead_letter")
    
    @@map("domain_events")
    @@index([eventType, timestamp])
    @@index([correlationId])
  }
  ```
  
  ```python
  # Event payload schema (AI service)
  from pydantic import BaseModel, Field
  from typing import Optional, List
  
  class {{event_name | pascalcase}}Payload(BaseModel):
      {% for field in payload_fields %}
      {{field.name}}: {{field.type | map_pydantic_type}} = Field(..., description="{{field.description}}")
      {% endfor %}
      
      class Config:
          extra = "forbid"  # strict validation
  
  class {{event_name | pascalcase}}Envelope(BaseModel):
      eventId: str = Field(default_factory=lambda: str(uuid4()))
      eventType: str = "{{event_name | kebabcase}}"
      timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
      version: int = 1
      source: str = "{{producer}}"
      correlationId: str
      data: {{event_name | pascalcase}}Payload
  ```
  
  ---
  
  **Consumer Registrations**:
  {% for consumer in consumers %}
  - **{{consumer}}**: `packages/{{consumer | lower}}/src/consumers/{{event_name | lower}}.consumer.ts/py`
    ```python
    @event_handler(event_type="{{event_name | kebabcase}}")
    async def handle_{{event_name }}_event(envelope: {{event_name | pascalcase}}Envelope):
        # Idempotency check: skip if eventId already processed
        if await is_already_processed(envelope.eventId):
            return
        
        # Business logic
        await process_{{event_name }}(envelope.data)
        
        # Mark as processed
        await mark_event_processed(envelope.eventId)
    ```
  {% endfor %}
  
  **SSE Channels**:
  - Frontend subscription: `/api/v1/events/stream?eventType={{event_type | kebabcase}}`
  - Event bus routing: `event_bus.emit(envelope.eventType, envelope.dict())`
  
  ---
  
  **Testing Requirements**:
  - Unit test for payload validation (Pydantic/Zod)
  - Integration test for at-least-once delivery
  - Consumer idempotency test (duplicate event should not double-process)
  - Dead-letter routing test for failures
  
  **Rollback Strategy**:
  - If consumer breaks, events back up in domain_events table
  - Resume from last successful eventId (store checkpoint in consumer_state table)
  - Manual replay possible via `replay_events(event_type, from_event_id)`

---
# End of skill definition
