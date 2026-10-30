---
phase: 01-foundations-architecture-decisions
plan: 06
subsystem: auth
tags: [repository-port, mongo, refresh-sessions, compare-and-set, mongomock]
status: complete

requires:
  - phase: 01-foundations-architecture-decisions
    provides: "01-03 object_id_or_none guarded id conversion; 01-05 port/adapter error conventions"
provides:
  - "RefreshSession record and RefreshSessionRepository port (7 abstract methods) in openwellness_core.application.repositories"
  - "MongoRefreshSessionRepository(collection=...) with ensure_indexes(), keeping today's document and index names"
  - "11 adapter contract tests over mongomock"
affects: [01-11, phase-03-refresh-grace-window, phase-04-postgres-adapter]

actuals:
  tokens: 3600
  tasks: 2
  commits: 3
plan_head_before: 2465b5bdf6c84a5db9ef7d641025acfa5a296dd8
plan_head_after: 79d1530f14c8a5205772119a3aa7269cf2d3a108

tech-stack:
  added: []
  patterns:
    - "Auth persistence record lives beside its port; adapter receives its collection handle from the caller"
    - "Single-use rotation is one conditional update_one with a matched_count check, no transaction"

key-files:
  created:
    - backend/core/src/openwellness_core/application/repositories/refresh_session_repository.py
    - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_refresh_session_repository.py
    - backend/api/tests/test_refresh_session_repository.py
  modified:
    - backend/core/src/openwellness_core/application/repositories/__init__.py
    - backend/core/src/openwellness_core/adapters/mongo/repositories/__init__.py

key-decisions:
  - "RefreshSession is a frozen kw_only dataclass in the port module, not domain/models (auth persistence record, no behavior)"
  - "Adapter never names a collection so plan 01-11 can keep honoring API_AUTH_REFRESH_COLLECTION"
  - "Adapter uses only find_one/insert_one/update_one/update_many so the existing test_session_store.py wrappers keep biting after 01-11"

requirements-completed: [FOUND-05]

duration: 15min
completed: 2026-10-30
---

# Phase 1 Plan 06: Refresh-session port and Mongo adapter Summary

**Datastore-neutral `RefreshSessionRepository` port with a Mongo adapter that writes today's exact refresh-session document, with atomic single-use `mark_rotated` and scoped revocation proven by contract tests.**

## What was built

- Port module with `RefreshSession` (sha256 `token_hash` only, no raw-token field) and seven abstract methods: `create`, `get_by_token_hash`, `mark_rotated`, `clear_rotated`, `revoke_by_token_hash`, `revoke_family`, `revoke_all_for_user`. Docstrings state the atomicity contract.
- `MongoRefreshSessionRepository` writes the same 14 camelCase fields and the same four index names (`uq_token_hash`, `ix_family_id`, `ix_user_id`, `ttl_expires_at`) as `session_store.py`, so live sessions need no migration. `_as_utc` and `ensure_indexes` are copied verbatim; plan 01-11 deletes the store-side copies.
- Nothing consumes the port yet; the API still uses `RefreshSessionStore`.

## Tasks and commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 (tracer) | e49047b | Port, adapter create/get/ensure_indexes, 4 tests; other methods stubbed |
| 2 RED | 2cf751e | 7 failing tests for rotation and revocation |
| 2 GREEN | 79d1530 | Implemented the five stubbed methods |

Tracer verification: pytest (4 passed, full api suite 216 passed) and pyright (0 errors) re-run green before Task 2.
Final: 223 api tests passed, pyright 0 errors (12 pre-existing warnings), 0 `NotImplementedError` left in the adapter.

## TDD

- **RED:** 7 target tests (`test_mark_rotated_*`, `test_clear_rotated_only_while_value_matches`, `test_revoke_by_token_hash_touches_that_session_only`, `test_bulk_revoke_is_scoped[family|user]`) failed; the 4 Task 1 tests still passed. Manual semantic assessment (pytest output is not a format `gsd_run check tdd-red-evidence` accepts, so the classifier was not run): the tests were collected and executed, and each failed by reaching the planned stub (`NotImplementedError("Task 2")`) inside the method under test, not on an import, syntax or fixture fault. A stub-driven RED rather than an assertion RED, as the plan prescribes.
- **GREEN:** all 11 tests pass after implementing the five methods. No REFACTOR commit.

## Deviations from Plan

- Added one extra test (`test_is_a_refresh_session_repository`) to Task 1, so 4 rather than 3 tests exist after Task 1; total is 11 (plan minimum 9). Task 2's tests were added in the RED commit, keeping the cycle visible in git.
- During Task 1 I briefly implemented `mark_rotated` before restoring its stub, to keep it test-first. No code or commit was affected.

None otherwise: plan executed as written.

## Known Stubs

None. All `NotImplementedError` stubs were replaced.

## Threat Flags

None. No new network, auth or file surface; mitigations T-01-17 (CAS contract tests), T-01-18 (hash-only port) and T-01-19 (document and index names asserted, caller-supplied collection) are implemented as planned.

## Self-Check: PASSED

Files created exist; commits e49047b, 2cf751e and 79d1530 are on the branch.
