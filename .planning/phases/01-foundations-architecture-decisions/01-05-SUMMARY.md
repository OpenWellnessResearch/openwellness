---
phase: 01-foundations-architecture-decisions
plan: 05
subsystem: auth
tags: [repository-port, mongo, fastapi, error-handling, anti-enumeration]
status: complete

requires:
  - phase: 01-foundations-architecture-decisions
    provides: "01-03 guarded id conversion and catch-all handler; 01-04 prior wave"
provides:
  - "UserRepository.get_by_email port method and Mongo implementation"
  - "DuplicateEntityException (application layer, re-exported from adapters.exceptions)"
  - "Mongo create/save translate DuplicateKeyError into DuplicateEntityException"
  - "409 ALREADY_EXISTS handler for duplicate writes"
affects: [phase-02-auth-enforcement, phase-04-postgres-adapter]

actuals:
  tokens: 6500
  tasks: 3
  commits: 5
plan_head_before: c24d2c6cb2006ebd5cec467e623b439dba292a88
plan_head_after: 7a9a2c3f729f62adf690e634b0c3f6c12b937cf0

tech-stack:
  added: []
  patterns:
    - "Driver errors translated at the adapter boundary into application-layer exceptions that the API maps"
    - "Datastore query dialect (Mongo dict) stays inside the adapter; ports expose intent-named methods"

key-files:
  created: []
  modified:
    - backend/core/src/openwellness_core/application/repositories/user_repository.py
    - backend/core/src/openwellness_core/application/exceptions.py
    - backend/core/src/openwellness_core/adapters/exceptions.py
    - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_user_repository.py
    - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py
    - backend/api/src/openwellness_api/auth/service.py
    - backend/api/src/openwellness_api/errors/handlers.py
    - backend/api/tests/conftest.py
    - backend/api/tests/test_auth_service.py
    - backend/api/tests/test_repository_errors.py

key-decisions:
  - "DuplicateEntityException follows the LimitExceededException placement (defined in application, re-exported by adapters.exceptions, Mongo adapter imports it from adapters.exceptions); no convention deviation"
  - "Exception messages and the 409 body name the collection only, never the duplicated value"
  - "The 409 on duplicate-email POST /v1/users is an accepted pre-Phase-2 enumeration window (T-01-33); /v1/auth:* stays uniform 400"

requirements-completed: [FOUND-05, FOUND-06]

duration: ~25min
completed: 2026-10-30
---

# Phase 1 Plan 05: Users-by-email port and duplicate-key translation Summary

AuthService now finds users through `UserRepository.get_by_email` and no longer imports pymongo; Mongo unique-index collisions cross the adapter boundary as `DuplicateEntityException` and map to 409 ALREADY_EXISTS (registration keeps its uniform 400).

## Accomplishments

- Task 1 (tracer): `get_by_email` added as an abstract port method, implemented in `MongoUserRepository` by delegating to `get_by_query({"email": ...})` inside the adapter. Both service lookups (`send_login_code`, `_eligible_registration_target`) use it; the three-lookup shape is unchanged and the recording-repo test now asserts `("get_by_id", "get_by_email")`. Test fakes updated. Tracer verified end to end (52 auth/CRUD tests green) before expanding.
- Task 2 (TDD): `DuplicateEntityException` in `application/exceptions.py`, re-exported in `adapters.exceptions.__all__`, documented on the `UserRepository` docstring. `MongoBaseRepository.create`/`save` catch `DuplicateKeyError` and raise it `from exc` with a collection-only message. `AuthService` catches it in `verify_registration_code` and still raises `invalid_code()`.
- Task 3 (TDD): handler for `DuplicateEntityException` registered before the catch-all returns 409 ALREADY_EXISTS with a generic message; the docstring records the enumeration window. Proven end to end through a real `MongoUserRepository` over mongomock with a unique email index.

## TDD

- RED (Task 2): `test_create_duplicate_email_raises_duplicate_entity`, `test_save_to_existing_email_raises_duplicate_entity`, and the updated `test_registration_email_collision_is_uniform_400` failed on the planned assertion (raw pymongo `DuplicateKeyError` surfaced instead of `DuplicateEntityException`). The empty exception class was committed with the RED tests as scaffolding so the failure is an assertion, not an ImportError. Semantic assessment: targets executed and failed for the intended reason. `gsd_run check tdd-red-evidence` was not run: pytest output is not a supported report format, and a JUnit-XML attempt hung; evidence is the pytest failure output only.
- RED (Task 3): `test_duplicate_email_post_returns_409_without_the_email` failed with the unhandled `DuplicateEntityException` propagating (no handler).
- GREEN: commits 6e66897 and 7a9a2c3. REFACTOR: none needed.

## Task Commits

| Task | Commit | Message |
| ---- | ------ | ------- |
| 1 | 0038699 | feat(01-05): look users up by email through UserRepository.get_by_email |
| 2 RED | 0ea45a7 | test(01-05): add failing tests for duplicate-key translation |
| 2 GREEN | 6e66897 | feat(01-05): translate duplicate-key errors into DuplicateEntityException |
| 3 RED | 9c119e6 | test(01-05): add failing test for 409 on duplicate POST /v1/users |
| 3 GREEN | 7a9a2c3 | feat(01-05): map DuplicateEntityException to 409 ALREADY_EXISTS |

## Deviations from Plan

**1. [Process] Plan commit ledger written after the first commit**
- The `gsd-plan-head-before-01-05` ledger was created right after Task 1's commit from `0038699^` (= c24d2c6, the verified pre-plan HEAD), so `commits: 5` is measured correctly.

**2. [Minor] Exception class added in the RED commit**
- Scaffolding so RED fails on assertion rather than import (see TDD above).

Otherwise the plan executed as written.

## Verification

- api 212 passed, core 83 passed, scheduler 4 passed; pyright 0 errors (12 pre-existing warnings).
- `service.py` has 0 pymongo imports and 0 `_user_repo.get_by_query`; `reexport-ok` printed; handler (line 87) precedes `exception_handler(Exception)` (line 169).

## Known Stubs

None.

## Threat Flags

None. T-01-33 (409 enumeration window on POST /v1/users) is the accepted, documented residual risk; recording it in ADR 0007 is plan 01-09's job.

## Self-Check: PASSED

All five commits (0038699, 0ea45a7, 6e66897, 9c119e6, 7a9a2c3) are ancestors of HEAD; all modified files exist.
