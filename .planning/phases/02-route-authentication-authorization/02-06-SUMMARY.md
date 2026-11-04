---
phase: 02-route-authentication-authorization
plan: 06
subsystem: auth
tags: [authorization, policy-engine, coach-writes, server-ingested, d-06, d-08, auth-05]
type: execute
status: complete

requires:
  - phase: 02-route-authentication-authorization
    provides: authorize/Access engine, weight reference router, matrix harness (plan 02-04)
provides:
  - five coach-authored routers (condition, message, job_rule, message_draft, user_settings) and seven server-ingested routers (shared_goal_progress, actigraph_record, fitbit_heart_record, fitbit_record, fitbit_sleep, fitbit_sleep_session, fitbit_weight) under authorize
  - condition._build_condition(body, user, access) stamping through access.stamp_create
  - message list that scopes the unfiltered owner list before parsing filter=
  - tests/test_coach_writes.py (coach write check, cross-study create, moved owner)
affects: [02-07 to 02-09 sibling rollouts, 02-10 route structure test]

actuals:
  tokens: 20990
  tasks: 3
  commits: 4

commits: 4
plan_head_before: e735235affcaadebd7a7f1a5009baf0ef91c96d8
plan_head_after: 0a89a24a2f5423abc7026924d585d125a46513ac

tech-stack:
  added: []
  patterns:
    - "Router recipe from 02-04 applied by a throwaway regex script (not committed), every diff read"
    - "Scope the unfiltered owner list first, then intersect with the filter-narrowed query (as goal in 02-05)"

key-files:
  created:
    - backend/api/tests/test_coach_writes.py
  modified:
    - backend/api/src/openwellness_api/resources/condition.py
    - backend/api/src/openwellness_api/resources/message.py
    - backend/api/src/openwellness_api/resources/job_rule.py
    - backend/api/src/openwellness_api/resources/message_draft.py
    - backend/api/src/openwellness_api/resources/user_settings.py
    - backend/api/src/openwellness_api/resources/shared_goal_progress.py
    - backend/api/src/openwellness_api/resources/actigraph_record.py
    - backend/api/src/openwellness_api/resources/fitbit_heart_record.py
    - backend/api/src/openwellness_api/resources/fitbit_record.py
    - backend/api/src/openwellness_api/resources/fitbit_sleep.py
    - backend/api/src/openwellness_api/resources/fitbit_sleep_session.py
    - backend/api/src/openwellness_api/resources/fitbit_weight.py
    - backend/api/tests/test_policy_matrix.py

key-decisions:
  - "Matrix list call sends integer bounds for condition (the only parse_int range) instead of changing condition's wire contract"
  - "message list intersects the filter query with the scoped set only when subtype or condition is present, otherwise returns the scoped set"

requirements-completed: [AUTH-03, AUTH-05]

coverage:
  - id: D1
    description: "A coach creates a condition only for a participant in a held study; study_id and updatedBy are server-set"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_coach_writes.py#test_coach_creates_condition_in_study"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_coach_writes.py#test_coach_create_other_study_participant_is_404"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_coach_writes.py#test_coach_supplied_study_cannot_cross"
        status: pass
    human_judgment: false
  - id: D2
    description: "A coach cannot patch or delete a record whose owner moved to another study, but can still read it"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_coach_writes.py#test_coach_patch_after_owner_moved_is_404"
        status: pass
    human_judgment: false
  - id: D3
    description: "A participant reads own coach-authored rows, cannot write them (403), and cannot reach or file under another participant or study (404)"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/api/tests/test_coach_writes.py#test_participant_reads_own_condition_only"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_coach_writes.py#test_participant_cannot_file_under_other_study"
        status: pass
    human_judgment: false
  - id: D4
    description: "message filter= narrows within scope and a hostile filter is 404 for an out-of-scope coach, 400 for the owner"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/api/tests/test_coach_writes.py#test_coach_message_filter_stays_in_scope"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_coach_writes.py#test_message_hostile_filter_after_scope"
        status: pass
    human_judgment: false
  - id: D5
    description: "All twelve modules meet their ADR 0007 cells for every op and caller class (588 cells)"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_policy_matrix"
        status: pass
    human_judgment: false

duration: about 25 min
completed: 2026-11-04
---

# Phase 2 Plan 06: Coach-authored and server-ingested routers Summary

