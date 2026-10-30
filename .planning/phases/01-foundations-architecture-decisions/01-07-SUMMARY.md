---
phase: 01-foundations-architecture-decisions
plan: 07
subsystem: docs
tags: [adr, madr, uuid, timestamps, soft-delete, jwt, ed25519, jwks]

requires:
  - phase: 01-foundations-architecture-decisions
    provides: decisions D-07 to D-14 captured in 01-CONTEXT.md
provides:
  - ADR index and format conventions at docs/adr/README.md
  - ADR 0001 primary key format (text UUIDv4, D-11)
  - ADR 0002 timestamp representation (double precision epoch, D-12)
  - ADR 0003 soft delete, archive and purge (D-07 to D-10)
  - ADR 0004 access token format (EdDSA/JWKS, D-13)
affects: [01-08, 01-09, phase-03-auth, phase-04-postgres-schema, phase-05, phase-06-powersync]

actuals:
  tokens: 4200
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns: ["Short MADR files in docs/adr/, one decision per file, index check one-liner"]

key-files:
  created:
    - docs/adr/README.md
    - docs/adr/0001-primary-key-format.md
    - docs/adr/0002-timestamp-representation.md
    - docs/adr/0003-soft-delete-archive-purge.md
    - docs/adr/0004-access-token-format.md
  modified: []

key-decisions:
  - "Primary keys are text UUIDv4 via uuid.uuid4(); validation accepts any UUID version; UUIDv7 is the upgrade path"
  - "All Postgres timestamp columns are double precision epoch seconds; wire stays RFC 3339"
  - "DELETE sets deleted_at, undelete is indefinite, purge is admin-only hard delete; streams filter deleted_at IS NULL"
  - "Access tokens are EdDSA (Ed25519) with kid and a JWKS; separate aud=powersync token; HS256 retired; participants carry no study claim"

patterns-established:
  - "ADR index check: every numbered ADR appears once in the README index with Context/Decision/Consequences headings"

requirements-completed: [FOUND-07]

plan_head_before: 438da0eadcd369e5fc6de6ef284fb2e688587abd
plan_head_after: 823fc90b46933eb23b08042ef32a5c5c1c298c13
commits: 3

duration: 8min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 07: ADRs 0001 to 0004 Summary

**ADR directory with index plus four accepted decisions: text UUIDv4 keys, double precision epoch timestamps, deleted_at soft delete with admin-only purge, and EdDSA/JWKS access tokens**

## Performance

- **Duration:** 8 min
- **Completed:** 2026-10-30T13:08:08Z
- **Tasks:** 3
- **Files modified:** 5 (all created)

## Accomplishments
- `docs/adr/` created with a README holding the format rules, how to add an ADR, and the index.
- ADR 0002 lists exactly the 10 domain `datetime` fields, verified against source by the plan's field check.
- ADR 0004 records that participants have no study claim; the study comes from the Participant record (ADR 0007).

## Task Commits

1. **Task 1: ADR index plus ADR 0001** - `b64909b` (docs)
2. **Task 2: ADR 0002 and ADR 0003** - `8473ef3` (docs)
3. **Task 3: ADR 0004** - `823fc90` (docs)

## Files Created/Modified
- `docs/adr/README.md` - conventions and index (rows 0001 to 0004)
- `docs/adr/0001-primary-key-format.md` - D-11
- `docs/adr/0002-timestamp-representation.md` - D-12, with datetime field table
- `docs/adr/0003-soft-delete-archive-purge.md` - D-07 to D-10
- `docs/adr/0004-access-token-format.md` - D-13

## Decisions Made
None beyond recording D-07 to D-13 as specified.

## Deviations from Plan

None - plan executed exactly as written.

The tracer gate: Task 1 `<verify>` is automated-only, so it was re-run end to end before expanding and passed.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Index and format are in place for 01-08 (ADR 0005) and 01-09 (ADRs 0006, 0007), which append rows. ADR 0004 forward-references 0006 and 0007, which do not exist yet.

---
*Phase: 01-foundations-architecture-decisions*
*Completed: 2026-10-30*

## Self-Check: PASSED
