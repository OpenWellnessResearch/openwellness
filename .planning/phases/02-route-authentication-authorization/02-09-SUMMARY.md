---
phase: 02-route-authentication-authorization
plan: 09
subsystem: auth
tags: [authorization, membership, participant-group, conversation, fitbit, token-redaction, a-09-2]
type: execute
status: complete

requires:
  - phase: 02-route-authentication-authorization
    provides: authorize/Access engine, check_members, stamp_create, matrix harness (plan 02-04)
provides:
  - participant_group, conversation, device and fitbit routers behind authorize
  - resources/fitbit.py::_wire, the single serialization path that nulls OAuth tokens for non-admins
  - tests/test_membership_rows.py (17 tests) and tests/test_fitbit_device_rows.py (6 tests)
affects: [02-10 route structure and wave-boundary full run, 02-12 closes the Fitbit blocker in STATE.md, phase 6 conversation membership link]

actuals:
  tokens: 9700
  tasks: 3
  commits: 6

commits: 6
plan_head_before: 1919ad7871c29365ebc2594de622138c32abfede
plan_head_after: 25484aaf9341419178507c8f39b0bc37e6d60dca

tech-stack:
  added: []
  patterns:
    - "Membership rows: _fetch ends in check_record with no check_parent; list filters by participant_ids, then scope_list, then the time window"
    - "One serialization path per sensitive resource (_wire) so a redaction cannot be skipped on a new route"

key-files:
  created:
    - backend/api/tests/test_membership_rows.py
    - backend/api/tests/test_fitbit_device_rows.py
  modified:
    - backend/api/src/openwellness_api/resources/participant_group.py
    - backend/api/src/openwellness_api/resources/conversation.py
    - backend/api/src/openwellness_api/resources/device.py
    - backend/api/src/openwellness_api/resources/fitbit.py

key-decisions:
  - "participant_group list runs scope_list before the time window, not after: the window is part of the repo query for weight, but here an in-memory filter placed first would turn the D-08 all-removed 404 into an empty 200 for a coach outside the study whenever the window excludes the record"
  - "participant_group patch checks check_members only when participantIds is truthy, after _fetch and before apply_patch, so a denied patch leaves the stored object unchanged"
  - "conversation :search uses op list and scope_list on the get_for_filters result (A4)"

requirements-completed: [AUTH-03, AUTH-05, AUTH-06]

coverage:
  - id: C1
    description: "A participant reads a group by membership only; an owner who is not a member gets 404 and the group is absent from their list"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_non_member_is_404_even_when_owner"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_member_list_returns_memberships_only"
        status: pass
    human_judgment: false
  - id: C2
    description: "A coach cannot add a participant outside coach_studies to a group on create or patch; the denial body equals the normal denial; admins are unrestricted; a patch without participantIds reads no Participant"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_coach_group_create_cross_study_member_is_404"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_coach_group_patch_cross_study_member_is_404"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_admin_group_members_unrestricted"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_coach_group_patch_without_members_reads_no_participant"
        status: pass
    human_judgment: false
  - id: C3
    description: "Participants match no conversation (get 404, list and search empty, create 403); coaches are study-scoped; :search cannot widen scope; create records updated_by from the token"
    requirement: AUTH-06
    verification:
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_participant_matches_no_conversation"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_coach_conversation_scope"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_membership_rows.py#test_conversation_updated_by_from_token"
        status: pass
    human_judgment: false
  - id: C4
    description: "Fitbit accessToken and refreshToken are null for every non-admin and present for an admin on get, list, create, patch and undelete"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/api/tests/test_fitbit_device_rows.py#test_fitbit_tokens_null_for_owner"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_fitbit_device_rows.py#test_fitbit_tokens_visible_to_admin"
        status: pass
    human_judgment: false
  - id: C5
    description: "A participant lists and reads only their own devices; a coach gets 403 on device and fitbit routes"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_fitbit_device_rows.py#test_device_list_is_own_only"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_fitbit_device_rows.py#test_device_get_scope"
        status: pass
    human_judgment: false

duration: about 25 min
completed: 2026-11-04
---

# Phase 2 Plan 09: Membership rows and Fitbit token redaction Summary

