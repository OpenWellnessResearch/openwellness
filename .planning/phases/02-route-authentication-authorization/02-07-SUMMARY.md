---
phase: 02-route-authentication-authorization
plan: 07
subsystem: auth
tags: [authorization, policy-engine, study-scope, lookup, mass-assignment, regex-escape]
type: execute
status: complete

requires:
  - phase: 02-route-authentication-authorization
    provides: policy engine, weight reference router, matrix harness (plan 02-04)
provides:
  - participant, study, study_message and study_settings routers under authorize
  - study :lookup scope-filtered, denial byte-identical to a missing study
  - MongoStudyRepository.get_by_name with an escaped name pattern
  - tests/test_study_rows.py (14 tests)
affects: [02-08, 02-09, 02-10 route structure test, phase 6 sync policy]

actuals:
  tokens: 4500
  tasks: 2
  commits: 4

commits: 4
plan_head_before: 63068dbba161f4a05a2dafaa8388fd3407553cc9
plan_head_after: a5367728f0cb1f99d9f2809be1644267a2ebf170

tech-stack:
  added: []
  patterns:
    - "binding-None routers (participant, study, study_message) keep their own create and gate it with authorize only"
    - "id-in-body custom method denies through check_record(entity, name=...) so the 404 text equals not_found"

key-files:
  created:
    - backend/api/tests/test_study_rows.py
  modified:
    - backend/api/src/openwellness_api/resources/participant.py
    - backend/api/src/openwellness_api/resources/study.py
    - backend/api/src/openwellness_api/resources/study_message.py
    - backend/api/src/openwellness_api/resources/study_settings.py
    - backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_study_repository.py

key-decisions:
  - "A1 holds as written: a participant's study-participants list and create are 403 for any study, with no Participant read"
  - "A-07-1: get_by_name escapes the name with re.escape; the lookup stays an exact case-insensitive match"
  - "A body studyId on a study_settings create is dropped by the wire schema (extra=ignore), so the row is bound to the path study rather than answering 404"

requirements-completed: [AUTH-05, AUTH-06]

coverage:
  - id: S1
    description: "A coach lists and patches participants only under a study in coach_studies (404 elsewhere); a coach patch cannot change user_id, an admin patch can"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_study_rows.py#test_coach_lists_participants_in_study"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_study_rows.py#test_coach_patch_ignores_user_id"
        status: pass
    human_judgment: false
  - id: S2
    description: "A participant reads their own record only; their list and create are 403 for any study with no read (A1)"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_study_rows.py#test_participant_reads_own_record"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_study_rows.py#test_participant_list_is_403_for_any_study"
        status: pass
    human_judgment: false
  - id: S3
    description: ":lookup is scope-filtered and answers a study out of scope exactly as a missing one; the name regex is escaped"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_study_rows.py#test_lookup_denied_matches_missing"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_study_rows.py#test_lookup_regex_is_escaped"
        status: pass
    human_judgment: false
  - id: S4
    description: "A study's updated_by comes from the token on create and patch; study_settings is bound to the path study; a participant with no study fails closed"
    requirement: AUTH-06
    verification:
      - kind: integration
        ref: "backend/api/tests/test_study_rows.py#test_study_updated_by_from_token"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_study_rows.py#test_study_settings_binding"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_study_rows.py#test_self_study_fail_closed"
        status: pass
    human_judgment: false

duration: about 25 min
completed: 2026-11-04
---

# Phase 2 Plan 07: Study-parented routers under the engine Summary

**`participant`, `study`, `study_message` and `study_settings` run all seven ops through `authorize`; the participant patch goes through `apply_patch` so a coach cannot relink `user_id`, `:lookup` denies with the exact bytes of a missing study, and `get_by_name` no longer feeds the lookup name to `$regex` unescaped.**

## Accomplishments

