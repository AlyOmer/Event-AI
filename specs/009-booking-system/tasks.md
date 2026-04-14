# Task Specification: Booking System

**Branch**: `feature/booking-system` | **Date**: 2026-04-09 | **Spec**: [specs/booking-system/spec.md](spec.md) | **Plan**: [specs/booking-system/plan.md](plan.md)

## Task Breakdown

### Phase 1: Database & Event Bus Foundation

- [x] **1.1: Create `DomainEvent` Model**
  - **Location**: `packages/backend/src/models/domain_event.py`
  - **Action**: Add a new SQLModel representing the `domain_events` table (id, event_type, payload, user_id, etc.).
  - **Test**: None directly required for model definition.

- [x] **1.2: Add Alembic Migrations**
  - **Location**: `packages/backend/alembic/versions/`
  - **Action**: Use `alembic init` or generate a migration mapping `Booking`, `BookingMessage`, `DomainEvent` (and updating the `env.py` to include these SQLModel classes).
  - **Test**: Run `alembic upgrade head` and verify tables exist via psql or PgAdmin.

- [x] **1.3: Create Event Bus Service**
  - **Location**: `packages/backend/src/services/event_bus_service.py`
  - **Action**: Implement an async Python EventBus that can dispatch and persist `booking.*` events to the `domain_events` table asynchronously.
  - **Test**: Create a simple unit test ensuring an emitted event is written into the DB.

### Phase 2: Refactor Booking Routes & Services

- [x] **2.1: Implement JWT Auth Guards**
  - **Location**: `packages/backend/src/api/v1/bookings.py`
  - **Action**: Add `get_current_user` dependency from `auth.py` to all booking endpoints.
  - **Test**: `GET /api/v1/bookings` with no token returns 401 Unauthorized.

- [x] **2.2: Implement Availability Optimistic Locking**
  - **Location**: `packages/backend/src/models/booking.py` & `src/services/booking_service.py`
  - **Action**: Create `VendorAvailability` model. Update `create_booking` and `get_availability` methods to lock via row-level locks or precise availability checks.
  - **Test**: Write a concurrency test for booking the same service/date simultaneously; assert one returns 409 Conflict.

- [x] **2.3: Implement Status Lifecycle Validation**
  - **Location**: `packages/backend/src/services/booking_service.py`
  - **Action**: Add State Machine validation for `PATCH /{id}/status`. Only allow valid transitions (e.g., `pending` -> `confirmed` or `rejected`).
  - **Test**: Reject `pending` -> `completed` transition with 400 Bad Request.

- [x] **2.4: Integrate Domain Event Emission**
  - **Location**: `packages/backend/src/services/booking_service.py`
  - **Action**: Replace the `# Ideally, trigger "booking.*" event here` comments with actual `event_bus_service` calls upon booking creation, transition, and cancellation.
  - **Test**: Assert that after booking creation, a `DomainEvent` record exists with `type="booking.created"`.

### Phase 3: AI Service Tool Refactoring

- [x] **3.1: Clean up Anti-patterns in AI SDK Agents**
  - **Location**: `packages/agentic_event_orchestrator/agents/sdk_agents.py`
  - **Action**: Remove `nest_asyncio.apply()`, `sys.path.insert`, and module-level `load_dotenv()`.
  - **Test**: Ensure the server runs without errors when launched via PDM/Uv.

- [x] **3.2: Clean up Booking Tools**
  - **Location**: `packages/agentic_event_orchestrator/tools/booking_tools.py`
  - **Action**: Ensure dependencies are injected (Lifespan + Depends) and input data uses strict Pydantic schemas. Remove arbitrary dictionary passing.
  - **Test**: Unit test the tools with mocked endpoints via `respx`.

### Phase 4: Testing & Verification

- [x] **4.1: End-to-End Booking Tests**
  - **Location**: `packages/backend/tests/test_bookings.py`
  - **Action**: Write complete async HTTP tests using `pytest-asyncio` for the CRUD flows + state machine logic + concurrency.
  - **Test**: Target 80% coverage on `booking_service.py` and `bookings.py` routes.

- [x] **4.2: AI Booking Tool Tests**
  - **Location**: `packages/agentic_event_orchestrator/tests/test_booking_tools.py`
  - **Action**: Write mock tests using `respx` to test AI tool calls without calling external LLMs or the backend for real.
  - **Test**: `pytest tests/test_booking_tools.py` completes fully synchronously.