**participant_group, conversation, device and fitbit now run every operation through the policy engine: groups open by `participant_ids` membership (never owner), a coach's group write refuses any participant outside their studies, conversations fail closed for participants, and Fitbit OAuth tokens are nulled for every non-admin through one `_wire` path.**

## Accomplishments

- `participant_group.py`: `check_parent` and `get_for_owner_between` are gone (the latter is not implemented by the Couchbase adapter, so list now works on a live store). List is `list_all` filtered by `{user}` in `participant_ids`, then `scope_list`, then the time window. Create is `stamp_create` then `check_members`; patch calls `check_members` before `apply_patch` when `participantIds` is set.
- `conversation.py`: all seven ops plus `:search` (op `list`, eight `authorize` dependencies). `create` goes through `stamp_create(parent_id=None)`, so `owner` from the body is kept and `updated_by` is the token's `sub`. Participants match nothing (engine `shortcut:` from plan 02-04, Phase 6 blocker unchanged).
- `device.py`: list and get scoped to the caller's `participant_id`.
- `fitbit.py`: `_wire(entity, access)` serializes, then nulls `accessToken` and `refreshToken` unless `principal.is_admin`; get, create, patch, undelete and every list row use it; `serialize_many` is no longer called.

## Task Commits

1. Task 1 (tracer) RED `0350b15`: 8 of 12 membership tests failing on the planned assertions. GREEN `5240cf2`. Tracer gate: 12 passed in `test_membership_rows.py` and 49 in `[participant_group-`; tracer verified end-to-end, expanding.
2. Task 2 RED `fa4067f`: 4 failing (patch-cannot-move already held through the immutable-field set, by design). GREEN `ed518f7`.
3. Task 3 RED `dafda68`: 5 of 6 failing. GREEN `25484aa`.

## TDD Gate Compliance

All three tasks went RED then GREEN as above, judged by inspection of the pytest report (planned assertions failing, no collection errors). `gsd_run check tdd-red-evidence` was not run: the plan is `type: execute` and `workflow.tdd_mode` is not enabled. No REFACTOR commits.

## Deviations from Plan

None - plan executed exactly as written. One ordering choice inside the plan's intent, recorded under key-decisions: the participant_group list applies `scope_list` before the `created_at` window rather than after it, because the matrix (`test_policy_matrix[participant_group-list-coach_other]`, expected 404) seeds a group created now but lists with a 2026-01-01..02 window; windowing first would give an empty 200. Plan text lists "then passes the result through `access.scope_list`" without fixing the order against the window.

## Known Stubs

- `self-member-conversation` still matches nothing (engine predicate, plan 02-04, OQ1); the stored link is Phase 6. Not new in this plan.

## Issues Encountered

- A bulk string-replace used to wire `authorize` into `participant_group.py` first assigned `get` to undelete and `delete` to purge; the matrix caught it (two cells) before commit and it was corrected. No committed state was affected.
- The plan's `actuals.tokens` is chars/4 over the realized diff (38,942 characters of `backend/` diff), against an estimate of 45,000.

## Flagged assumptions

OQ1, A4, A-09-1 and A-09-2 are all implemented as the plan states them (developer-confirmed defaults). Nothing new to flag.

## Threat Flags

None. No new endpoints or storage; the four routers gained access checks and a response filter on existing routes. T-02-22, T-02-23, T-02-24 and T-02-36 are covered by the named tests above.

## Verification

- `tests/test_membership_rows.py tests/test_fitbit_device_rows.py`: 23 passed.
- `tests/test_policy_matrix.py -k "[participant_group- or [conversation- or [fitbit- or [device-"`: 196 passed (49, 49, 98).
- Per suite: api 2205 passed (1986 before), core 88 passed, scheduler 4 passed.
- Pyright on `api/src`: 13 errors, all in routers outside this plan (`survey_result`, `user_settings`, `user_sleep`, `user_stress` and others using `get_for_owner_between`); none in the four files touched here.
- Commits landed on `main` (`branching_strategy=none`, sequential dispatch).

## Self-Check: PASSED

- FOUND: backend/api/tests/test_membership_rows.py
- FOUND: backend/api/tests/test_fitbit_device_rows.py
- FOUND commits: 0350b15, 5240cf2, fa4067f, ed518f7, dafda68, 25484aa
