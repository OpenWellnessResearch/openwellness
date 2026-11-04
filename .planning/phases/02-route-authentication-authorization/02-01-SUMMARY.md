---
phase: 02-route-authentication-authorization
plan: 01
subsystem: auth
tags: [jwt, otp, rbac, coach-scope, refresh-rotation, fastapi]

requires:
  - phase: 01-local-dev-stack-and-backend-baseline
    provides: green api/core/scheduler suites and the pyright baseline
provides:
  - coach_studies claim on AccessClaims, mint_access and verify_access
  - AuthService._login_eligible, the one eligibility predicate for send, verify and refresh
  - coach and admin sign-in without a participant or verified_id
  - refresh that re-derives participant and coach_studies from the current User record
affects: [02-03 get_principal reads claims.coach_studies, 02-04 study-scoped authorization, phase 6 sync policy]

actuals:
  tokens: 4600
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "One shared login-eligibility predicate on the current User record"
    - "Token claims derived from the User record at every mint, never from the session"

key-files:
  created: []
  modified:
    - backend/api/src/openwellness_api/auth/token_service.py
    - backend/api/src/openwellness_api/auth/service.py
    - backend/api/tests/test_auth_api.py
    - backend/api/tests/test_auth_service.py
    - backend/api/tests/test_token_service.py

key-decisions:
  - "Staff (coach/admin) eligibility ignores verified_id; participant-only users still need verified_id and a pid (D-01, D-03)"
  - "coach_studies coerces stored ids with str() and never type-checks ObjectId, because the API may not import bson"
  - "Refresh keeps consume_for_rotation ahead of the eligibility gate, so an ineligible user's presented token is already consumed (A-01-3)"

patterns-established:
  - "_login_eligible(user): active AND (staff OR verified participant with pid)"
  - "Malformed roles or studies degrade to empty, never raise"

requirements-completed: [AUTH-05, AUTH-09]

coverage:
  - id: D1
    description: "A coach or admin with no participant can complete send and verify over HTTP and hold a verified token carrying roles and coach_studies"
    requirement: AUTH-05
    verification:
      - kind: integration
        ref: "backend/api/tests/test_auth_api.py#test_staff_login_coach"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_auth_api.py#test_staff_login_admin"
        status: pass
    human_judgment: false
  - id: D2
    description: "A user with no usable role stays locked out, and send responses for staff, unknown and ineligible emails are identical"
    requirement: AUTH-09
    verification:
      - kind: integration
        ref: "backend/api/tests/test_auth_api.py#test_staff_login_no_role_stays_locked_out"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_auth_api.py#test_staff_login_uniform_send_body"
        status: pass
    human_judgment: false
  - id: D3
    description: "Refresh re-derives participant and coach_studies from the User record and answers the uniform 401 for a user who lost every usable role, consuming the presented token"
    requirement: AUTH-05
    verification:
      - kind: unit
        ref: "backend/api/tests/test_auth_service.py#test_refresh_picks_up_study_change"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_auth_service.py#test_refresh_ineligible_token_stays_dead_after_role_returns"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_auth_service.py#test_refresh_drops_removed_participant_role"
        status: pass
    human_judgment: false
  - id: D4
    description: "verify_access rejects a coach_studies claim that is not a list of strings and returns an empty tuple when absent"
    requirement: AUTH-05
    verification:
      - kind: unit
        ref: "backend/api/tests/test_token_service.py#test_coach_studies_non_list_rejected"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_token_service.py#test_coach_studies_absent_defaults_empty"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-11-04
status: complete
plan_head_before: 3096c96b051e8e2beecdbd1c31f561370bd71229
plan_head_after: 0674ae70cd83f25bc3791abf880cb00ff49351ac
commits: 4
---

# Phase 2 Plan 01: Staff Sign-in and coach_studies Claim Summary

**Coaches and admins can now complete OTP login without a participant record, and every access token carries `coach_studies` re-derived from the User record at login and refresh, behind one shared eligibility predicate.**

## Performance

