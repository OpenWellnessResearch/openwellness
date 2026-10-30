---
phase: 01-foundations-architecture-decisions
fixed_at: 2026-10-30T00:00:00Z
review_path: .planning/phases/01-foundations-architecture-decisions/01-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 4
skipped: 1
status: partial
---

# Phase 1: Code Review Fix Report

**Fixed at:** 2026-10-30
**Source review:** .planning/phases/01-foundations-architecture-decisions/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 4
- Skipped: 1

**Verification location:** all gates ran in the orchestrator-provided worktree
`.claude/worktrees/pr6-review` (branch `gsd/pr6-code-review`), no nested worktree. Before each commit:
`pytest` in `backend/core`, `backend/api`, `backend/scheduler` (run per package, as CI does; a combined
`pytest core api scheduler` fails on a duplicate `tests.conftest` module name, a pre-existing layout limit)
and `uv run pyright` (0 errors). Final counts: core 85, api 231, scheduler 4 passed.

## Fixed Issues

### WR-01: `MongoParticipantRepository._to_doc` makes legacy participants un-patchable and un-archivable, with a misleading 404

**Files modified:** `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_participant_repository.py`, `backend/api/tests/test_participant_ids.py`
**Commit:** 4474523
**Status:** fixed: requires human verification (logic change)
**Applied fix:** `_to_doc` now coerces valid ObjectIds and passes any other stored value through unchanged, so `save` and `archive` work on legacy string ids. Strictness moved to a `create` override that still raises `EntityNotFoundException` for a malformed or empty reference, so the existing 404-on-create behavior and tests hold. The exception message names the field only and no longer echoes the value. Added tests: PATCH and DELETE over a legacy-string `userId`, and a no-echo message test. The review's optional request-schema pattern constraint (400 instead of 404 on create) was not added, because it would change the wire contract.

### WR-02: New catch-all 500 handler returns no CORS headers, and every unhandled error is logged twice

**Files modified:** `backend/api/src/openwellness_api/errors/handlers.py`, `backend/api/tests/test_repository_errors.py`
**Commit:** 7e3d74b
**Status:** fixed: requires human verification (logic change)
**Applied fix:** Took the review's first option. The handler echoes `Origin` with `access-control-allow-credentials` and `vary: Origin` only when the origin is in `APISettings().cors_origins_list`. Dropped `exc_info` from the handler log line because Starlette re-raises and uvicorn already logs the traceback. Test asserts the header for an allowed origin and its absence for another. The header is checked against a test app that registers handlers without `CORSMiddleware`; the real `create_app` stack was not probed end to end.

### WR-03: ADR 0007 omits two live routes, and one of them can bypass the membership scope the ADR defines

**Files modified:** `docs/adr/0007-authorization-policy-table.md`
**Commit:** f2988b1
**Applied fix:** Documentation only. Reworded "same seven operations" to "seven standard operations" plus custom methods, and added a "Custom methods" table (separate from the 36-row Policy table so the row-count and closed-vocabulary gates are unchanged) with cells for both routes. `conversation:search` states that the scope predicate applies before caller filters. Cells follow the review's suggestion, with admin also granted. Route-diff test remains a Phase 2 item, noted in the ADR.

### WR-04: `APP_*` variables listed in `.env.example` are read with `os.environ`, so they are silently ignored on direct runs

**Files modified:** `backend/core/src/openwellness_core/infrastructure/config/settings.py`, `backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_app_repository.py`, `backend/core/tests/test_settings.py`
**Commit:** d284012
**Applied fix:** Added `AppSettings(OpenWellnessSettings)` with `env_prefix="APP_"` (`store_id`, `ios_bundle_id`, `one_signal_app_id`). `MongoAppRepository` takes an optional `app_settings` and falls back to `AppSettings()` inside `create_app`, so the container wiring and `AppConfigInterface` are unchanged (`create_app` has no callers today). Tests cover `.env` loading and the unlisted-link flag.

## Skipped Issues

### WR-05: Unauthenticated `POST /v1/users` now answers 409 ALREADY_EXISTS, an email-existence oracle

**File:** `backend/api/src/openwellness_api/errors/handlers.py:87-102`
**Reason:** Skipped per instruction. This is a deliberate interim decision, recorded as an accepted gap in ADR 0007 pending route auth in Phase 2. No principal is enforced yet (`enforce_principal` is False), so there is no authenticated caller to keep the 409 for, and a minimal test-backed mitigation that preserves the contract does not exist before Phase 2.
**Original issue:** Any caller can distinguish 201 from 409 on `POST /v1/users` and learn whether an email is registered.

---

_Fixed: 2026-10-30_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
