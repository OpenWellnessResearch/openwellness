---
phase: 01-foundations-architecture-decisions
plan: 11
subsystem: auth
tags: [repository-port, refresh-sessions, composition-root, dependency-injector, lifespan]
status: complete

requires:
  - phase: 01-foundations-architecture-decisions
    provides: "01-06 RefreshSessionRepository port and MongoRefreshSessionRepository"
provides:
  - "RefreshSessionStore(repo=, clock=) holding the rotation policy over the port, no pymongo import"
  - "RepositoryContainer.refresh_session_collection (Object) and refresh_session (Singleton)"
  - "AuthContainer.refresh_session_repository Dependency, wired in the lifespan"
  - "Container, settings and real-lifespan boot tests"
affects: [phase-03-refresh-grace-window, phase-04-postgres-adapter]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: bd69f7906de3d8f20c82bc79dcf38cc22af3f519
plan_head_after: a346beb77528f5960ee548166d202042ea6a3bb8

key-files:
  modified:
    - backend/api/src/openwellness_api/auth/session_store.py
    - backend/api/src/openwellness_api/deps/auth_container.py
    - backend/api/src/openwellness_api/main.py
    - backend/core/src/openwellness_core/infrastructure/containers/repository_container.py
    - backend/api/tests/test_session_store.py
    - backend/api/tests/conftest.py
    - backend/api/tests/test_auth_service.py
    - backend/api/tests/test_auth_container.py

key-decisions:
  - "AuthSettings.refresh_collection is untouched; the lifespan overrides RepositoryContainer.refresh_session_collection with it before resolving the singleton, so customized deployments keep their sessions"

requirements-completed: [FOUND-05]

duration: 15min
completed: 2026-10-30
---

# Phase 1 Plan 11: RefreshSessionStore over the repository port Summary

**Single-use refresh rotation and reuse detection now run in the API over `RefreshSessionRepository`, wired from the composition root with the configurable collection name preserved, and `backend/api/src` imports no pymongo.**

## What was built

- `RefreshSessionStore` keeps the same public API and outcomes (`create`, `consume_for_rotation`, `revoke_by_hash`, `revoke_family`, `revoke_all_for_user`, `RefreshInvalid`, `RefreshReuse`, `RotationResult`) but talks only to the port: `get_by_token_hash`, `mark_rotated` (CAS), `clear_rotated` (child-insert rollback) and the revoke methods. `_as_utc`, `ensure_indexes` and `_revocation_update` moved out (the adapter owns them).
- `RepositoryContainer` gains `refresh_session_collection = DIObject("auth_refresh_sessions")` and `refresh_session = DISingleton(MongoRefreshSessionRepository, collection=DICallable(operator.getitem, collection_repository, refresh_session_collection))`.
- Lifespan overrides the collection name from `AuthSettings.refresh_collection`, resolves the singleton, ensures indexes, and hands it to `AuthContainer.refresh_session_repository`.
- Tests: the three `RefreshSessionStore` construction sites build the Mongo adapter; four new tests in `test_auth_container.py` (singleton, default name, custom name, settings default) plus `test_lifespan_wires_refresh_session_repository`, which enters the real lifespan with only Couchbase stubbed and Mongo on mongomock.

## Tasks and commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 (tracer) | 3b8e6a8 | Store over the port, container and lifespan wiring, construction sites updated |
| 2 | a346beb | Container, settings and real-lifespan boot tests |

Verification: all 16 session-store tests pass; full suites api 227, core 83, scheduler 4 passed; pyright 0 errors (12 pre-existing warnings); boot smoke printed `boot-ok`; `lifespan-wired` and `wiring-ok` gates pass; 0 pymongo imports in `backend/api/src`.

## Deviations from Plan

**1. [Rule 3 - Blocking] Hand-rolled fake collection in `test_cas_matched_zero_branch_revokes_family`**
- **Issue:** The test's `_ZeroCasCollection.find_one` returned a document without `issuedAt` and `createdBy`. The old store never read them, but the adapter's `_to_session` does, so the test raised `KeyError`.
- **Fix:** Added those two fields to the fake document. No assertion changed or removed.
- **Files modified:** `backend/api/tests/test_session_store.py`
- **Commit:** 3b8e6a8

**2. [Formatting] Two lifespan override calls kept on one line in `main.py`**
- The plan's grep gates match the single-line text, so the calls are not wrapped at 88 columns. Folded into 3b8e6a8.

**Tracer gate:** end-to-end verify (session-store, auth API, full api suite, boot smoke) passed before Task 2.

## Orchestrator note

FOUND-05 was already ticked in REQUIREMENTS.md by 01-06. With this plan the tick is accurate: refresh sessions go through the port and `backend/api/src` has no pymongo import. I did not re-mark it.

## Known Stubs

None.

## Threat Flags

None. T-01-35 is covered by the unchanged race and rollback session-store tests running over the adapter's conditional update. T-01-31 is covered by the container tests and the boot test with a custom collection name.

## Self-Check: PASSED

Commits 3b8e6a8 and a346beb are on the branch; modified files exist.