**Twelve routers (condition, message, job_rule, message_draft, user_settings, shared_goal_progress, actigraph_record, five fitbit_* rows) now run all seven ops through `authorize`, and the coach write check is proven over HTTP including a moved owner.**

## Accomplishments

- Task 1 (tracer): `condition` builds entities through `access.stamp_create`, so study_id comes from the owner's Participant and a coach in study A cannot reach a participant in study B by any body value. `message` scopes the unfiltered owner list first, then intersects the `subtype`/`condition` query with the scoped set (D-08).
- Tasks 2 and 3: ten routers took the 02-04 recipe unchanged; `resolve_time_range` and the 7-day span limits (`actigraph_record`, `fitbit_sleep`, `fitbit_sleep_session`) stay where they were. `resources/fitbit.py` untouched (plan 02-09).
- `tests/test_coach_writes.py`: 8 tests. Matrix: 588 cells for these 12 modules pass.

## Task Commits

1. Task 1 RED `569fc43`: 7 of 8 coach-write tests failed on the planned assertions (the weight cross-study case already passed, since weight was rolled out in 02-04).
2. Task 1 GREEN `9110c70`: condition, message, matrix int-range tweak.
3. Task 2 `bf993f5`: job_rule, message_draft, user_settings, shared_goal_progress, actigraph_record.
4. Task 3 `0a89a24`: five Fitbit record routers.

Tracer gate: the Task 1 `<verify>` was re-run end to end (8 passed; 98 matrix passed) before expansion. Tracer verified end-to-end, expanding.

## TDD Gate Compliance

Task 1 followed RED then GREEN. RED was judged from the pytest report: the failing tests failed on the planned status-code assertions, not on collection. `gsd_run check tdd-red-evidence` was not run (plan `type: execute`, `workflow.tdd_mode` not enabled). Tasks 2 and 3 are `type="auto"` without `tdd`; their gate is the matrix, which failed open before the change (routers unprotected for owner_self writes) and passes after. No REFACTOR commits.

## Deviations from Plan

**1. [Rule 3 - Blocking] Matrix list call used timestamp bounds for condition**
- **Found during:** Task 1
- **Issue:** `condition` lists with `parse_int` (week numbers), so the matrix's ISO `startTime` returned 400 for the five 200-expected `condition-list-*` cells. The plan says the matrix needs no edit, but it was written for timestamp ranges only.
- **Fix:** added `INT_RANGE = {"startTime": 0, "endTime": 99999}` and used it when `module == "condition"`. Keeps the wire contract; the plan's no-edit instruction existed to avoid conflicts with parallel plans, and this run is sequential on `main`. The ROLLED_OUT detection, `expected()` and the engine are untouched.
- **Files modified:** backend/api/tests/test_policy_matrix.py
- **Commit:** `9110c70`

**2. [Test adjustment] test_coach_message_filter_stays_in_scope**
- The plan said `coach_other` with `filter=subtype=N` gets 404. With a study-B message of that subtype present, `coach_other` correctly gets that B record (200). The test asserts that, then moves the record out of B and asserts the 404. Same D-08 rule, setup made consistent.

**Total deviations:** 1 auto-fixed (Rule 3), 1 test-setup adjustment. **Impact:** none on scope.

## Known Stubs

None.

## Issues Encountered

- `get_for_owner_between` is missing from the Couchbase adapters of `job_rule`, `message_draft` and `user_settings`, so those lists 500 on a live store. Pre-existing, out of scope, already reported by the planner; the in-memory fakes used by the matrix are unaffected. Not logged to the windows ledger (no `.planning/WINDOWS.md` population attempted).
- Plan frontmatter estimate was low confidence at 60000 tokens; `actuals.tokens` is chars/4 over the realized diff (83,952 characters).

## Threat Flags

None. No new endpoints or schema; T-02-15 and T-02-16 are covered by `test_coach_writes.py` and the matrix.

## Verification

Plan-level: `tests/test_coach_writes.py` 8 passed; scoped matrix 588 passed. Per suite: api 1611 passed (1015 before), core 88 passed, scheduler 4 passed; pyright 0 errors (12 pre-existing warnings). None of the twelve files imports `get_principal`; each of the ten recipe files has seven `Depends(authorize(` occurrences and one `stamp_create` and `scope_list` (condition and message were hand-edited and gated the same way).

## Self-Check: PASSED

- FOUND: backend/api/tests/test_coach_writes.py
- FOUND commits: 569fc43, 9110c70, bf993f5, 0a89a24
