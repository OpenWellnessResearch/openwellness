# 0001. Primary key format

- Status: Accepted
- Date: 2026-10-30
- Decisions: D-11

## Context

PowerSync syncs rows by a text primary key, and offline clients create rows before they ever reach the server, so ids must be generatable on the client. The domain already does this on the server side: `BaseEntity.id` defaults to `str(uuid4())`. Legacy backends use other formats: Mongo uses 24-hex ObjectIds and Couchbase uses Sync Gateway document ids. Python 3.12 has no stdlib `uuid7`.

## Decision

- Every primary key is a text UUID generated with stdlib `uuid.uuid4()`.
- The repository boundary accepts any valid UUID, of any version, by parsing with `uuid.UUID`. A malformed id is treated as not found (404, never 500).
- Clients may supply the id on create. The offline write path in Phase 7 relies on this.
- Legacy Couchbase/Mongo backends keep their own id formats behind the legacy datastore flag.
- UUIDv4 over UUIDv7: it needs only the standard library and does not depend on device clocks, which are unreliable on phones.

## Consequences

- Random ids have worse index write locality than time-ordered ids.
- UUIDv7 is the upgrade path if the Phase 7 wearable load test shows index write pressure. Switching costs nothing for existing rows because validation is version-agnostic.
- This is a one-way door: the column type and client-generated ids are baked into the Postgres schema and the mobile app.
