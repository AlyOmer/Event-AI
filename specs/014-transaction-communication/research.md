# Research: Transaction & Communication System

## Decision: Backend Technology Stack
**Rationale**: Following the constitution mandate for Python backend architecture, using FastAPI for high-performance async API development, SQLModel for ORM with SQLAlchemy core and Pydantic validation, and asyncpg for async PostgreSQL connectivity. This aligns with the established stack and provides proven patterns for building scalable REST APIs.

**Alternatives considered**:
- Node.js/Fastify: Rejected due to constitution mandate switching to Python
- Django: Considered but rejected as FastAPI provides better performance for API-first applications and aligns better with microservices/event-driven architecture
- Flask: Rejected as FastAPI provides built-in async support, automatic API documentation, and better performance

## Decision: Event-Driven Architecture Implementation
**Rationale**: Implementing in-process event emitter with FastAPI background tasks for Phase 1, with migration path to NATS JetStream for Phase 2 scaling. This follows the constitution's event-driven architecture guidelines and provides a clear evolution path.

**Alternatives considered**:
- Immediate NATS JetStream: Rejected as over-engineering for initial phase; in-process solution is simpler to develop and test
- REST polling: Rejected as violates constitution's real-time push requirement and creates unnecessary load
- Webhooks only: Rejected as doesn't provide real-time updates to connected clients

## Decision: Database Modeling Approach
**Rationale**: Using SQLModel for unified database models that serve as both ORM models and Pydantic validation schemas, eliminating duplication and ensuring consistency between database layer and API contracts.

**Alternatives considered**:
- Separate SQLAlchemy models and Pydantic schemas: Rejected as creates duplication and potential inconsistency
- Raw SQL queries: Rejected as loses ORM benefits and increases boilerplate
- Alternative ORMs (TortoiseORM, Peewee): Rejected as SQLModel has better FastAPI integration and aligns with constitution

## Decision: Real-Time Communication Mechanism
**Rationale**: Using Server-Sent Events (SSE) via sse-starlette for real-time updates to clients, as it provides efficient HTTP-based streaming with automatic reconnection handling and broad browser support.

**Alternatives considered**:
- WebSockets: Considered but SSE chosen for simpler implementation and adequate for server-to-client streaming use case
- Polling: Rejected as violates performance goals and creates unnecessary load
- Webhooks: Rejected as doesn't provide real-time browser updates

## Decision: Notification Delivery System
**Rationale**: Abstracting notification delivery through a service layer that can integrate with multiple providers (email services like SendGrid, SMS providers like Twilio, and in-app notifications) while maintaining a consistent interface for booking lifecycle events.

**Alternatives considered**:
- Direct provider integrations in booking flow: Rejected as creates tight coupling and makes testing difficult
- Single notification channel: Rejected as doesn't meet requirement for email/in-app/SMS flexibility
- Third-party notification services (like Courier, Novu): Rejected as adds external dependency and cost when direct provider integration is sufficient for scope

## Decision: Payment Processing Integration
**Rationale**: Integrating with established payment gateways (Stripe, PayPal) through a service layer that handles secure payment processing, webhook handling for asynchronous payment confirmation, and refund processing according to vendor policies.

**Alternatives considered**:
- Custom payment processing: Rejected as violates security best practices and compliance requirements
- Storing payment information: Rejected as violates PCI DSS requirements and security standards
- Single payment provider: Rejected as limits vendor flexibility and creates vendor lock-in