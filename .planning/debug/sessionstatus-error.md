---
status: resolved
trigger: UndefinedObjectError type "sessionstatus" does not exist
created: 2026-04-15
updated: 2026-04-15
---

<focus>
hypothesis: SQLModel handles sa_column=SAEnum(...) but at the Pydantic level continues passing actual enum instances to asyncpg, which tries to map it against non-existent native enums.
next_action: Verify server stability after string conversion.
</focus>

## Root Cause
Despite `native_enum=False` in `SAEnum`, asyncpg receives Enum objects pushed down from SQLModel/Pydantic validation layers instead of native strings. Postgres then crashes trying to search for the namespace of the Enum (`sessionstatus`).

## Fix
Change the SQLModel schema annotation strictly to `str` while injecting `.value` for enumeration defaults (`default=SessionStatus.active.value`, `status: str = Field(...)`). This forces pure python strings strictly through the system stack.