- **Duration:** about 15 min
- **Completed:** 2026-11-04T22:43Z
- **Tasks:** 2 (1 tracer, 1 auto, both TDD)
- **Files modified:** 5 (2 source, 3 test)

## Accomplishments

- `AccessClaims.coach_studies`, `mint_access(coach_studies=...)` and a `verify_access` shape check (list of strings, absent means empty).
- `_is_staff`, `_coach_studies` and `_login_eligible` on `AuthService`. `_eligible_login_user`, `verify_login_code` and `refresh_token` all use the one predicate.
- Refresh no longer pins the participant claim from the session and no longer survives a lost role.
- Send and verify response bodies are unchanged for unknown, ineligible and staff emails (`UNIFORM_SEND_MESSAGE`, `invalid_code` and `_dummy_hash_work` untouched).

## Task Commits

1. **Task 1 (tracer): coach signs in over HTTP, token carries coach_studies**
   - RED `32201b8` (test): 2 of 4 new tests failed on the planned assertion (no OTP sent for a coach or admin). The other 2 passed because they pin behavior that must not change (no-role lockout, uniform send body).
   - GREEN `6b147dd` (feat)
2. **Task 2: refresh re-derives claims and re-checks eligibility**
   - RED `9b7b101` (test): 6 refresh tests failed on assertions. The `coach_studies` token and malformed-value tests already passed because Task 1 implemented that code.
   - GREEN `0674ae7` (feat)

**Plan metadata:** committed separately (docs: complete plan).

## TDD Gate Compliance

RED then GREEN commit exists for both tasks (`test(02-01)` before `feat(02-01)`). Semantic assessment of RED: each failing target test failed on the planned behavior (`no OTP code recorded for the login email`, claims not matching the User record), not on import, collection or fixture errors. No REFACTOR commits were needed.

## Files Modified

- `backend/api/src/openwellness_api/auth/token_service.py` - `coach_studies` claim on mint and verify.
- `backend/api/src/openwellness_api/auth/service.py` - the three helpers, shared predicate, refresh re-derivation.
- `backend/api/tests/test_auth_api.py` - 4 `test_staff_login_*` HTTP tests.
- `backend/api/tests/test_auth_service.py` - 6 refresh tests plus a parametrized malformed-studies test.
- `backend/api/tests/test_token_service.py` - 4 `test_coach_studies_*` tests.

## Decisions Made

- Followed the plan's assumptions A-01-1 to A-01-3 as written. A dual-role user with a falsy `verified_id` is eligible via the staff role and still gets the participant claim from the pid.

## Deviations from Plan

None - plan executed exactly as written.

One test-only adjustment, not a deviation from behavior: `test_refresh_ineligible_token_stays_dead_after_role_returns` builds its own `_Ctx(resend_cooldown_seconds=0)`, because fakeredis TTLs run on real time and ignore the injected clock, so a second `sendLoginCode` for the same email would otherwise hit the resend cooldown.

## Issues Encountered

None. The plan-level `uv sync --frozen --extra dev` step was not re-run (environment already synced); every other command in the plan's `<verification>` was run and exited 0.

## Verification

- `core` 88 passed, `api` 250 passed (baseline 232), `scheduler` 4 passed.
- `pyright`: 0 errors (12 pre-existing warnings).
- `check_no_fstring_n1ql.py`: exit 0.
- Task 1 and Task 2 `<verify>` commands pass (4 and 14 passed respectively); `result.participant_id` is no longer read in `refresh_token`.

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema changes beyond the planned claim and eligibility predicate.

## Next Phase Readiness

Plan 02-03 can read `claims.coach_studies` in `get_principal`. Note for later plans: `_participant_pid` still assumes `roles.participant` is a dict when truthy (pre-existing, untouched).

## Self-Check: PASSED

- `32201b8`, `6b147dd`, `9b7b101`, `0674ae7` are ancestors of HEAD.
- All five modified files exist.

---
*Phase: 02-route-authentication-authorization*
*Completed: 2026-11-04*
