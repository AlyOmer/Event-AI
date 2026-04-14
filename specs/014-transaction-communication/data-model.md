# Data Model: Transaction & Communication System

## Entities

### Booking
Represents a user's reservation for an event or service from a vendor.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier for the booking |
| user_id | UUID (FK) | Reference to the user who made the booking |
| vendor_id | UUID (FK) | Reference to the vendor providing the event/service |
| event_id | UUID (FK) | Reference to the specific event being booked |
| service_id | UUID (FK, nullable) | Reference to specific service within event (if applicable) |
| quantity | Integer | Number of items/tickets booked |
| total_amount | Decimal | Total cost of the booking |
| currency | String (3) | Currency code (e.g., USD, PKR) |
| status | Enum | Booking status: pending, confirmed, modified, cancelled, refunded |
| booking_date | DateTime | When the booking was created/modified |
| start_date | DateTime | Event/service start time |
| end_date | DateTime | Event/service end time |
| special_requests | Text (nullable) | Any special requests from the user |
| payment_id | String (nullable) | Reference to payment transaction ID |
| metadata | JSONB | Additional flexible metadata |

**Constraints**:
- user_id, vendor_id, event_id are required
- Quantity must be >= 1
- Total_amount must be >= 0
- Status transitions follow defined workflow
- One booking per user/event/service combination (unless multiple quantities allowed)

### BookingEvent
Represents a domain event triggered by booking lifecycle actions.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier for the event |
| booking_id | UUID (FK) | Reference to the associated booking |
| event_type | Enum | Type of booking event: created, modified, cancelled |
| timestamp | DateTime | When the event occurred |
| version | Integer | Event schema version (for evolution) |
| source | String | Source service generating the event (typically "backend") |
| correlation_id | UUID | Request trace ID for distributed tracing |
| data | JSONB | Event payload containing relevant booking data |

**Constraints**:
- booking_id is required
- event_type must be one of defined values
- timestamp defaults to creation time
- data must contain at least booking ID and timestamp

### Notification
Represents a message sent to a user about a booking lifecycle event.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier for the notification |
| booking_id | UUID (FK) | Reference to the associated booking |
| user_id | UUID (FK) | Reference to the recipient user |
| event_type | Enum | Type of booking event that triggered notification |
| channel | Enum | Delivery channel: email, in_app, sms |
| template_id | String | Identifier for notification template used |
| subject | String | Notification subject/title |
| content | Text | Notification body/content |
| status | Enum | Delivery status: pending, sent, delivered, failed |
| sent_at | DateTime (nullable) | When notification was sent |
| delivered_at | DateTime (nullable) | When notification was delivered |
| failure_reason | String (nullable) | Reason for delivery failure (if applicable) |
| metadata | JSONB | Additional flexible metadata |

**Constraints**:
- booking_id, user_id, event_type, channel are required
- Status follows delivery lifecycle
- Template references must exist in notification template system

### RealTimeConnection
Represents an active connection for real-time updates.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Unique identifier for the connection |
| user_id | UUID (FK) | Reference to the connected user |
| connection_id | String | Unique connection identifier (e.g., session ID) |
| connected_at | DateTime | When connection was established |
| last_ping | DateTime | Last heartbeat/received message |
| user_agent | String (nullable) | Client user agent string |
| ip_address | String (nullable) | Client IP address |
| is_active | Boolean | Whether connection is currently active |
| metadata | JSONB | Additional connection metadata |

**Constraints**:
- user_id and connection_id are required
- connection_id must be unique per user
- connected_at defaults to creation time
- last_ping updates on heartbeat/message receipt

## Relationships

- Booking belongs to User (many-to-one)
- Booking belongs to Vendor (many-to-one)
- Booking belongs to Event (many-to-one)
- Booking may belong to Service (many-to-one, optional)
- BookingEvent belongs to Booking (many-to-one)
- Notification belongs to Booking (many-to-one)
- Notification belongs to User (many-to-one)
- RealTimeConnection belongs to User (many-to-one)

## State Transitions

### Booking Status Flow
```
pending → [confirmed] → [modified] → [cancelled]
                           ↓
                        [refunded] (from cancelled or modified)
```

**Rules**:
- Only pending bookings can be confirmed
- Confirmed bookings can be modified (subject to vendor policies)
- Modified bookings maintain confirmed status
- Confirmed or modified bookings can be cancelled (subject to vendor policies)
- Cancelled bookings may be refunded based on timing and vendor policy

### Notification Delivery Flow
```
pending → sent → delivered
                    ↓
                 failed
```

**Rules**:
- Notifications start in pending state
- Sent when dispatched to delivery provider
- Delivered when provider confirms delivery
- Failed if provider rejects or delivery fails after retries

### Connection State Flow
```
created → active → [idle] → disconnected
                           ↓
                        timed_out
```

**Rules**:
- Connections start in created state
- Become active upon first successful handshake
- May become idle after period of inactivity
- Disconnected manually or due to timeout/error