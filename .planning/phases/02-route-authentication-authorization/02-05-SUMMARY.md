---
phase: 02-route-authentication-authorization
plan: 05
subsystem: auth
tags: [authorization, policy-engine, participant-data, filter-scope, d-08, idor]
type: execute
status: complete

requires:
  - phase: 02-route-authentication-authorization
    provides: authorize/Access engine, weight reference router, matrix harness (plan 02-04)
provides:
  - twelve participant-data routers under authorize (goal, asset, card, daily_state, meta_data, physical_activity, post, session, survey_result, user_food, user_sleep, user_stress)
  - goal list that scopes the unfiltered owner list before parsing filter=
  - tests/test_filter_scope.py (hostile filter and scope-before-filter)
affects: [02-06 to 02-09 sibling rollouts, 02-10 route structure test]

actuals:
  tokens: 9560
  tasks: 3
  commits: 4

commits: 4
plan_head_before: ad16195660b24474f534229dc122a0f84034981b
plan_head_after: 1bec50a4629c5e867e5a688339a5b70cb68f6e1b

tech-stack:
  added: []
  patterns:
    - "Scope the unfiltered owner list first, then let filter= narrow by intersection"

key-files:
  created:
    - backend/api/tests/test_filter_scope.py
  modified:
    - backend/api/src/openwellness_api/resources/goal.py
    - backend/api/src/openwellness_api/resources/asset.py
    - backend/api/src/openwellness_api/resources/card.py
    - backend/api/src/openwellness_api/resources/daily_state.py
    - backend/api/src/openwellness_api/resources/meta_data.py
    - backend/api/src/openwellness_api/resources/physical_activity.py
    - backend/api/src/openwellness_api/resources/post.py
    - backend/api/src/openwellness_api/resources/session.py
    - backend/api/src/openwellness_api/resources/survey_result.py
    - backend/api/src/openwellness_api/resources/user_food.py
    - backend/api/src/openwellness_api/resources/user_sleep.py
    - backend/api/src/openwellness_api/resources/user_stress.py
    - backend/api/tests/test_goals_carveout.py

key-decisions:
  - "goal kind filter runs the repository kind query and keeps only ids present in the scoped list, so filter= can only narrow (LegacyGoal has no kind attribute, so no Python-side kind filtering)"
  - "The router recipe was applied with a throwaway script kept outside the repo; every diff was read and the matrix is the gate"

requirements-completed: [AUTH-03, AUTH-05]

coverage:
  - id: D1
    description: "A participant's own goals answer; another participant's path is 404 through filter=kind and filter=owner; owner= on the caller's own path is 400"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/api/tests/test_filter_scope.py#test_owner_filter_on_own_path_is_400"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_filter_scope.py#test_owner_filter_on_other_path_is_404"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_filter_scope.py#test_kind_filter_on_other_path_is_404"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-08 on goal: coach scope runs before filter=kind; kind narrows in-scope records only; all-removed is 404; hostile filter after scope is 404"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_filter_scope.py#test_coach_kind_filter_stays_in_scope"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_filter_scope.py#test_coach_kind_filter_all_removed_is_404"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_filter_scope.py#test_hostile_filter_after_scope"
        status: pass
    human_judgment: false
  - id: D3
    description: "All twelve modules meet every cell of their ADR 0007 rows (12 modules x 7 ops x 7 callers)"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_policy_matrix.py#test_policy_matrix"
        status: pass
    human_judgment: false

duration: about 25 min
completed: 2026-11-04
---

# Phase 2 Plan 05: Participant-data routers under the policy engine Summary

**Twelve participant-data routers (including `goal` with `filter=`) now run every handler through `authorize`, with goal scoping the unfiltered owner list before the kind filter so a query parameter can only narrow, proven by 588 matrix cells and six filter-scope tests.**

## Accomplishments

- `goal`, `asset`, `card`, `daily_state`, `meta_data`, `physical_activity`, `post`, `session`, `survey_result`, `user_food`, `user_sleep`, `user_stress`: seven `Depends(authorize(...))` handlers each, `check_record` ending `_fetch`, `scope_list` before `paginate`, `stamp_create` on create, `apply_patch(..., principal=access.principal)`. None imports `get_principal`.
- `goal.list_items`: `access.scope_list(get_all_for_owner_between(...))` first, then `parse_filter`, then the kind query intersected with the scoped ids. `_build_goal` takes `access`.
- `test_goals_carveout.py` seeds a Participant per owner and no longer sends the forged `X-Principal-Id` header (count 2 to 0).

## Task Commits

1. Task 1 RED `3de99c0`: `test_filter_scope.py` (5 of 6 failed on the planned status assertions; the own-path 400 already held) plus carveout fixture.
2. Task 1 GREEN `6ff374d`: goal and asset. Tracer gate: filter-scope and carveout 9 passed, matrix `[goal-`/`[asset-` 98 passed. Tracer verified end-to-end, expanding.
3. Task 2 `eb06811`: card, daily_state, meta_data, physical_activity, post (245 passed).
4. Task 3 `1bec50a`: session, survey_result, user_food, user_sleep, user_stress (245 passed).

## TDD Gate Compliance

Task 1 followed RED (`3de99c0`) then GREEN (`6ff374d`). RED was assessed from the pytest report: failures were the planned 200-vs-404 assertions, not collection errors. `gsd_run check tdd-red-evidence` was not run (`type: execute` plan, `workflow.tdd_mode` off). Tasks 2 and 3 are `auto` with matrix verification and no RED commit. No REFACTOR commits.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Reported, out of scope (as the plan states): `get_for_owner_between` is missing from the Couchbase adapters of `asset`, `card`, `meta_data`, `physical_activity`, `post`, `session`, `survey_result`, `user_sleep` and `user_stress`, so their lists raise 500 on a live store. It predates this phase; in-memory fakes have the method, so tests pass regardless.
- The plan's acceptance check is 98 + 245 + 245 = 588 matrix tests, matched exactly.

## Known Stubs

None.

## Threat Flags

None. No new endpoints or schema. T-02-13 is covered by `test_filter_scope.py` (scope first, grammar cannot name owner or study_id); T-02-14 by the matrix over all twelve modules.

## Verification

Per suite: api 1015 passed (421 before, plus 6 filter-scope and 588 matrix), core 88 passed, scheduler 4 passed; pyright 0 errors (12 pre-existing warnings); `check_no_fstring_n1ql.py` exit 0. Plan-level command: 9 passed, then 588 passed.

Note: commits landed on `main` because the orchestrator set `branching_strategy=none` and dispatched sequentially.

## Self-Check: PASSED

- FOUND: backend/api/tests/test_filter_scope.py
- FOUND commits: 3de99c0, 6ff374d, eb06811, 1bec50a