- `participant.py`: `authorize("participant", op)` on every handler, `_fetch` keeps both `not_found` checks then calls `check_record`, list goes through `scope_list`, and the `setattr` loop is gone in favour of `apply_patch` (`user_id` is admin-only).
- `study.py`: all seven ops plus `lookup` (`authorize("study", "get")`, `check_record(entity, name=body.name)`, no router-level exception handling). `create` overwrites `updated_by` with the token's id; `patch` already did through `apply_patch`.
- `study_message.py`: engine on all ops, `check_parent` then `check_record`, create keeps its own `study_id = study`, list wrapped in `scope_list`.
- `study_settings.py`: engine on all ops, create uses `access.stamp_create(..., parent_id=study)`, list wrapped in `scope_list`.
- `mongo_study_repository.py`: `re.escape(name)` inside the anchored case-insensitive pattern (T-02-18).

## Task Commits

1. Task 1 RED `1568be5`: 5 of 6 participant tests failing on the planned assertions (200 where 404/403 was expected, and the A1 read guard firing).
2. Task 1 GREEN `6fa5ddd`: participant router. Tracer gate re-run: 13 passed (`test_study_rows` + `test_participant_ids`), matrix `[participant-` 49 passed. Tracer verified end-to-end, expanding.
3. Task 2 RED `01c6980`: study, lookup, settings and message tests failing, including `ValueError: Multiple studies found with name .*` for the unescaped regex.
4. Task 2 GREEN `a536772`: the three routers and the repository fix.

## TDD Gate Compliance

RED then GREEN for both tasks as above; RED was judged by reading the pytest report (assertion failures on the planned behavior, not collection errors). `gsd_run check tdd-red-evidence` was not run: the plan is `type: execute` and `workflow.tdd_mode` is off. No REFACTOR commits.

## Deviations from Plan

**1. [Test expectation] `test_study_settings_binding`: a differing `studyId` is dropped, not 404**
- **Found during:** Task 2 RED
- **Issue:** The plan expects a body `studyId` that differs from the path to answer 404. `StudySettingsCreate` has no `studyId` field and `SCHEMA_CONFIG` sets `extra="ignore"`, so the key never reaches `stamp_create`; the row is bound to the path study and the answer is 201.
- **Fix:** The test asserts the property that matters: the row is stored with `studyId` equal to the path study, whatever the body names. No policy matrix expectation changed, no wire contract changed. A 404 would need `studyId` added to the create schema, which is a wire change outside this plan.
- **Files modified:** `backend/api/tests/test_study_rows.py`
- **Commit:** `a536772` (tests committed in `01c6980`)

**Total deviations:** 1 (test expectation clarified). **Impact:** none on security; the body cannot move a settings row to another study.

## Known Stubs

None.

## Issues Encountered

- `get_for_owner_between` is missing from the Couchbase `study_settings` adapter, so its list raises 500 on a live Couchbase store. Predates this phase and is out of this plan's scope, as the plan states; the fake in tests has the method.

## Threat Flags

None. T-02-18 to T-02-21 are mitigated and covered by `test_lookup_regex_is_escaped`, `test_lookup_denied_matches_missing`, `test_coach_patch_ignores_user_id` and `test_study_updated_by_from_token`.

## Verification

- `tests/test_study_rows.py` plus `tests/test_participant_ids.py`: 20 passed (14 + 6).
- Matrix `-k "[participant- or [study- or [study_message- or [study_settings-"`: 196 passed.
- Per suite: api 1821 passed, core 88 passed, scheduler 4 passed; pyright 0 errors (12 pre-existing warnings); `check_no_fstring_n1ql.py` exit 0.
- `grep -c 'check_record(entity, name=body.name)' study.py` is 1.

Commits landed on `main` because `branching_strategy=none` and execution was sequential.

## Self-Check: PASSED

- FOUND: backend/api/tests/test_study_rows.py
- FOUND: backend/api/src/openwellness_api/resources/participant.py (no `setattr`)
- FOUND: `re.escape(name)` in mongo_study_repository.py
- FOUND commits: 1568be5, 6fa5ddd, 01c6980, a536772
