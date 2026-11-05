---
phase: 02-route-authentication-authorization
plan: 03
subsystem: auth
tags: [fastapi, bearer, floor, route-class, jwt, deny-by-default]
type: execute

requires:
  - phase: 02-route-authentication-authorization
    provides: coach_studies claim on AccessClaims and mint_access (plan 02-01)
provides:
  - strict get_principal(request) that verifies the bearer or raises the uniform 401
  - Principal with coach_studies and is_admin
  - FloorRoute, applied to every resource route, verifying before body parsing
  - test helpers token_for, TEST_ADMIN_ID, anon_client; client authenticates as admin
affects: [02-04 authorize policy engine, 02-05 to 02-10 router migration]

actuals:
  tokens: 9000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "APIRoute subclass wraps the route handler so auth runs before body parsing"
    - "Test tokens minted through the app's own token service"

key-files:
  created:
    - backend/api/tests/test_e2e_roles_flow.py
  modified:
    - backend/api/src/openwellness_api/deps/principal.py
    - backend/api/src/openwellness_api/v1.py
    - backend/api/src/openwellness_api/config.py
    - backend/api/tests/conftest.py
    - backend/api/tests/test_principal.py
    - backend/api/tests/test_auth_api.py
    - backend/api/tests/test_weights_owner_crud.py
    - backend/api/tests/test_repository_errors.py

key-decisions:
  - "Floor is an APIRoute subclass (FloorRoute), not a router dependency or middleware, because FastAPI parses the body before solving dependencies"
  - "No WWW-Authenticate header on the 401, to keep the shape the mobile client depends on"
  - "A missing auth container raises AttributeError (500), never an anonymous pass"

requirements-completed: [AUTH-01, AUTH-06]

coverage:
  - id: D1
    description: "A caller who signs in through the real OTP flow reaches a resource route; anonymous, blank, non-Bearer, garbage and expired bearers all get the same 401 UNAUTHENTICATED body with no WWW-Authenticate header"
    requirement: AUTH-01
    verification:
      - kind: integration
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_signed_in_caller_reaches_a_resource_route"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_anonymous_is_401"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_blank_and_bad_bearer_are_401"
        status: pass
    human_judgment: false
  - id: D2
    description: "The floor answers before body parsing: an anonymous or bad-bearer request with unparseable JSON or invalid UTF-8 is 401, an authenticated one keeps the 400, and /v1/auth:* keeps its own 400"
    requirement: AUTH-01
    verification:
      - kind: integration
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_anonymous_unparseable_body_is_401"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_bad_bearer_with_unparseable_body_is_401"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_authenticated_unparseable_body_keeps_the_400"
        status: pass
      - kind: integration
        ref: "backend/api/tests/test_e2e_roles_flow.py#test_auth_routes_stay_outside_the_floor"
        status: pass
    human_judgment: false
  - id: D3
    description: "Permissive mode and the X-Principal-Id read are deleted; a forged header beside a valid bearer leaves the principal unchanged and alone answers 401"
    requirement: AUTH-06
    verification:
      - kind: unit
        ref: "backend/api/tests/test_principal.py#test_forged_x_principal_id_beside_valid_bearer_changes_nothing"
        status: pass
      - kind: unit
        ref: "backend/api/tests/test_principal.py#test_x_principal_id_alone_is_401"
        status: pass
      - kind: command
        ref: "python -c assert 'enforce_principal' not in AuthSettings.model_fields and no require_principal"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-11-04
status: complete
plan_head_before: 6526d48d883a1153767a93d70180d8bd1dd46139
plan_head_after: a205c588d43d0133800a71c8bf245203cab8ff94
commits: 3
---

# Phase 2 Plan 03: The Bearer Floor Summary

**Every resource route now verifies a bearer token before FastAPI reads the body (a `FloorRoute` wrapping the handler), so anonymous callers get the uniform 401 whatever they send; permissive mode and the `X-Principal-Id` fallback are deleted.**

## Performance

- **Duration:** about 12 min
- **Completed:** 2026-11-04
- **Tasks:** 2 (1 tracer TDD, 1 auto)
- **Files modified:** 9 (3 source, 6 test; 1 test file created)

## Accomplishments

- `get_principal(request)` is the only place a token is validated. Missing header, blank bearer, non-Bearer scheme, garbage and expired tokens all raise one 401 UNAUTHENTICATED envelope.
- `FloorRoute` (`v1.py`) is set on every route of every `RESOURCE_MODULES` router. `/v1/auth:*` and `/healthz` stay outside.
- `Principal` gains `coach_studies` and `is_admin`, loses `is_authenticated`. `require_principal` and `AuthSettings.enforce_principal` are gone.
- The 37 existing `Depends(get_principal)` call sites needed no change: the signature is `(request)` and they only read `.id`.
- Test infra: `token_for`, `TEST_ADMIN_ID`, `anon_client`; `client` is an admin-token client.

## Task Commits

1. **Task 1 (tracer): signed-in caller reaches a resource route, anyone else gets 401 whatever the body**
   - RED `bb3be0e` (test): 5 of 8 tests failed on the planned status assertion (`assert 400 == 401` or 200 vs 401). The other 3 pin behavior that must not change (signed-in 200, authenticated bad body 400, `/v1/auth:*` outside the floor).
   - GREEN `56e6d20` (feat): 8 passed.
   - Tracer gate: `<verify>` re-run, 8 passed. Tracer verified end-to-end, expanded.
2. **Task 2: existing suites onto real tokens, permissive flag deleted**
   - `a205c58` (feat)

## TDD Gate Compliance

RED (`test(02-03)`) precedes GREEN (`feat(02-03)`). Semantic assessment of RED: each failing target test failed on its planned assertion (an anonymous or bad-bearer request answering 200/400 instead of 401), not on import, collection or fixture errors; the conftest helpers were committed in the RED commit so no fixture was missing. The `gsd_run check tdd-red-evidence` classifier was not run (`workflow.tdd_mode` is not enabled and the plan is `type: execute`); the assessment is by inspection of the pytest report. No REFACTOR commit was needed.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `core` 88 passed, `api` 260 passed (was 256; +8 new floor tests, test_principal and test_auth_api rewritten/trimmed), `scheduler` 4 passed.
- `pyright`: 0 errors, 12 warnings (pre-existing).
- `check_no_fstring_n1ql.py`: exit 0.
- Task 2 flag-gone check printed `flag-gone`. `test_users_crud.py`, `test_pagination.py`, `test_participant_ids.py`, `test_goals_carveout.py` untouched and green.

## Known Stubs

None.

## Issues Encountered

- The plan-level `pyright` prints a "new version available" notice; it does not affect the result.
- Interim state, as the plan flagged: until plan 02-10, any authenticated caller can reach routers not yet carrying `authorize`.
- Out of scope, as flagged: an authenticated invalid UTF-8 body gets 400 with FastAPI's plain `{"detail": ...}` body (Starlette `HTTPException`, not handled by the AIP-193 handler).

## Threat Flags

None. T-02-06 and T-02-34 are mitigated and covered by `test_principal.py` and `test_anonymous_unparseable_body_is_401`.

## Next Phase Readiness

Plan 02-04 can put `authorize` behind this floor; it will call `get_principal` and so verifies the token a second time (one extra HMAC, no cache, per the plan).

## Self-Check: PASSED

- `bb3be0e`, `56e6d20`, `a205c58` are ancestors of HEAD.
- `backend/api/tests/test_e2e_roles_flow.py` and the other modified files exist.

---
*Phase: 02-route-authentication-authorization*
*Completed: 2026-11-04*
