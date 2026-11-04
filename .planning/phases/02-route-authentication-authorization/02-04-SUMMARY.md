---
phase: 02-route-authentication-authorization
plan: 04
subsystem: auth
tags: [authorization, policy-engine, d-06, d-07, d-08, d-16, idor, reference-router]
type: execute
status: complete

requires:
  - phase: 02-route-authentication-authorization
    provides: POLICY table (plan 02-02), strict bearer floor and token_for helpers (plan 02-03)
provides:
  - openwellness_api.authz.engine with Verdict, authorize(module, op) and Access (check_record, scope_list, stamp_create, check_members)
  - weight as the reference router: all seven ops behind authorize
  - apply_patch with a required principal, an immutable-key set and an admin-only-key set; stamp_audit that always records sub
  - test harness build_test_app, app_builder, World, seed_world, world, reset_fakes
  - test_policy_matrix.py (ROLLED_OUT, body_for, expected) generated from POLICY
affects: [02-05 to 02-09 router rollout, 02-10 route structure test imports body_for, phase 6 sync policy]

actuals:
  tokens: 16400
  tasks: 3
  commits: 5

commits: 5
plan_head_before: 0f47d3b1965136fb80dc3b0a6d3eb31199ba7a6d
plan_head_after: 58301df781de7f71b2e707b0f5a33aef79d52d8d

tech-stack:
  added: []
  patterns:
    - "Policy decision as a per-request Access built from the verified Principal; no module-level state"
    - "Deferred predicates: a column that needs the record is resolved by check_record or scope_list"
    - "Denial 404 text derived from the URL so it equals not_found/check_parent"

key-files:
  created:
    - backend/api/src/openwellness_api/authz/engine.py
    - backend/api/tests/test_authz_engine.py
    - backend/api/tests/test_policy_matrix.py
  modified:
    - backend/api/src/openwellness_api/common/handlers.py
    - backend/api/src/openwellness_api/resources/weight.py
    - backend/api/tests/conftest.py
    - backend/api/tests/test_e2e_roles_flow.py
    - backend/api/tests/test_weights_owner_crud.py

key-decisions:
  - "Engine implemented to the plan's decision rules 1-4 and predicate table with no deviation; a handler that skips check_record/scope_list fails open for deferred columns, so the matrix is the guard"
  - "self-study checks the segment/own-study first and treats a no-segment list or create as vacuous without reading the Participant (keeps A1 'no read')"
  - "stamp_create for binding membership denies a non-admin whose supplied study is outside coach_studies by leaving study empty, so the one deny path is shared"
  - "make_fakes() extracted in conftest so a module-scoped app can share the fixture's fake set"

requirements-completed: [AUTH-03, AUTH-05, AUTH-06]

coverage:
  - id: D1
    description: "D-06 scope before role: participant POST under another user is 404, own :purge is 403, coach create is 403 in-study and 404 out of study"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_order_scope_before_role"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-07 multi-role union: a participant who is also a coach has self rights on own data and coach rights in their studies"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_multirole_union"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-08 coach list scoping: all removed is 404, mixed returns in-study only, past-study records stay visible, no records is an empty 200, pagination walks each in-scope record once"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_d08_all_removed_is_404"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_d08_no_records_is_empty_200"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_coach_scoped_list_pagination"
        status: pass
    human_judgment: false
  - id: D4
    description: "A denied record request returns exactly the body a missing record returns, for a non-owner and an out-of-study coach"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_denial_404_matches_missing_404"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_authz_engine.py#test_check_record_name_sets_the_404_text"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-16 and mass assignment: updated_by is the verified sub on create and patch, a forged header changes nothing, patch cannot move owner or study_id for any caller"
    requirement: AUTH-06
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_updated_by_is_sub"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_patch_cannot_move_a_record"
        status: pass
    human_judgment: false
  - id: D6
    description: "Study binding on create: study_id comes from the owner's Participant, a differing value or an owner with no study is 404 even for admin; an unbound row raises"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_study_binding"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_authz_engine.py#test_stamp_create_refuses_a_row_with_no_binding"
        status: pass
    human_judgment: false
  - id: D7
    description: "Weight meets its ADR row for all seven ops and seven caller classes (49 cells); every create route accepts body_for (35 modules)"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_policy_matrix"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_body_for_creates_on_every_router"
        status: pass
    human_judgment: false
  - id: D8
    description: "Group members check (A-09-2) and coach write check on the owner's Participant, at engine level"
    requirement: AUTH-05
    verification:
      - kind: unit
        ref: "backend/api/tests/test_authz_engine.py#test_check_members"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_authz_engine.py#test_coach_write_check"
        status: pass
    human_judgment: false

duration: about 50 min
completed: 2026-11-04
---

# Phase 2 Plan 04: Policy engine and the weight reference router Summary

**`authz/engine.py` decides every request from `POLICY` (role predicate, scope-none rule, scope predicate, best verdict across columns), with a URL-derived 404 byte-identical to a missing record, and `weight` runs all seven operations through it, proven by a 49-cell matrix and named D-06/D-07/D-08/D-16 tests.**

## Accomplishments

