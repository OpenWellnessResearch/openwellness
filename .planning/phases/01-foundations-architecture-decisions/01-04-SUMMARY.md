---
phase: 01-foundations-architecture-decisions
plan: 04
subsystem: domain
tags: [mongo, objectid, participant, dependency-rule, fastapi]

requires:
  - phase: 01-foundations-architecture-decisions
    provides: "object_id_or_none and honest repository errors (plan 01-03)"
provides:
  - "datastore-free Participant entity with str ids"
  - "MongoParticipantRepository._to_doc owning ObjectId coercion"
  - "API source with no bson imports"
affects: [postgres-adapters, powersync-schema]

actuals:
  tokens: 4500
  tasks: 2
  commits: 2
plan_head_before: e7104a7e291974179ae3c8a5c66d788b373c9a2f
plan_head_after: e4bf0d7930137ecf8b0ac46d4dd6a8f05c333ef9

tech-stack:
  added: []
  patterns: ["adapter owns datastore id coercion in _to_doc; domain carries text ids"]

key-files:
  created: [backend/api/tests/test_participant_ids.py]
  modified:
    - backend/core/src/openwellness_core/domain/models/participant.py
    - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_participant_repository.py
    - backend/api/src/openwellness_api/resources/participant.py
    - backend/api/src/openwellness_api/schemas/_base.py
    - backend/api/src/openwellness_api/schemas/participant.py
    - backend/api/tests/conftest.py

key-decisions:
  - "Empty or malformed studyId is refused at the Mongo adapter (EntityNotFoundException -> 404) rather than stored as null"

requirements-completed: [FOUND-04]

coverage:
  - id: D1
    description: "Participant domain entity uses str ids; no bson/pymongo/couchbase/redis/sqlalchemy/psycopg import under domain/ or application/"
    requirement: FOUND-04
    verification:
      - kind: other
        ref: "grep import gate over core domain and application prints domain-clean"
        status: pass
    human_judgment: false
  - id: D2
    description: "Mongo adapter stores studyId/userId/assignedCoachId as ObjectId, returns strings on the wire, rejects malformed or empty ids"
    requirement: FOUND-04
    verification:
      - kind: integration
        ref: "backend/api/tests/test_participant_ids.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "No bson import anywhere in openwellness_api source; full backend suites and pyright green"
    requirement: FOUND-04
    verification:
      - kind: unit
        ref: "uv run --frozen pytest (api 209, core 83, scheduler 4) and pyright 0 errors"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-30
status: complete
---

# Phase 1 Plan 04: Participant String Ids Summary

**Participant domain carries plain str ids; the Mongo adapter coerces to ObjectId on every write, and the API no longer imports bson.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-10-30T13:11:04Z
- **Tasks:** 2
- **Files modified:** 7 (1 created)

## Accomplishments
- `Participant.assigned_coach_id`/`user_id` are `Optional[str]`, `study_id` is `str = ""`; domain has no driver imports.
- `MongoParticipantRepository._to_doc` stores the three reference ids as ObjectId (on-disk format preserved) and raises `EntityNotFoundException` for malformed ids or an empty `study_id`, so the old random-ObjectId default can never reach disk.
- Participant router lost `_coerce_object_ids` and bson; `schemas/_base.py` lost unused `ObjectIdField`.
- 7 end-to-end tests over mongomock cover on-disk ObjectId storage, get/list, cross-study 404, malformed ids, and the empty-study refusal.

## Task Commits

1. **Task 1: Participant string ids end to end** - `950647d` (feat)
2. **Task 2: Remove remaining datastore types from API surface** - `e4bf0d7` (refactor)

## Decisions Made
- Required `studyId` is refused when empty; optional references with falsy values become None.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. pyright reports 0 errors (12 pre-existing warnings).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Domain is ready for Postgres text-id adapters (Phases 4/5). Other entities with ObjectId-typed fields were out of scope for this plan.

## Self-Check: PASSED
- Created/modified files exist; commits 950647d and e4bf0d7 on branch; acceptance greps (`_coerce_object_ids` = 0, `ObjectIdField` = 0, bson in api/src = 0, conftest arg-type ignores 2 -> 0) pass.

---
*Phase: 01-foundations-architecture-decisions*
*Completed: 2026-10-30*
