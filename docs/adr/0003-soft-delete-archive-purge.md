# 0003. Soft delete, archive and purge

- Status: Accepted
- Date: 2026-10-30
- Decisions: D-07, D-08, D-09, D-10

## Context

Routes map DELETE to archive, `:undelete` to unarchive and `:purge` to a hard delete. Today's legacy archive is a copy that leaves the original readable: Mongo `archive()` copies the document into `{collection}_archive` and leaves the original in place, and Couchbase writes a separate `<Type>Archived` document. In both, `unarchive()` deletes the copy. That model cannot drive offline sync, because the original row never leaves the device.

## Decision

- DELETE (archive) sets `deleted_at` (epoch seconds per ADR 0002) and keeps the row.
- Every read excludes rows with `deleted_at` set unless the caller asks for them (AIP-164 `showDeleted`).
- `:undelete` clears `deleted_at`, indefinitely: there is no auto-expiry and no retention job (D-07).
- `:purge` is admin-only (D-08). It is a hard row delete with no scrub and no tombstone (D-09).
- Sync streams filter `deleted_at IS NULL`, so archive removes the row from devices and undelete brings it back. Purge relies on PowerSync's delete op. Phase 6 verifies the remove-on-transition (D-10).
- The legacy Couchbase/Mongo backend keeps its copy-based behavior behind the legacy flag and does not support offline sync. Mongo archive copies the document to `{collection}_archive` and leaves the original readable, Couchbase writes a separate `<Type>Archived` document, and unarchive deletes the copy.

## Consequences

- Purged research data cannot be recovered, which is why purge is admin-only. This is a one-way door.
- Archived rows cost storage until an admin purges them.
- The Postgres adapter and the legacy adapters behave differently on archive: after archive, the Postgres row is hidden from reads, while the legacy original stays readable. Clients must not depend on the legacy behavior.