- `authorize(module, op)` is a callable class returning a per-request `Access`; an unknown module or op is 403, logged at error. `Access.check_record`, `scope_list`, `stamp_create` and `check_members` implement the interface block as written.
- `weight.py` is the recipe for the other 35: `authorize` on every handler, `check_record` at the end of `_fetch`, `scope_list` before `paginate`, `stamp_create` on create, `apply_patch(..., principal=access.principal)`.
- `common/handlers.py`: `stamp_audit` assigns `principal.id` unconditionally; `apply_patch` requires `principal`, ignores `_IMMUTABLE_PATCH_FIELDS` for everyone and `_ADMIN_ONLY_PATCH_FIELDS` for non-admins.
- Test harness: `build_test_app` (every unnamed provider gets an `InMemoryOwnerRepo`), `app_builder`, `World`/`seed_world`/`world`/`reset_fakes`, `make_fakes`. Coaches can sign in through the real OTP flow against seeded users.
- `test_policy_matrix.py`: `ROLLED_OUT` is computed from `authorize` dependencies, `expected()` encodes the ADR rows for all 36 modules. Cross-checked once against the engine for all 36 modules x 7 ops x 7 callers (1764 cases): all agree, except the four membership-create cases (`conversation`, `participant_group` for out-of-study coaches), which are 404 only after the router calls `stamp_create`/`check_members` (plan 02-09), as the plan states.

## Task Commits

1. Task 1 (tracer) RED `b754619`: harness plus `test_coach_other_study_is_404` failing with 200 vs 404. The in-study test passes before the engine, by design (no policy yet means everything is allowed).
2. Task 1 GREEN `dac3a4f`: engine core, weight list scoped. Tracer gate: the `<verify>` re-run gave 10 passed (needs 9). Tracer verified end-to-end, expanding.
3. Task 2 RED `23082cb`: 30 failures (missing `check_record`, `stamp_create`, `check_members`, missing `studyId`), on the planned assertions.
4. Task 2 GREEN `86a7e34`: remaining predicates, handlers changes, all seven weight ops.
5. Task 3 `58301df`: matrix and named tests.

## TDD Gate Compliance

Task 1 and Task 2 followed RED then GREEN as above; RED was assessed by inspection of the pytest report (target tests failed on the planned assertion or on a missing method on the unit under test, not on collection errors). `gsd_run check tdd-red-evidence` was not run: `workflow.tdd_mode` is not enabled and the plan is `type: execute`. Task 3 has no RED commit: its behavior was implemented in Task 2, so those tests are characterization tests that passed on first run. The assertions were checked to be meaningful by the engine cross-check described above and by Task 2's RED, which covered the same decision paths at engine level. No REFACTOR commits.

## Deviations from Plan

None - plan executed exactly as written. Two small test-side adjustments follow from the plan's own behavior and are not deviations of scope:

- `test_signed_in_caller_reaches_a_resource_route` (plan 02-03) now reads the caller's own participant id, because `/v1/users/any/weights` is correctly 404 once the policy runs.
- `test_study_binding` exercises the coach branch at engine level on `job_rule`, since weight's coach cell has no create (a coach POST on weight is 403 before binding). The plan lists the coach case under `test_study_binding` on weight; this is the only way to reach it.

## Known Stubs

- `self-member-conversation` matches nothing (conversation predicate returns False), per OQ1 and the ADR 0007 Phase 2 amendment; the stored membership link is Phase 6. Marked with a `# shortcut:` comment in `engine.py`.

## Issues Encountered

- A router that never calls `check_record` or `scope_list` fails open for deferred columns. There is no runtime guard; the matrix (generated from `ROLLED_OUT`) is what catches it, so every router plan must keep its modules in the matrix gate.
- Interim state as before: routers not yet carrying `authorize` are protected by the bearer floor only, until plans 02-05 to 02-09.
- The plan's frontmatter `estimate` was low confidence; `actuals.tokens` is chars/4 over the realized diff (65,618 characters).

## Flagged assumptions

Edge AUTH-03 remains surfaced, not silently resolved: path binding, the record-owner check and hostile `filter=` are covered by this plan and plan 02-05; developer to flag anything else AUTH-03 should cover.

## Threat Flags

None. No new endpoints or schema; `authorize` adds an access check on existing routes. T-02-07 to T-02-12 are covered by `test_policy_matrix.py` and `test_authz_engine.py`.

## Verification

Per suite: core 88 passed, api 421 passed (260 before), scheduler 4 passed; pyright 0 errors (12 pre-existing warnings); `check_no_fstring_n1ql.py` exit 0. Gates: `-k "[weight-"` 49 passed; `-k body_for` 35 passed; `-k "order or multirole or d08"` 6 passed.

Note: commits landed on `main` because the orchestrator set `branching_strategy=none` and dispatched sequentially.

## Self-Check: PASSED

- FOUND: backend/api/src/openwellness_api/authz/engine.py
- FOUND: backend/api/tests/test_authz_engine.py
- FOUND: backend/api/tests/test_policy_matrix.py
- FOUND commits: b754619, dac3a4f, 23082cb, 86a7e34, 58301df
