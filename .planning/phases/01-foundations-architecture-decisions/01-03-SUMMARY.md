---
phase: 01-foundations-architecture-decisions
plan: 03
subsystem: api
tags: [mongo, error-handling, logging, fastapi, python]
requires: []
provides:
  - "object_id_or_none(value) -> ObjectId | None in mongo_base_repository"
  - "Catch-all Exception handler in register_exception_handlers: logged generic 500 INTERNAL"
  - "backend/api/tests/test_repository_errors.py (malformed-id and outage tests over mongomock)"
affects: [01-04 participant repo, 01-05 base repo and handlers, Phase 9 mobile retry logic]
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
plan_head_before: 9523f0cd44ffaf29820f85f5e37a71656f52dd0a
plan_head_after: 7aa951a5fae7ad0c9763273284e71e101470aebc
tech-stack:
  added: []
  patterns: ["Malformed Mongo id means not-found; datastore errors always propagate to the API catch-all"]
key-files:
  created:
    - backend/api/tests/test_repository_errors.py
  modified:
    - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py
    - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_device_repository.py
    - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_participant_repository.py
    - backend/api/src/openwellness_api/errors/handlers.py
key-decisions:
  - "500 body is the fixed string 'Internal error.'; exception type, method and path are logged with exc_info, never the response"
  - "Couchbase and Postgres untouched: Mongo-only scope per the plan assumption"
requirements-completed: [FOUND-06]
status: complete
---

# Phase 1 Plan 03: Honest Repository Errors Summary

Malformed Mongo ids now map to not-found, and a Mongo outage surfaces as a logged 500 INTERNAL instead of a 404 or empty list.

## What changed

- `object_id_or_none` guards every `ObjectId(...)` conversion in the Mongo base, device and participant repositories.
- `MongoBaseRepository.get_by_id` lost its broad `except` and `print` calls; `unarchive` lost its silent catch. `save` and `delete` raise `EntityNotFoundException` for a malformed id (404 at the API). `unarchive`, device-by-participant and participant-by-study lookups treat a malformed id as no rows.
- `register_exception_handlers` gained a final `Exception` handler that logs `Unhandled <Type> on <METHOD> <path>` at ERROR with the traceback and returns a generic 500 envelope.

## TDD record

- Task 1 (tracer) was test-first: the outage tests (get and list) failed at HEAD (`404 == 500`; list returned a non-JSON 500), then passed after the change. The tracer's `<verify>` was re-run end to end before Task 2 (11 passed).
- Task 2 RED (`d5ca764`): 5 target tests failed on the planned behavior (`bson.errors.InvalidId` escaping from save, delete, device and participant lookups; `DID NOT RAISE ServerSelectionTimeoutError` for unarchive/delete outage). Semantic assessment: each failed for the intended reason, not an import or fixture fault. The plan is `type: execute`, so `gsd_run check tdd-red-evidence` was not run.
- Task 2 GREEN (`7aa951a`): all behavior cases pass. No refactor commit.

## Verification

- api 202 passed, core 83 passed, scheduler 4 passed; pyright 0 errors (12 pre-existing warnings).
- `grep -rn 'print(' backend/{core,api,scheduler}/src` returns 0 matches (baseline 3); no broad except in `mongo_base_repository.py` (baseline 2); no `traceback` import.

## Commits

- `4fa9d06` fix(01-03): malformed id is 404, datastore outage is a logged 500
- `d5ca764` test(01-03): add failing tests for guarded Mongo id conversions
- `7aa951a` feat(01-03): guard every Mongo id conversion

## Deviations from Plan

None - plan executed as written.

## Known Stubs

None.

## Threat Flags

None. T-01-08 to T-01-11 are mitigated as planned (test asserts the driver text is absent from the response body).

## Notes for later plans

- The pre-existing `_domain_exception` handler still returns `str(exc.message)` in a 500 body; out of scope here.
- Plans 01-04 and 01-05 edit `mongo_participant_repository.py`, `mongo_base_repository.py` and `handlers.py` after this plan.

## Self-Check: PASSED

Files exist and commits `4fa9d06`, `d5ca764`, `7aa951a` are ancestors of HEAD.
